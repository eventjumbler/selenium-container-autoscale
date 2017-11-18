import asyncio
import datetime
import json
import logging
import os
import random
import re
import sys

from hypersh_client.main.hypersh import HypershClient
from urllib3.exceptions import NewConnectionError

import proxy.cmd_utils as cmd_utils
from proxy.driver_requests import NEW_SESSION_REQ_BODY
from proxy.selenium_client import SeleniumClient
from proxy.util import PORT, do_selenium_request_async, get_session_id, uuid
from sanic.response import json as json_resp

NODE_IMAGE = os.environ.get('SELENIUM_NODE_IMAGE', 'eventjumbler/selenium-node')
NEW_SESSION_REQ_BODY_STR = json.dumps(NEW_SESSION_REQ_BODY)


MAX_DRIVERS_PER_CONTAINER = 3

logger = logging.getLogger(__name__)


def create_container(app_logic, container_name):
    self = app_logic
    return self.hyper_client.create_container(
        NODE_IMAGE, container_name, size='M2',
        environment_variables={'PROXY_CONTAINER': self.proxy_container},
        tcp_ports=['4444', '5555']
    )


class AppLogic(object):

    def __init__(self, asyncio_loop, proxy_container_id):
        self.loop = asyncio_loop
        self.leftover_drivers = []
        self.drivers = {}
        self.proxy_container = cmd_utils.get_host()
        self.hyper_client = HypershClient()
        self.selenium_client = SeleniumClient(self.loop)

    @property
    def container_capacities(self):
        driver_counts = {}
        for _, di in self.drivers.items():
            driver_counts[di['container']] = driver_counts.get(di['container'], 0) + 1
        return {
            container: (MAX_DRIVERS_PER_CONTAINER - count)
            for (container, count) in driver_counts.items()
        }

    async def launch_driver(self, req_body):

        leftover_id = await self._find_leftover()

        if leftover_id:
            logger.info('reusing leftover driver')
            success = self._create_from_leftover(leftover_id)
            if success:
                return True, False, self.drivers[leftover_id]

        success, created, container_name = await self.get_or_create_container()
        if success is False:
            return False, None, None

        if created:  # wait for selenium to start
            await asyncio.sleep(3.5)
            success = await self._wait_for_selenium_ready(container_name)
            if success is False:
                return False, None, None

        success, req_session, resp_json = await self.selenium_client._launch_driver_on_container(
            req_body, container_name
        )

        if success is False:
            return False, None, None

        selenium_session_id = resp_json['value']['sessionId']

        self.drivers[selenium_session_id] = {
            'requests_session': req_session,
            'selenium_session_id': selenium_session_id,
            'container': container_name,
            'last_command_time': datetime.datetime.now(),
            'creation_resp_json': resp_json
        }

        return True, True, self.drivers[selenium_session_id]

    async def quit_driver(self, selenium_id):
        container = self.drivers[selenium_id]['container']

        if (await self.ping_container(container)) is False:
            logger.warning('quit_driver() called on offline container')
            return

        success = await self.selenium_client.get_page(container, selenium_id, 'about:blank')
        if not success:
            logger.error('quit_driver(): driver not added to leftovers because get_page() failed')
            return

        self.leftover_drivers.append(selenium_id)

    def sort_leftovers(self):
        """
        Sort leftovers so most recently used drivers can get reused first and so drivers
        in the same container are adjacent (makes _find_leftover() more efficient)
        """
        def order_leftovers(id):
            container = self.drivers[id]['container']
            command_times = [
                self.drivers[id]['last_command_time'] for id in self.drivers
                if self.drivers[id]['container'] == container
            ]
            return max(command_times)  # will be same for all drivers in a container
        self.leftover_drivers.sort(key=order_leftovers, reverse=True)

    async def _wait_for_selenium_ready(self, container_name, wait_time=12):
        """ Wait for selenium to initialise and respond to requests. """
        logger.info('waiting for selenium to be ready, will retry get_active_sessions() for %s seconds' % wait_time)

        if (await self.ping_container(container_name)) is False:
            logger.warning('_wait_for_selenium_ready() called on container that seems offline (ping failed)')

        iterations = round(wait_time / 0.5)
        for i in range(iterations):
            try:
                success, sessions = await self.selenium_client.get_active_sessions([container_name])
                if success:
                    logger.info('selenium ready on: ' + container_name)
                    return True
                logger.info('_get_active_sessions() failed, this is normal while the container is initialising')
            except NewConnectionError:
                logger.info('waiting for selenium-grid to initialise on container (POST to /wd/hub/sessions/ gave a NewConnectionError)')

            await asyncio.sleep(0.5)

        logger.warning('selenium failed to be ready on %s after %s seconds' % (container_name, wait_time))
        return False

    async def _launch_container(self):
        container_name = 'seleniumnode' + uuid(10)

        logger.info('creating and starting container: %s from image: %s' % (container_name, NODE_IMAGE))

        success, container_id = await self.loop.run_in_executor(
            None, create_container, self, container_name
        )

        if not success:
            logger.error('error: problem when launching container')
            return False, None

        logger.info('pinging new container repeatedly for 22s to wait for launch')
        success = await cmd_utils.ping_wait(container_name, wait=22)
        if not success:
            logger.error('error: ping_wait for new container failed after 16 seconds pinging')
            return False, None

        logger.info('successfully launched container: ' + container_name)
        return True, container_name

    async def ping_container(self, container_name, deep=False):
        success, stdout, std_err = await cmd_utils.sys_call_async("ping -c 1 " + container_name)
        if success is False:
            return False
        if not deep:
            return True
        try:
            success, sessions = await self.selenium_client.get_active_sessions([container_name])
            return success
        except:
            return False

    async def shutdown_nodes(self):
        containers = self.container_capacities.keys()
        for container in containers:
            await self.loop.run_in_executor(  # hopefully doesn't stall?
                None, self.hyper_client.remove_container, container
            )
            self.notify_container_down(container)

    def notify_container_down(self, container_name):
        to_delete = []
        for session_id, di in self.drivers.items():
            if di['container'] == container_name:
                to_delete.append(session_id)

        for session_id in to_delete:
            del self.drivers[session_id]

            if session_id in self.leftover_drivers:
                try:
                    self.leftover_drivers.remove(session_id)
                except:
                    pass  # just in case of race condition

    async def get_or_create_container(self):
        for name, capacity in self.container_capacities.items():
            # slight possibility that this would be out of sync, it could be that one of the driver sessions has been dropped
            if capacity >= 1:
                ping_result = await self.ping_container(name)  # can we put this in the if statement?
                if ping_result is False:
                    self.notify_container_down(name)
                    continue
                return True, False, name
        success, container_name = await self._launch_container()
        return success, True, container_name   # success, created, container_name

    async def _find_leftover(self):
        if not self.leftover_drivers:
            return None

        logger.info('find_leftover() called, leftovers: %s' % self.leftover_drivers)

        active_sessions = {}

        self.sort_leftovers()

        while self.leftover_drivers:
            try:
                leftover_id = self.leftover_drivers.pop()
            except IndexError:
                break  # very slight chance of race-condition

            container = self.drivers[leftover_id]['container']

            if container not in active_sessions:  # so we query it once per container
                success, sessions = await self.selenium_client.get_active_sessions([container])
                active_sessions[container] = sessions if success else []

            if leftover_id in active_sessions[container]:
                return leftover_id
            # otherwise leftover_id will get discarded

        return None

    async def proxy_selenium_request(self, request, driver_url):
        body_str = request.body.decode()
        selenium_id = get_session_id(driver_url, body_str)
        container = self.drivers[selenium_id]['container']
        request_session = self.drivers[selenium_id]['requests_session']
        if random.randint(0, 10) == 9:  # for efficiency, we do this 1 in every 10 requests
            self.drivers['last_command_time'] = datetime.datetime.now()

        url = 'http://' + container + ':' + PORT + '/' + driver_url

        status_code, resp_json = await do_selenium_request_async(
            request, request_session, url
        )
        if status_code != 200:
            print('warning: selenium request gave status: %s' % status_code)

        return json_resp(resp_json, status=status_code)
        # return HTTPResponse(resp.content.decode(), status=resp.status_code, content_type="application/json")

    def _create_from_leftover(self, leftover_id):
        if leftover_id in self.leftover_drivers:
            try:
                self.leftover_drivers.remove(leftover_id)
            except:  # possible race condition
                return False
        self.drivers[leftover_id]['last_command_time'] = datetime.datetime.now()
        return True


