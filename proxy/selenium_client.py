import json
import logging
import requests
import sys


logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger(__name__)


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
        from .logic import base_url
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
        from .driver_requests import get_page_async
        success = await get_page_async(container, session_id, url)
        if not success:
            logger.error('get_page_async() failed')
        return success
