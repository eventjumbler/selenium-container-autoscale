import logging
import re
import time

import dockerrest.docker_provider as docker_provider

import proxy.cmd_utils as cmd_utils
import proxy.rest_client as rest_client
import proxy.util as util
from exception import (ExecutionError, NotFoundError, RequestError,
                       ValidationError)
from proxy.database_service import DatabaseService
from proxy.selenium_service import SeleniumService, State

_LOG = logging.getLogger(__name__)


class BusinessLogic(object):
    '''
    Represents application bussiness logic, manages database service/selenium service and so more
    '''

    def __init__(self, asyncio_loop, business_cfg):
        self.loop = asyncio_loop
        self.retry = business_cfg.get('retry')
        self.interval = business_cfg.get('interval')
        self.docker_client = docker_provider.factory(business_cfg.get('mode'), loop=self.loop, endpoint=business_cfg.get('endpoint'))
        self.proxy_container_id = cmd_utils.get_host()
        self.proxy_container_ip = self.__get_docker_container_ip(self.proxy_container_id)
        self.selenium = SeleniumService(self.loop, self.retry, self.interval)
        self.database = DatabaseService(self.loop)

    async def create_node_container(self, browser, os_system):
        '''
        Create new or reuse node

        :Args:
        browser: Request browser
        os_system: Request OS platform

        :Returns:
        result: A dict mapping node name and its information. For example:
        `{'browser': 'chrome', 'os': 'LINUX', 'container_id': 'b870855c27f47fed29334b8776617837c3f71392ec2bafd1437c2f88aa52d4ba',
        'selenium_node_id': 'chrome-ce3adcddcf'}`
        '''
        _LOG.info('Register new container Browser: %s - OS: %s', browser, os_system)
        browser, os_system = self.__validate_request_node(browser, os_system)
        status, container_id, selenium_node_id = await self.__check_node_browser_available(browser, os_system)
        _LOG.info('Node Id: %s - Node Status: %s', selenium_node_id, str(status))
        result = {'browser': browser, 'os': os_system, 'container_id': container_id, 'selenium_node_id': selenium_node_id}
        if status in (State.NOT_AVAILABLE, State.RUNNING):
            # Create new selenium node with browser and generated id
            result['selenium_node_id'] = browser + '-' + util.uuid(10)
            container_info = self.selenium.create_node_info(self.proxy_container_id, browser, result.get('selenium_node_id'))
            if not self.docker_client.pull_image(container_info.get('image'), container_info.get('tag')):
                raise RequestError('Cannot pull image %s', container_info.get('full_image'))
            status, result['container_id'] = self.docker_client.create_container(
                container_info.get('full_image'), name=container_info.get('name'),
                env_vars=container_info.get('env'), links=container_info.get('links'))
            if not status:
                raise RequestError('Cannot create container')
        elif status is State.OFF:
            success = self.docker_client.start_container(container_id)
            if not success:
                raise RequestError('Cannot start container id: %s - name: %s' % (container_id, selenium_node_id))
        elif status is State.PENDING:
            pass
        else:
            raise ExecutionError('Not handle status: %s', str(status))
        await self.database.persist_node(result, status)
        return result

    async def start_selenium_node(self, capabilities):
        '''
        Start execution via specified Selenium Grid Node

        :Args:
        capabilities: Selenium Grid Node capabilities

        :Returns:
        response: Selenium Grid Server response
        '''
        browser, os_system = self.__validate_request_node(
            capabilities.get('desiredCapabilities').get('browserName'),
            capabilities.get('desiredCapabilities').get('platform')
        )
        result = await self.create_node_container(browser, os_system)
        selenium_node_id = result.get('selenium_node_id')
        capabilities['desiredCapabilities']['applicationName'] = selenium_node_id
        response = await self.selenium.start_node(self.proxy_container_ip, selenium_node_id, capabilities)
        await self.database.update_node_state(selenium_node_id, State.RUNNING)
        return response

    async def verify_node_status(self, selenium_node_id):
        '''
        Check Selenium Grid Node state

        :Args:
        selenium_node_id: Selenium Grid Node id

        :Returns:
        result: A dict mapping node name and its status. For example:
        `{'node': 'test1', 'state': 'RUNNING'}`
        '''
        result = {}
        result['node'] = selenium_node_id
        result['state'] = await self.selenium.verify_node_status(self.proxy_container_ip, selenium_node_id)
        return result

    async def stop_node(self, selenium_node_id):
        '''
        Stop Selenium Grid Node

        :Args:
        selenium_node_id: Selenium Grid Node id
        '''
        self.database.update_node_state(selenium_node_id, State.STOP)

    async def cleanup_selenium_nodes(self, hub_name):
        '''
        Cleanup all selenium nodes that link to hub_name.\n
        It is mandatory step before stop server

        :Args:
        hub_name: Selenium Grid Node id
        '''
        node_ids = self.selenium.find_nodes(hub_name)
        # self.docker_client.stop_container(node_ids)
        await self.database.remove_node(node_ids)

    async def forward_request(self, request, driver_url):
        '''
        Forward request to Selenium Hub

        :Args:
        request: HTTP request
        driver_url: Selenium Hub driver URL
        '''
        url = self.selenium.generate_hub_url(self.proxy_container_ip, driver_url)
        if request.method == 'POST':
            return await rest_client.http_post(url, data=request.body)
        elif request.method == 'GET':
            return await rest_client.http_get(url, params=dict(request.args))
        elif request.method == 'DELETE':
            return await rest_client.http_delete(url)
        raise Exception('unexpected http method: ' + request.method)

    def __validate_request_node(self, browser, os_system):
        #  TODO: For future
        # if not re.compile(r'(?i)^(chrome|ie|edge|safari|firefox|phantomjs|opera)$').match(browser):
        #     raise ValidationError('Browser is not support')
        # if not re.compile(r'(?i)^(unix|linux|windows|win)$').match(os_system):
        #     raise ValidationError('OS system is not support')
        if not re.compile(r'(?i)^(chrome|firefox|phantomjs)$').match(browser):
            raise ValidationError('Browser {} is not supported'.format(browser))
        if not re.compile(r'(?i)^(unix|linux)$').match(os_system):
            raise ValidationError('OS System {} is not supported'.format(os_system))
        return browser.lower(), os_system.upper()

    async def __check_node_browser_available(self, browser, os_system):
        # TODO: lookup DB to get all node with browser name and os_system
        container_id, selenium_node_id = self.database.find_selenium_node(browser, os_system)
        state = State.NOT_AVAILABLE if not container_id else await self.verify_node_status(selenium_node_id)
        return state, container_id, selenium_node_id

    def __get_docker_container_ip(self, container_id):
        for count in range(self.retry):
            try:
                status_code, resp = self.docker_client.inspect_container(container_id)
                if status_code:
                    return resp['NetworkSettings']['Networks']['bridge']['IPAddress']
            except RequestError:
                _LOG.debug('Get Docker container %s internal IP #%d', container_id, count)
            time.sleep(self.interval)
        raise RequestError('Failure to get docker internal ip')
