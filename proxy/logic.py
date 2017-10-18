import json
import datetime
from uuid import uuid4
import asyncio
from asyncio.subprocess import PIPE
from subprocess import Popen, PIPE
import os
import logging
import sys

import requests
from requests.exceptions import ConnectionError
from hypersh_client.main.hypersh2 import HypershClient

from proxy.driver_requests import get_page_async, NEW_SESSION_REQ_BODY


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


class AppLogic(object):

    def __init__(self, asyncio_loop, proxy_container_id):
        self.loop = asyncio_loop
        self.leftover_drivers = []
        self.drivers = {}
        self.proxy_container = proxy_container_id
        self.hyper_client = HypershClient(os.environ.get('HYPERSH_REGION'))
        self.running_containers_cache = None
        self.running_containers_last_checked = datetime.datetime.now() - datetime.timedelta(minutes=60)

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

    async def launch_driver(self, req_body, reuse_session=None):
        """
        Launch a selenium driver. If a specific 'reuse_session' is specified
        attempt to reuse it, otherwise attempt to find another 'leftover'
        session. Otherwise launch a new driver.
        """
        print('launch_driver() called')
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

        # pops leftover_ids, queries containers for their active sessions
        leftover_id = await self._find_leftover()

        if leftover_id:
            logger.info('reusing leftover driver')
            success = self._create_from_leftover(leftover_id)  # doesn't block
            if success:
                return True, False, self.drivers[leftover_id]

        success, selenium_id = await self._create_new(req_body)  # always blocks
        if not success:
            return False, False, None
        return True, False, self.drivers[selenium_id]

    async def quit_driver(self, selenium_id):
        success = False
        try:
            success = await get_page_async(self.drivers[selenium_id], 'about:blank')
            if not success:
                logger.error('get_page_async() failed')
                # todo: we need to handle two kinds of errors, a selenium session has already been quit or dropped; a container is down

        except ConnectionError:
            logger.error('quit_driver() got a ConnectionError when trying to quit')
            return  # because the container may have gone down
        except Exception as e:
            logger.critical('quit_driver() got unexpected Exception: %s' % e)

        if success:
            self.leftover_drivers.append(selenium_id)
        else:
            logger.error('quit_driver(): driver not added to leftovers because get_page_async() failed')

    def sort_leftovers(self):
        """
        Sort leftovers so most recently used driver gets reused first and so drivers
        in the same container are adjacent (so that _find_leftover() can minimize
        the number of calls to get_active_sessions()
        """
        def order_leftovers(id):
            container = self.drivers[id]['container']
            command_times = [
                self.drivers[id]['last_command_time'] for id in self.drivers
                if self.drivers[id]['container'] == container
            ]
            return max(command_times)  # will be same for all drivers in a container
        self.leftover_drivers.sort(key=order_leftovers, reverse=True)

    async def _launch_driver_on_container(self, req_body, container_name):
        req_session = requests.Session()
        #session = aiohttp.ClientSession(loop=self.loop)
        url = base_url(container_name) + '/wd/hub/session'
        logger.info('launching driver on: '+ base_url(container_name))

        resp = await self.loop.run_in_executor(None, req_session.post, url, req_body)

        logger.info('finished driver launch attempt, status: %s' % resp.status_code)

        if resp.status_code != 200:
            logger.error('POST to %s failed, status: %s' % (url, resp.status_code))
            return False, None, None

        resp_json = json.loads(resp.content.decode())

        return True, req_session, resp_json

    async def _wait_for_container_ready(self, container_name):
        """
        Wait up to 20 seconds for container to come online. Then attempt to
        get selenium active sessions, retrying for up to 6 seconds.
        """
        logger.info('pinging new selenium-node container repeatedly, until successful ping')
        success = await ping_wait(container_name, wait=22)
        if success is False:
            logger.error('container took > 22s to launch, repeated pinging failed')

        await asyncio.sleep(3.5)  # usually needs another 5-6 seconds but start polling for sessions a little earlier

        logger.info('attempting to request for active sessions from the selenium-node, will try 14 times over 7 seconds')
        for i in range(14):
            try:
                success, status, sessions = await self._get_active_sessions(container_name)
                if success:
                    return True
                logger.info('_get_active_sessions() failed, this is normal while the container is initialising (http status: %s)' % status)
            except Exception as e:
                logger.error('exception from _get_active_sessions() %s' % e)

            await asyncio.sleep(0.5)

        if i == 13:
            logger.error('warning: container not ready /wd/hub/sessions failed to load in time, continuing anyway')
        return False

    async def _launch_container(self):
        container_name = 'seleniumnode' + uuid(10)
        image = os.environ.get('SELENIUM_NODE_IMAGE', 'eventjumbler/selenium-node')

        logger.info('creating and starting container: %s from image: %s' % (container_name, image))
        success, container_id = self.hyper_client.create_container(
            image, name=container_name, size='M2',
            environment_variables={'PROXY_CONTAINER': self.proxy_container},
            tcp_ports=['4444', '5555']
        )
        if not success:
            logger.error('error: problem when launching container')
            return False, None

        logger.info('pinging new container repeatedly for 17s to wait for launch')
        success = await ping_wait(container_name, wait=17)
        if not success:
            logger.error('error: ping_wait for new container failed after 16 seconds pinging')
            return False, None

        if self.running_containers_cache:
            self.running_containers_cache.append(container_name)
        else:
            self.running_containers_cache = [container_name]

        logger.info('successfully launched container: ' + container_name)
        return True, container_name

    async def ping_container(self, container_name, deep=False):
        success, stdout, std_err = await sys_call_async("ping -c 1 " + container_name)
        if success is False:
            return False
        if not deep:
            return True
        try:
            success, status, sessions = self._get_active_sessions(container_name)
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

    async def get_active_sessions(self, container=None):
        if container:
            success, status, sessions = await self._get_active_sessions(container)
            return success, sessions
        results = []
        for container in self.container_capacities:
            success, status, sessions = await self._get_active_sessions(container)
            if success:
                results.extend(sessions)
        return True, results

    async def _get_active_sessions(self, container):
        start = datetime.datetime.now()
        #session = aiohttp.ClientSession()
        #resp = await session.get(base_url(container) + '/wd/hub/sessions')
        # old: resp = requests.get(base_url(container) + '/wd/hub/sessions')  # don't catch this exception

        resp = await self.loop.run_in_executor(None, requests.get, base_url(container) + '/wd/hub/sessions')

        if resp.status_code != 200:
            print('GET /wd/hub/sessions status: %s  %s' % (resp.status_code , resp.content.decode()))
            return False, resp.status_code, []

        resp_json = json.loads(resp.content.decode())
        #resp_json = await resp.json()
        active_sessions = [di['id'] for di in resp_json['value']]
        end = datetime.datetime.now()

        print('get_active_sessions() called')
        print(end-start)
        print('active sessions: %s' % active_sessions)

        return True, 200, active_sessions

    async def get_running_containers(self):
        now = datetime.datetime.now()
        fifteen_secs_agp = datetime.timedelta(seconds=7)
        if self.running_containers_cache is None or now-self.running_containers_last_checked > fifteen_secs_agp:

            success, running_containers = self.hyper_client.get_containers(image='digiology/selenium_node')
            # old version: running_containers = await get_running_containers_async(self.loop, 'digiology/selenium_node')
            if not success:
                print('warning: failed to get running containers from hypersh')

            result = [di['name'] for di in running_containers]
            self.running_containers_cache = result
            self.running_containers_last_checked = datetime.datetime.now()
        return self.running_containers_cache

    async def refresh(self):
        running_containers = await self.get_running_containers()

        for cn in list(self.container_capacities.keys()):
            if cn not in running_containers:
                self.notify_container_down(cn)

        def is_valid(di):
            if di['container'] in running_containers and di['state'] != 'DRIVER_LAUNCH_FAILED':
                return True
            return False

        self.drivers = {sel_id: di for (sel_id, di) in self.drivers.items() if is_valid(di)}
        self.leftover_drivers = [id for id in self.leftover_drivers if id in self.drivers.keys()]

    async def _find_leftover(self):
        if not self.leftover_drivers:
            return None

        logger.info('find_leftover() called, leftovers: %s' % self.leftover_drivers)

        await self.refresh()
        active_sessions = {}

        self.sort_leftovers()

        while self.leftover_drivers:
            try:
                leftover_id = self.leftover_drivers.pop()
            except IndexError:
                break  # very slight chance of race-condition

            container = self.drivers[leftover_id]['container']

            if container not in active_sessions:  # so we query it once per container
                success, sessions = await self.get_active_sessions(container)  # todo: does this query take long?
                if success:
                    active_sessions[container] = sessions
                else:
                    active_sessions[container] = []  # container may be down, should we ping and call notify_container_down()? surely refresh() would normally catch this?

            if leftover_id in active_sessions[container]:  # todo: adjust selenium grid's timeout to not drop idle sessions too quickly
                return leftover_id
            # otherwise leftover_id will get discarded

        return None

    async def _create_new(self, req_body, retry_on_fail=True):
        success, created, container_name = await self.get_or_create_container()
        if success is False:
            raise Exception('failed to create new container')

        if created:
            success = await self._wait_for_container_ready(container_name)
            if success is False:
                if retry_on_fail:
                    logger.warning('_create_new() failed, retrying once')
                    return await self._create_new(req_body, retry_on_fail=False)
                else:
                    return False, None

        success, req_session, resp_json = await self._launch_driver_on_container(req_body, container_name)

        if success is False:
            if retry_on_fail:
                logger.warning('_create_new() failed, retrying once')
                return await self._create_new(req_body, retry_on_fail=False)
            return False, None

        selenium_session_id = resp_json['value']['sessionId']

        self.drivers[selenium_session_id] = {
            'requests_session': req_session,
            #'aiohttp_session': req_session,
            'selenium_session_id': selenium_session_id,
            'state': 'DRIVER_STARTED',
            'container': container_name,
            'last_command_time': datetime.datetime.now(),
            'creation_resp_json': resp_json
        }

        return True, selenium_session_id

    def _create_from_leftover(self, leftover_id):
        if leftover_id in self.leftover_drivers:
            try:
                self.leftover_drivers.remove(leftover_id)
            except:  # possible race condition
                return False
        self.drivers[leftover_id]['state'] = 'DRIVER_STARTED'
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