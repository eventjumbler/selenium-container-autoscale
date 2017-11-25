import logging
import re

import dockerrest.docker_provider as docker_provider

import proxy.cmd_utils as cmd_utils
import proxy.util as util
from exception import (ExecutionError, NotFoundError, RequestError,
                       ValidationError)
from proxy.selenium_service import SeleniumService, Status

_LOG = logging.getLogger(__name__)


class BusinessLogic(object):

    def __init__(self, asyncio_loop, business_cfg):
        self.loop = asyncio_loop
        self.docker_client = docker_provider.factory(business_cfg.get('mode'), endpoint=business_cfg.get('endpoint'))
        self.proxy_container_id = cmd_utils.get_host()
        self.proxy_container_ip = self.__get_docker_container_ip(self.proxy_container_id)
        self.selenium = SeleniumService(self.loop, self.docker_client)

    async def create_node_container(self, browser, os_system):
        _LOG.info('Start Browser: %s - OS: %s', browser, os_system)
        #  TODO: For future
        # if not re.compile(r'(?i)^(chrome|ie|edge|safari|firefox|phantomjs|opera)$').match(browser):
        #     raise ValidationError('Browser is not support')
        # if not re.compile(r'(?i)^(unix|linux|windows|win)$').match(os_system):
        #     raise ValidationError('OS system is not support')
        if not re.compile(r'(?i)^(chrome|firefox|phantomjs)$').match(browser):
            raise ValidationError('Browser {} have not yet supported'.format(browser))
        if not re.compile(r'(?i)^(unix|linux)$').match(os_system):
            raise ValidationError('OS System {} have not yet supported'.format(os_system))
        status, container_id, selenium_node_id = await self.__check_node_browser_available(browser, os_system)
        _LOG.info('Node Id: %s - Node Status: %s', selenium_node_id, str(status))
        result = {'browser': browser, 'os': os_system, 'container_id': container_id, 'selenium_node_id': selenium_node_id}
        if status in (Status.NOT_AVAILABLE, Status.RUNNING):
            # Create new selenium node with browser and generated id
            result['selenium_node_id'] = browser + '_' + util.uuid(10)
            result['container_id'] = self.selenium.create_node(self.proxy_container_id, browser, result.get('selenium_node_id'))
        elif status is Status.OFF:
            success = self.docker_client.start_container(container_id)
            if not success:
                raise RequestError('Cannot start container id: %s - name: %s' % (container_id, selenium_node_id))
        elif status is Status.PENDING:
            pass
        else:
            raise ExecutionError('Not handle status: %s', str(status))
        return result

    async def verify_node_status(self, selenium_node_id):
        result = {}
        result['node'] = selenium_node_id
        result['status'] = await self.selenium.verify_node_status(self.proxy_container_ip, selenium_node_id)
        return result

    async def stop_node(self, selenium_node_id):
        pass

    async def start_selenium_node(self, capabilities):
        browser = capabilities.get('capabilities').get('alwaysMatch').get('browserName') or 'firefox'
        os_system = capabilities.get('capabilities').get('alwaysMatch').get('platformName') or 'unix'
        result = await self.create_node_container(browser.lower(), os_system.lower())
        capabilities['capabilities']['alwaysMatch']['id'] = result.get('selenium_node_id')
        capabilities['desiredCapabilities']['id'] = result.get('selenium_node_id')
        return await self.selenium.start_node(self.proxy_container_id, capabilities)

    async def __check_node_browser_available(self, browser, os_system):
        # TODO: lookup DB to get all node with browser name and os_system
        container_id = ''
        selenium_node_id = ''
        status = Status.NOT_AVAILABLE if not selenium_node_id else await self.verify_node_status(selenium_node_id)
        return status, container_id, selenium_node_id

    def __get_docker_container_ip(self, container_id):
        status_code, resp = self.docker_client.inspect_container(container_id)
        if not status_code:
            raise RequestError('Failure to get docker internal ip')
        return resp['NetworkSettings']['Networks']['bridge']['IPAddress']
