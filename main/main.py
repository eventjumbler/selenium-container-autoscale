import re
import asyncio
import logging
from signal import signal, SIGINT

from sanic import Sanic
from sanic.response import json as json_resp
from sanic.response import text as text_resp

from proxy.driver_responses import new_driver_resp, quit_response
from proxy.logic import AppLogic, sys_call
from proxy.util import uuid, PORT, get_session_id


NEW_DRIVER = 0
GET_COMMAND = 1
QUIT_COMMAND = 2
OTHER = 3


sanic_app = Sanic(__name__)
sanic_app.config.REQUEST_TIMEOUT = 90  # default is 60


def driver_request_type(driver_url, method):
    if method == 'POST' and driver_url == 'wd/hub/session':
        return NEW_DRIVER
    elif method == 'POST' and re.search(r'wd/hub/session/[a-z0-9-]+?/url', driver_url) is not None:
        return GET_COMMAND
    elif method == "DELETE" and driver_url.startswith('wd/hub/session/'):
        return QUIT_COMMAND
    else:
        return OTHER


@sanic_app.route('/test/', methods=['GET'])
async def test_view(request):
    return text_resp('success!')


@sanic_app.route('/shutdown_nodes/', methods=['POST'])
async def shutdown_nodes(request):
    app_logic.shutdown_nodes()
    return text_resp('success!')


@sanic_app.route('/container/<container_name:[A-z0-9_]{7,15}>', methods=['DELETE'])
async def notify_node_shutdown(request, container_name):
    app_logic.notify_container_down(container_id)
    return text_resp('success!')


@sanic_app.route('/driver/<driver_url:path>', methods=['GET', 'POST', 'DELETE'])
async def query_driver(request, driver_url):

    if '//' in driver_url:
        driver_url = driver_url.replace('//', '/')

    request_type = driver_request_type(driver_url, request.method)

    if request_type == NEW_DRIVER:
        # old: reuse_session = json.loads(body_str).get('reuse_session')
        body_str = request.body.decode()
        success, new_created, driver_dict = await app_logic.launch_driver(body_str)

        if not success:
            return json_resp(driver_dict['creation_resp_json'], status=500)

        return json_resp(driver_dict['creation_resp_json'], 200)

    elif request_type == QUIT_COMMAND:
        selenium_id = get_session_id(driver_url, request.body.decode())
        await app_logic.quit_driver(selenium_id)
        return quit_response(selenium_id)

    return await app_logic.proxy_selenium_request(request, driver_url)


if __name__ == '__main__':
    logging.getLogger('asyncio').setLevel(logging.WARNING)

    # NOTE: this way doesn't support multiple processes but gives you access to the event loop
    server = sanic_app.create_server(host="0.0.0.0", port=5000, debug=True, log_config=None)

    loop = asyncio.get_event_loop()

    succ, container_id, err = sys_call('hostname')
    if succ is False :
        print('failed to get container_id')
    if succ is False or not container_id.strip():
        container_id = uuid(10)
        print('warning: no container_id found, (are you running outside a container?), generating false id: %s' % container_id)

    app_logic = AppLogic(loop, container_id)

    task = asyncio.ensure_future(server)
    signal(SIGINT, lambda s, f: loop.stop())

    try:
        loop.run_forever()
    except:
        loop.stop()