# old code:
'''
async def launch_driver():

    if reuse_session:
        if reuse_session in self.leftover_drivers:
            self._create_from_leftover(reuse_session)
            return True, False, self.drivers[reuse_session]
            # else, ignore and continue as normal
        else:
            if reuse_session in self.drivers:
                logger.warning(
                    'warning: reuse_session not found in leftovers, '
                    'you need to call driver.quit() or /quit_driver/ first'
                )
            else:
                logger.error('warning: reuse_session not found, driver session doesn\'t exist')


async def refresh(self):
    running_containers = await self.get_running_containers()

    for cn in list(self.container_capacities.keys()):
        if cn not in running_containers:
            self.notify_container_down(cn)

    def is_valid(di):
        if di['container'] in running_containers:# and di['state'] != 'DRIVER_LAUNCH_FAILED':
            return True
        return False

    self.drivers = {sel_id: di for (sel_id, di) in self.drivers.items() if is_valid(di)}
    self.leftover_drivers = [id for id in self.leftover_drivers if id in self.drivers.keys()]

async def get_running_containers(self):
    now = datetime.datetime.now()
    fifteen_secs_agp = datetime.timedelta(seconds=7)

    if self.running_containers_cache is None or now-self.running_containers_last_checked > fifteen_secs_agp:

        success, running_containers = self.hyper_client.get_containers(state='running', image=NODE_IMAGE)

        if not success:
            print('warning: failed to get running containers from hypersh')

        result = [di['name'] for di in running_containers]
        self.running_containers_cache = result
        self.running_containers_last_checked = datetime.datetime.now()
    return self.running_containers_cache
'''
