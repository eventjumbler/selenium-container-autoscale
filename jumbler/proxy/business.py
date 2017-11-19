import logging
import re

from hypersh_client.main.hypersh import HypershClient

import proxy.cmd_utils as cmd_utils
import proxy.util as util
from proxy.selenium import Selenium, Status

from exception import ValidationError, RequestError

_LOG = logging.getLogger(__name__)


class BusinessLogic(object):

    def __init__(self, asyncio_loop):
        self.loop = asyncio_loop
        self.docker_client = HypershClient()
        self.proxy_container_id = cmd_utils.get_host()
        self.proxy_container_ip = self.__get_docker_container_ip(self.proxy_container_id)
        self.selenium = Selenium(self.loop, self.docker_client)

    async def start_node(self, browser, os_system):
        if not re.compile(r'(?i)^(chrome|firefox|phantomjs)$').match(browser):
            raise ValidationError('Browser {} have not yet supported'.format(browser))
        if not re.compile(r'(?i)^(unix|linux)$').match(os_system):
            raise ValidationError('OS System {} have not yet supported'.format(os_system))
        status, selenium_node_id = await self.__check_node_browser_available(browser, os_system)
        if status in (Status.NOT_AVAILABLE, Status.RUNNING):
            # Create new selenium node with browser and generated id
            node_id = browser + util.uuid(10)
            return self.selenium.start_new_node(self.proxy_container_id, browser, node_id)
        if status is Status.OFF:
            return self.docker_client.start_container(selenium_node_id)

    async def verify_node_status(self, selenium_node_id):
        return self.selenium.verify_node_status(self.proxy_container_ip, selenium_node_id)

    async def stop_node(self, selenium_node_id):
        pass

    async def __check_node_browser_available(self, browser, os_system):
        # TODO: lookup DB to get all node with browser name and os_system
        selenium_node_id = ''
        status = Status.NOT_AVAILABLE if not selenium_node_id else await self.verify_node_status(selenium_node_id)
        return status, selenium_node_id

    def __get_docker_container_ip(self, container_id):
        status_code, resp = self.docker_client.inspect_container(container_id)
        if not status_code:
            raise RequestError('Failure to get docker internal ip')
        return resp['NetworkSettings']['Networks']['IPAddress']
