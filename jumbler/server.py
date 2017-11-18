import asyncio
import logging
import re
from signal import SIGINT, signal

import proxy.cmd_utils as cmd_utils
from exception import BusinessError, ValidationError
from proxy.business import BusinessLogic
from proxy.driver_responses import quit_response
from proxy.logic import AppLogic
from proxy.util import get_session_id, uuid
from sanic import Sanic
from sanic.exceptions import InvalidUsage, ServerError
from sanic.response import json as json_resp
from sanic.response import text as text_resp

_LOG = logging.getLogger(__name__)


class SanicServer():
    """
    Sanic server
    """

    NEW_DRIVER = 0
    GET_COMMAND = 1
    QUIT_COMMAND = 2
    OTHER = 3

    def __init__(self, server_cfg, log_cfg):
        self.server_cfg = server_cfg
        self.sanic_app = Sanic(__name__, log_config=log_cfg)
        self.server = self.sanic_app.create_server(**server_cfg)
        self.loop = asyncio.get_event_loop()
        self.app_logic = AppLogic(self.loop)
        self.business_logic = BusinessLogic(self.loop)
        self.__config()

    def start(self):
        """
        Entry point to startup server
        """
        _LOG.info('Starting sanic server...')
        task = asyncio.ensure_future(self.server)
        signal(SIGINT, lambda s, f: self.loop.stop())
        try:
            self.loop.run_forever()
        except Exception as ex:
            _LOG.exception(ex)
            self.loop.stop()

    def __config(self):
        self.sanic_app.config.REQUEST_TIMEOUT = 90
        self.sanic_app.add_route(self.__test_view, '/test/', methods=['GET'])
        self.sanic_app.add_route(self.__shutdown_nodes, '/shutdown_nodes/', methods=['POST'])
        self.sanic_app.add_route(self.__notify_node_shutdown, '/container/<container_name:[A-z0-9_]{7,15}>', methods=['DELETE'])
        self.sanic_app.add_route(self.__query_driver, '/driver/<driver_url:path>', methods=['GET', 'POST', 'DELETE'])
        self.sanic_app.add_route(self.__start_node, '/node', methods=['POST'])
        self.sanic_app.add_route(self.__check_node_status, '/node/<node_name:[A-z0-9_]{7,15}>/status', methods=['GET'])

    def __driver_request_type(self, driver_url, method):
        if method == 'POST' and driver_url == 'wd/hub/session':
            return self.NEW_DRIVER
        elif method == 'POST' and re.search(r'wd/hub/session/[a-z0-9-]+?/url', driver_url) is not None:
            return self.GET_COMMAND
        elif method == "DELETE" and driver_url.startswith('wd/hub/session/'):
            return self.QUIT_COMMAND
        else:
            return self.OTHER

    async def __test_view(self, request):
        _LOG.info(request)
        return text_resp('success!')

    async def __shutdown_nodes(self, request):
        self.app_logic.shutdown_nodes()
        return text_resp('success!')

    async def __notify_node_shutdown(self, request, container_name):
        self.app_logic.notify_container_down(container_name)
        return text_resp('success!')

    async def __query_driver(self, request, driver_url):
        if '//' in driver_url:
            driver_url = driver_url.replace('//', '/')
        request_type = self.__driver_request_type(driver_url, request.method)
        if request_type == self.NEW_DRIVER:
            # old: reuse_session = json.loads(body_str).get('reuse_session')
            body_str = request.body.decode()
            success, _, driver_dict = await self.app_logic.launch_driver(body_str)
            if not success:
                return json_resp(driver_dict['creation_resp_json'], status=500)
            return json_resp(driver_dict['creation_resp_json'], 200)
        elif request_type == self.QUIT_COMMAND:
            selenium_id = get_session_id(driver_url, request.body.decode())
            await self.app_logic.quit_driver(selenium_id)
            return quit_response(selenium_id)
        return await self.app_logic.proxy_selenium_request(request, driver_url)

    async def __start_node(self, request):
        _LOG.info('Start node')
        browser = request.form.get('browser') if request.form else request.json['browser'] or 'firefox'
        os_system = request.form.get('os') if request.form else request.json['os'] or 'unix'
        if not re.compile(r'(?i)^(chrome|ie|edge|safari|firefox|phantomjs|opera)$').match(browser):
            raise InvalidUsage('Browser is not support')
        if not re.compile(r'(?i)^(unix|linux|windows|win)$').match(os_system):
            raise InvalidUsage('OS system is not support')
        _LOG.info(browser)
        _LOG.info(os_system)
        try:
            return await json_resp(self.business_logic.start_node(browser.lower(), os_system), status=200)
        except ValidationError as ve:
            raise InvalidUsage(ve.message)
        except BusinessError as be:
            raise ServerError(be.message)

    async def __check_node_status(self, request, node_name):
        _LOG.info('Check node %s status', node_name)
        try:
            return await json_resp(self.business_logic.verify_node_status(node_name), status=200)
        except BusinessError as be:
            raise ServerError(be.message)
