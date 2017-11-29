import time
import copy
import logging
from enum import Enum

import proxy.rest_client as rest_client
from exception import NotFoundError, RequestError

_DEFAULT_BROWSER = 'firefox'
_DEFAULT_PLATFORM = 'LINUX'
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


class State(Enum):
    '''
    Represents for Selenium Grid Node state
    '''
    RUNNING = 1
    PENDING = 2
    OFF = 3
    NOT_AVAILABLE = 4
    UNKNOWN = 5


class SeleniumService:
    '''
    Selenium service interacts with Selenium Grid Hub or Selenium Grid Node via REST API or plain HTTP endpoint
    '''

    def __init__(self, loop, retry=5, interval=1):
        self.loop = loop
        self.retry = retry
        self.interval = interval

    def find_nodes(self, hub_name, hub_ip, hub_port=_DEFAULT_HUB_PORT):
        # TODO: implement
        return []

    def generate_hub_url(self, hub_ip, path, hub_port=_DEFAULT_HUB_PORT):
        return 'http://%s:%s/wd/hub/%s' % (hub_ip, hub_port, path)

    async def start_node(self, hub_ip, selenium_node_id, capabilities, hub_port=_DEFAULT_HUB_PORT):
        '''
        Execute business by starting Selenium Grid Node with `capabilities` by connect to `<hup_ip>:<hub_port>/wd/hub/session`

        :Args:
        hub_ip: Selenium Grid Hub internal IP in Docker network to request connection
        hub_port: Selenium Grid Hub Port. Default: `4444`
        capabilities: Selenium Grid Node capabilities. To specific which node for execution, must define `applicationName`

        :Returns:
        response: Selenium response when request new Grid Node session
        '''
        state = State.UNKNOWN
        for count in range(self.retry):
            try:
                state = await self.verify_node_status(hub_ip, selenium_node_id)
                if state is State.PENDING:
                    break
            except RequestError:
                _LOG.debug('Verify Node status #%d', count)
            time.sleep(self.interval)
        if state is not State.PENDING:
            raise RequestError('Selenium Node is in %s. Failure to start Selenium Node %s' % (state, selenium_node_id))
        url = self.generate_hub_url(hub_ip, 'session', hub_port)
        resp_code, response = await rest_client.http_post(url, json=capabilities)
        if resp_code != 200:
            raise RequestError('Failure communication with Selenium Hub in %s. Response: %s' % (url, response))
        return response

    def create_node(self, hub_name, browser, selenium_node_id, image=None, tag=None):
        '''
        Create new Docker container for Selenium Grid Node.\n
        If Docker image of Selenium Grid Node not found in current system, it will try to pull image firstly

        :Args:
        hub_name: Selenium Grid Hub name to link from new Selenium Grid node
        browser: Request browser for execution
        selenium_node_id: Uses for container name, Selenium Grid node id and `applicationName` in capabilities
        image: Customize image name
        tag: Customize image tag

        :Returns:
        node_info: Selenium Node information that uses when creating new Docker container
        '''
        browser = browser.lower()
        image = _IMAGES[browser].get('image') if not image else image
        tag = _IMAGES[browser].get('tag') if not tag else tag
        if not image:
            raise NotFoundError('Docker image for browser %s is not available' % browser)
        full_image = '%s:%s' % (image, tag)
        env = copy.deepcopy(_DEFAULT_NODE_OPTION)
        env['SE_OPTS'] = '-id ' + selenium_node_id
        env['NODE_APPLICATION_NAME'] = selenium_node_id
        links = [hub_name + ':hub']
        return {'full_image': full_image, 'image': image, 'tag': tag, 'name': selenium_node_id, 'env': env, 'links': links}

    async def verify_node_status(self, hub_ip, selenium_node_id, hub_port=_DEFAULT_HUB_PORT):
        '''
        Check Selenium Grid Node status.

        :Args:
        hub_ip: Selenium Grid Hub internal IP in Docker network to request connection
        hub_port: Selenium Grid Hub Port. Default: `4444`
        selenium_node_id: Selenium Grid Node id to check

        :Returns:
        state: Selenium Grid Node status :cls:`<selenium_service.State>`
        '''
        json_data = {'id': selenium_node_id, 'isAlive': '', 'isDown': ''}
        resp_code, response = await rest_client.http_post('http://%s:%d/grid/api/proxy' % (hub_ip, hub_port), json=json_data)
        if resp_code != 200:
            raise RequestError('Cannot connect to Selenium Hub to retrieve Selenium Node information')
        is_success = response.get('success')
        is_alive = response.get('isAlive')
        is_down = response.get('isDown')
        if not is_success:
            raise RequestError('Failure communication with Selenium Hub. Response: %s' % response)
        if not is_alive or is_down:
            return State.OFF
        node_host = response['request']['configuration']['host']
        node_port = int(response['request']['configuration']['port'] or _DEFAULT_NODE_PORT)
        selenium_node_url = self.generate_hub_url(node_host, 'sessions', node_port)
        resp_code, response = await rest_client.http_get(selenium_node_url)
        if resp_code != 200:
            raise RequestError('Failure communication with Selenium Node %s in %s. Response: %s' % (selenium_node_id, selenium_node_url, response))
        # status = response['status']
        value = response.get('value')
        if value:
            return State.RUNNING
        return State.PENDING
