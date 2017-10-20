import re
import asyncio
from signal import signal, SIGINT
from uuid import uuid4
import aiohttp
from sanic import Sanic
from sanic.exceptions import SanicException
from sanic.response import json as json_resp
from sanic.response import text as text_resp
from sanic.response import HTTPResponse
from proxy.driver_responses import new_driver_resp, quit_response
from proxy.logic import AppLogic, ping_wait
import json
import datetime
import logging
from proxy.logic import sys_call
from proxy.util import uuid, PORT

NEW_DRIVER = 0
GET_COMMAND = 1
QUIT_COMMAND = 2
OTHER = 3
SESSION_ID_REGEXP = r'/(?P<selenium_id>\w{8}-\w{4}-\w{4}-\w{4}-\w{12})'


sanic_app = Sanic(__name__)
sanic_app.config.REQUEST_TIMEOUT = 90  # default is 60



def do_selenium_request(request, sess, url):
    if request.method == 'POST':
        resp = sess.post(url, data=request.body)
    elif request.method == 'GET':
        resp = sess.get(url, params=dict(request.args))
    elif request.method == 'DELETE':
        resp = sess.delete(url)
    return resp


def driver_request_type(driver_url, method):

    if method == 'POST' and driver_url == 'wd/hub/session':
        ans = NEW_DRIVER
    elif method == 'POST' and re.search(r'wd/hub/session/[a-z0-9-]+?/url', driver_url) is not None:
        ans = GET_COMMAND
    elif method == "DELETE" and driver_url.startswith('wd/hub/session/'):
        ans = QUIT_COMMAND
    else:
        ans = OTHER
    print(driver_url + ': ' + str(ans))
    return ans


@sanic_app.route('/quit_driver/', methods=['POST'])
async def quit_driver(request):
    selenium_id = json.loads(request.body.decode())['selenium_session_id']

    if selenium_id in app_logic.drivers and selenium_id not in app_logic.leftover_drivers:
        await app_logic.quit_driver(selenium_id)

    return text_resp('done')


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


def get_session_id(driver_url, body_str):
    match = re.search(SESSION_ID_REGEXP, driver_url)

    if match:
        selenium_id = match.groupdict()['selenium_id']
    elif body_str == '':
        import pdb; pdb.set_trace()
    else:
        selenium_id = json.loads(body_str)['sessionId']  # based on assumption that this will always be in the response
    return selenium_id


@sanic_app.route('/driver/<driver_url:path>', methods=['GET', 'POST', 'DELETE'])
async def query_driver(request, driver_url):

    if '//' in driver_url:
        driver_url = driver_url.replace('//', '/')

    request_type = driver_request_type(driver_url, request.method)
    body_str = request.body.decode()

    selenium_id = None
    if request_type != NEW_DRIVER:

        selenium_id = get_session_id(driver_url, body_str)

    if request_type == NEW_DRIVER:

        # old: reuse_session = json.loads(body_str).get('reuse_session')

        start = datetime.datetime.now()
        success, new_created, driver_dict = await app_logic.launch_driver(body_str)

        end = datetime.datetime.now()

        if success:
            print('launch_driver took: %s ' % (end - start))
            return json_resp(driver_dict['creation_resp_json'], 200)

        if driver_dict:
            return json_resp(driver_dict['creation_resp_json'], status=500)

        return new_driver_resp(selenium_id, error=True)

    if request_type == QUIT_COMMAND:
        print('quitting driver')
        await app_logic.quit_driver(selenium_id)
        return quit_response(selenium_id)

    container_name = app_logic.drivers[selenium_id]['container']
    url = 'http://' + container_name + ':' + PORT + '/' + driver_url
    sess = app_logic.drivers[selenium_id]['requests_session']

    # to read: http://mahugh.com/2017/05/23/http-requests-asyncio-aiohttp-vs-requests/
    # to read: https://gist.github.com/snehesht/c8ef95850c550dc47126
    # need an asyn version of requests.get()  (possibility: https://stackoverflow.com/questions/22190403/how-could-i-use-requests-in-asyncio and client example here: https://aiohttp.readthedocs.io/en/stable/)
    # todo: I think this is what it needs: https://aiohttp.readthedocs.io/en/stable/client_reference.html

    resp = await loop.run_in_executor(None, do_selenium_request, request, sess, url)
    if resp.status_code != 200:
        print('warning: selenium request gave status: %s' % resp.status_code)

    return HTTPResponse(resp.content.decode(), status=resp.status_code, content_type="application/json")

    #resp = await do_selenium_request(request, sess, url)
    #return json_resp(await resp.read())
    #return HTTPResponse((await resp.read()).decode(), status=200, content_type="application/json")


# async def do_selenium_request_old(request, sess, url):  # todo: what about http headers?
#     if request.method == 'GET':
#         #resp = await sess.get(url,  params=dict(request.args))
#
#         async with aiohttp.get(url, params=dict(request.args)) as resp:
#             if resp.status == 200:
#                 return await resp
#
#     elif request.method == 'POST':
#         #resp = await sess.post(url, data=request.body)
#
#         async with aiohttp.post(url, data=request.body) as resp:
#             if resp.status == 200:
#                 return await resp
#
#     elif request.method == 'DELETE':
#         #resp = await sess.delete(url)
#
#         async with aiohttp.delete(url) as resp:
#             if resp.status == 200:
#                 return await resp
#
#     return resp
#
#
# async def do_selenium_request(request, sess, url, ):
#     resp = None
#     if request.method == 'GET':
#         async with aiohttp.ClientSession(loop=loop) as client:
#             async with client.get(url, params=dict(request.args)) as resp:
#                 return resp
#     elif request.method == 'POST':
#         async with aiohttp.ClientSession(loop=loop) as client:
#             async with client.post(url, data=request.body) as resp:
#                 return resp
#     elif request.method == 'DELETE':
#         async with aiohttp.ClientSession(loop=loop) as client:
#             async with client.delete(url) as resp:
#                 return resp
#
#     status = resp.status if resp else None
#     raise SanicException('problem in do_selenium_request(): %s %s' % (request.method, status))


if __name__ == '__main__':
    logging.getLogger('asyncio').setLevel(logging.WARNING)

    # NOTE: this way doesn't support multiple processes but gives you access to the event loop (regular version: # app.run(host="0.0.0.0", port=5000, debug=True, workers=1))
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
