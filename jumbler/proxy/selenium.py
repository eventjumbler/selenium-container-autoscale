import copy
import logging
from enum import Enum

import proxy.rest_client as rest_client

from exception import NotFoundError, RequestError

_DEFAULT_HUB_PORT = 4444
_DEFAULT_NODE_PORT = 5555
_DEFAULT_NODE_OPTION = {
    'SCREEN_WIDTH': '1920',
    'SCREEN_HEIGHT': '1080'
}
# TODO: should be in database
_IMAGES = {
    'firefox': 'selenium/node-firefox',
    'chrome': 'selenium/node-chrome',
    'phantomjs': 'selenium/node-phantomjs',
}


_LOG = logging.getLogger(__name__)


class Status(Enum):
    RUNNING = 1
    PENDING = 2
    OFF = 3
    NOT_AVAILABLE = 4


class Selenium:

    def __init__(self, loop, docker_client):
        self.loop = loop
        self.docker_client = docker_client

    def start_new_node(self, hub_name, browser, selenium_node_id, image=None):
        image = _IMAGES[browser] if not image else image
        if not image:
            raise NotFoundError('Docker image for browser %s is not available' % browser)
        env = copy.deepcopy(_DEFAULT_NODE_OPTION)
        env['SE_OPTS'] = '-id ' + selenium_node_id
        links = [hub_name + ':hub']
        return self.docker_client.create_container(image, name=selenium_node_id, environment_variables=env, links=links)

    def verify_node_status(self, hub_ip, selenium_node_id, hub_port=_DEFAULT_HUB_PORT):
        json_data = {'id': selenium_node_id, 'isAlive': '', 'isDown': ''}
        resp_code, response = rest_client.http_post(hub_ip + ':' + str(hub_port) + '/grid/api/proxy', json=json_data)
        if resp_code != 200:
            raise RequestError('Cannot connect to selenium hub')
        is_success = response['success']
        is_alive = response['isAlive']
        is_down = response['isDown']
        if not is_success:
            raise RequestError('Failure when communicate with selenium hub')
        if not is_alive or is_down:
            return Status.OFF
        node_host = response['request']['configuration']['host']
        node_port = response['request']['configuration']['port'] or _DEFAULT_NODE_PORT
        resp_code, response = rest_client.http_get(node_host + ':' + node_port + '/wd/hub/sessions')
        if resp_code != 200:
            raise RequestError('Cannot connect to selenium node %s in host %s, %s' % (selenium_node_id, node_host, node_port))
        # status = response['status']
        value = response['value']
        if value:
            return Status.RUNNING
        return Status.PENDING
