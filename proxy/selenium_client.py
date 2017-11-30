import logging
import sys

import aiohttp

from proxy.util import http_get, http_post
import json


logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger(__name__)


def base_url(container_name):
    return 'http://' + container_name + ':' + '5555'


class SeleniumClient(object):

    def __init__(self, loop):
        self.loop = loop
        self.req_sessions = {}

    async def get_req_session(self, container):
        if container not in self.req_sessions:
            self.req_sessions[container] = aiohttp.ClientSession()
        return self.req_sessions[container]

    async def get_active_sessions(self, containers):
        assert isinstance(containers, list)

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
            status, resp_json = await http_get(
                base_url(container) + '/wd/hub/sessions',
                session=(await self.get_req_session(container))
            )
        except:
            return False, None, None

        if status != 200:
            print('GET /wd/hub/sessions status: %s  %s' % (status , resp_json))
            return False, status, []

        active_sessions = [di['id'] for di in resp_json['value']]
        logger.info('%s has sessions: %s ' % (container, active_sessions))
        return True, 200, active_sessions

    async def _launch_driver_on_container(self, req_body, container_name):
        from .logic import base_url
        logger.info('launching driver on: ' + base_url(container_name))

        url = base_url(container_name) + '/wd/hub/session'
        req_session = aiohttp.ClientSession()  # new session per driver (todo: if we implement proxying through this class we should store this session in another dictionary keyed by selenium_id)
        try:
            status_code, resp_json = await http_post(
                url, data=req_body,
                session=req_session
            )
        except:
            logger.error('exception thrown when attemtping to launch driver')
            return False, None, None

        logger.info('finished driver launch attempt, status: %s' % status_code)

        if status_code != 200:
            logger.error('POST to %s failed, status: %s' % (url, status_code))
            return False, None, None

        return True, req_session, resp_json

    async def get_page(self, container, selenium_sess_id, url):

        req_url = 'http://'+container+':5555'+('/wd/hub/session/%s/url' % selenium_sess_id)

        status_code, resp_json = await http_post(
            req_url, json={'sessionId': selenium_sess_id, 'url': url},
            session=(await self.get_req_session(container))
        )

        if status_code not in (200, 201, 204):
            logger.error('get_page_async() failed')
            return False
        return True
