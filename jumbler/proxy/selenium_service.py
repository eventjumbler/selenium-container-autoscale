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
# TODO: should be in database and can be register via REST
_IMAGES = {
    'firefox': {'image': 'selenium/node-firefox', 'tag': 'latest'},
    'chrome': {'image': 'selenium/node-chrome', 'tag': 'latest'},
    'phantomjs': {'image': 'selenium/node-phantomjs', 'tag': 'latest'}
}


_LOG = logging.getLogger(__name__)


class Status(Enum):
    RUNNING = 1
    PENDING = 2
    OFF = 3
    NOT_AVAILABLE = 4


class SeleniumService:

    def __init__(self, loop, docker_client):
        self.loop = loop
        self.docker_client = docker_client

    async def start_node(self, hub_ip, capabilities, hub_port=_DEFAULT_HUB_PORT):
        resp_code, response = await rest_client.http_post('http://%s:%d/wd/hub' % (hub_ip, hub_port), json=capabilities)
        if resp_code != 200:
            raise RequestError('Cannot connect to selenium hub in host %s:%d' % (hub_ip, hub_port))
        return response

    def create_node(self, hub_name, browser, selenium_node_id, image=None, tag=None):
        image = _IMAGES[browser.lower()].get('image') if not image else image
        tag = _IMAGES[browser.lower()].get('tag') if not tag else tag
        if not image:
            raise NotFoundError('Docker image for browser %s is not available' % browser)
        full_image = '%s:%s' % (image, tag)
        if not self.docker_client.pull_image(image, tag):
            raise RequestError('Cannot pull image %s', full_image)
        env = copy.deepcopy(_DEFAULT_NODE_OPTION)
        env['SE_OPTS'] = '-id ' + selenium_node_id
        links = [hub_name + ':hub']
        status, container_id = self.docker_client.create_container(full_image, name=selenium_node_id, environment_variables=env, links=links)
        if status:
            return container_id
        raise RequestError('Cannot create container')

    async def verify_node_status(self, hub_ip, selenium_node_id, hub_port=_DEFAULT_HUB_PORT):
        json_data = {'id': selenium_node_id, 'isAlive': '', 'isDown': ''}
        resp_code, response = await rest_client.http_post('http://%s:%d/grid/api/proxy' % (hub_ip, hub_port), json=json_data)
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
        node_port = int(response['request']['configuration']['port'] or _DEFAULT_NODE_PORT)
        resp_code, response = await rest_client.http_get('http://%s:%d/wd/hub/sessions' % (node_host, node_port))
        if resp_code != 200:
            raise RequestError('Cannot connect to selenium node %s in host %s:%d' % (selenium_node_id, node_host, node_port))
        # status = response['status']
        value = response['value']
        if value:
            return Status.RUNNING
        return Status.PENDING
