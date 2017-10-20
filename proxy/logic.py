import json
import datetime
from uuid import uuid4
import asyncio
from asyncio.subprocess import PIPE
from subprocess import Popen, PIPE
import os
import logging
import sys
from urllib3.exceptions import NewConnectionError
import requests
from requests.exceptions import ConnectionError
from hypersh_client.main.hypersh2 import HypershClient

from proxy.driver_requests import get_page_async, NEW_SESSION_REQ_BODY


NODE_IMAGE = os.environ.get('SELENIUM_NODE_IMAGE', 'eventjumbler/selenium-node')
NEW_SESSION_REQ_BODY_STR = json.dumps(NEW_SESSION_REQ_BODY)


PORT = '5555'
MAX_DRIVERS_PER_CONTAINER = 3
SESSION_TYPE = 'asycnio'  # 'requests'


logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger(__name__)


def base_url(container_name):
    #from main_new2 import PRODUCTION, HYPER_FIP
    host = container_name #if PRODUCTION else HYPER_FIP
    return 'http://' + host + ':' + PORT


def uuid(len):
    return uuid4().hex[:len]


class SeleniumClient(object):

    def __init__(self, loop):
        self.loop = loop

    async def get_active_sessions(self, containers):
        if len(containers) == 1:
            success, status, sessions = await self._get_active_sessions(
                containers[0]
            )
            return success, sessions

        results = []
        success = False
        for container in containers:
            succ, status, sessions = await self._get_active_sessions(container)
            if succ:
                success = True
                results.extend(sessions)
        return success, results

    async def _get_active_sessions(self, container):
        try:
            resp = await self.loop.run_in_executor(None, requests.get, base_url(container) + '/wd/hub/sessions')
        except:
            return False, None, None

        if resp.status_code != 200:
            print('GET /wd/hub/sessions status: %s  %s' % (resp.status_code , resp.content.decode()))
            return False, resp.status_code, []

        resp_json = json.loads(resp.content.decode())

        active_sessions = [di['id'] for di in resp_json['value']]

        logger.info('get_active_sessions() called: %s' % active_sessions)

        return True, 200, active_sessions

    async def _launch_driver_on_container(self, req_body, container_name):
        logger.info('launching driver on: ' + base_url(container_name))

        req_session = requests.Session()
        url = base_url(container_name) + '/wd/hub/session'

        try:
            resp = await self.loop.run_in_executor(None, req_session.post, url, req_body)
        except Exception as e:
            logger.error('exception thrown when attemtping to launch driver')
            return False, None, None

        logger.info('finished driver launch attempt, status: %s' % resp.status_code)

        if resp.status_code != 200:
            logger.error('POST to %s failed, status: %s' % (url, resp.status_code))
            return False, None, None

        resp_json = json.loads(resp.content.decode())

        return True, req_session, resp_json

    async def get_page(self, container, session_id, url):
        success = await get_page_async(container, session_id, url)
        if not success:
            logger.error('get_page_async() failed')
        return success


class AppLogic(object):

    def __init__(self, asyncio_loop, proxy_container_id):
        self.loop = asyncio_loop
        self.leftover_drivers = []
        self.drivers = {}
        self.proxy_container = proxy_container_id
        self.hyper_client = HypershClient(os.environ.get('HYPERSH_REGION'))
        self.selenium_client = SeleniumClient(self.loop)

    @property
    def container_capacities(self):
        driver_counts = {}
        for driver_id, di in self.drivers.items():
            container = di['container']
            # should we skip if last_command_time > 10 minutes and assume it has been dropped?  (todo: set timeout on the selenium container, I think there is an env variable for this in selenium grid)
            driver_counts[container] = driver_counts.get(container, 0) + 1
        for container, count in driver_counts.items():
            driver_counts[container] = MAX_DRIVERS_PER_CONTAINER - count
        return driver_counts

    async def launch_driver(self, req_body):

        leftover_id = await self._find_leftover()

        if leftover_id:
            logger.info('reusing leftover driver')
            success = self._create_from_leftover(leftover_id)
            if success:
                return True, False, self.drivers[leftover_id]

        success, created, container_name = await self.get_or_create_container()
        if success is False:
            raise Exception('failed to create new container')

        if created:  # wait for selenium to start
            await asyncio.sleep(3.5)
            success = await self._wait_for_selenium_ready(container_name)
            if success is False:
                logger.error('_wait_for_container_ready() timeout, launch_driver() aborted')
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

    async def _wait_for_selenium_ready(self, container_name, wait_time=8):
        """ Wait for selenium to initialise and respond to requests. """
        logger.info('waiting for selenium to ready, will retry get_active_sessions() for %s seconds' % wait_time)

        if (await self.ping_container(container_name)) is False:
            logger.warning('_wait_for_selenium_ready() called on container that cannot curently be pinged')

        iterations = round(wait_time/0.5)
        for i in range(iterations):
            try:
                success, sessions = await self.selenium_client.get_active_sessions([container_name])
                if success:
                    logger.info('selenium ready on: '+container_name)
                    return True
                logger.info('_get_active_sessions() failed, this is normal while the container is initialising')
            except NewConnectionError:
                logger.info('waiting for selenium-grid to initialise on container (POST to /wd/hub/sessions/ gave a NewConnectionError)')

            await asyncio.sleep(0.5)

        logger.info('selenium failed to be ready on %s after %s seconds' % (container_name, wait_time))
        return False

    async def _launch_container(self):
        container_name = 'seleniumnode' + uuid(10)

        logger.info('creating and starting container: %s from image: %s' % (container_name, NODE_IMAGE))
        success, container_id = self.hyper_client.create_container(
            NODE_IMAGE, name=container_name, size='M2',
            environment_variables={'PROXY_CONTAINER': self.proxy_container},
            tcp_ports=['4444', '5555']
        )
        if not success:
            logger.error('error: problem when launching container')
            return False, None

        logger.info('pinging new container repeatedly for 22s to wait for launch')
        success = await ping_wait(container_name, wait=22)
        if not success:
            logger.error('error: ping_wait for new container failed after 16 seconds pinging')
            return False, None

        logger.info('successfully launched container: ' + container_name)
        return True, container_name

    async def ping_container(self, container_name, deep=False):
        success, stdout, std_err = await sys_call_async("ping -c 1 " + container_name)
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
                None, self.hyper_client.remove_container, (container,)
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

    def _create_from_leftover(self, leftover_id):
        if leftover_id in self.leftover_drivers:
            try:
                self.leftover_drivers.remove(leftover_id)
            except:  # possible race condition
                return False
        self.drivers[leftover_id]['last_command_time'] = datetime.datetime.now()
        return True


async def sys_call_async(command):
    proc = await asyncio.create_subprocess_exec(*command.split(), stdout=PIPE, stderr=PIPE)   # or loop.subprocess_exec?
    await proc.wait()
    stdout, stderr = await proc.communicate()
    success = proc.returncode == 0
    return success, stdout.decode(), stderr.decode()


def sys_call(cmd_str, shell=False, suppress_errors=True):
    p = Popen(cmd_str.split(), stdout=PIPE, stderr=PIPE, stdin=PIPE, shell=shell) #stderr=PIPE,
    #p.communicate()
    stdout, stderr = p.stdout.read(), p.stderr.read()
    p.wait()
    success = p.returncode == 0
    return success, stdout, stderr


async def ping_wait(container_name, wait=9):
    print('poop')
    num_loops = round(wait / 0.35)
    #host = container_name if PRODUCTION else HYPER_FIP
    command = "ping -c 1 " + container_name #+ " >/dev/null 2>&1"

    #command = 'ls -la sdfsdf'
    print('num loops: %s' % num_loops)

    for i in range(num_loops):  # wait up to 9 seconds
        print('ping!')
        success, stdout, stderr = await sys_call_async(command)

        if success:
            return True
        print('stdout: '+ stdout)
        print('stderr: ' + stderr)

        await asyncio.sleep(0.35)
    print('finished pinging without succeeding')
    return False



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

        success, running_containers = self.hyper_client.get_containers(image=NODE_IMAGE)

        if not success:
            print('warning: failed to get running containers from hypersh')

        result = [di['name'] for di in running_containers]
        self.running_containers_cache = result
        self.running_containers_last_checked = datetime.datetime.now()
    return self.running_containers_cache
'''