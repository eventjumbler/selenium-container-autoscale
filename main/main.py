import re
import asyncio
from signal import signal, SIGINT
from uuid import uuid4

from sanic import Sanic
from sanic.exceptions import SanicException
from sanic.response import json as json_resp
from sanic.response import text as text_resp
from sanic.response import HTTPResponse
from proxy.driver_responses import new_driver_resp, quit_response
from proxy.logic import AppLogic, ping_wait
import json
import datetime

NEW_DRIVER = 0
GET_COMMAND = 1
QUIT_COMMAND = 2
OTHER = 3
SESSION_ID_REGEXP = r'/(?P<selenium_id>\w{8}-\w{4}-\w{4}-\w{4}-\w{12})'

#PRODUCTION = True
#HYPER_FIP = '199.245.57.93'

sanic_app = Sanic(__name__)


def uuid(len):
    return uuid4().hex[:len]


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
    await ping_wait('google.com', loop, wait=20)
    end = datetime.datetime.now()
    print('ping took:')
    print(end-start)
    return text_resp('test_view')


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

    request_type = driver_request_type(driver_url, request.method)
    body_str = request.body.decode()

    selenium_id = None
    if request_type != NEW_DRIVER:

        selenium_id = get_session_id(driver_url, body_str)

    if request_type == NEW_DRIVER:

        reuse_session = json.loads(body_str).get('reuse_session')  # often None

        start = datetime.datetime.now()
        success, driver_dict = await app_logic.launch_driver(reuse_session or None)
        # success, driver_dict = await loop.run_in_executor(   # or: await asyncio.wait_for(future, timeout, loop=loop)
        #     None, app_logic.launch_driver, (reuse_session or None)
        # )
        end = datetime.datetime.now()
        print('launch_driver took: %s ' % (end-start))

        if success:
            return new_driver_resp(driver_dict['selenium_session_id'])

        raise SanicException('Container launch failed', 500)

    # elif request_type == GET_COMMAND:
    #     pass
        # too complex, lets leave this out
        # retry_count = 0
        # while app_logic.drivers[driver_id]['state'] == 'PAGE_GET_IN_PROGRESS' and retry_count < 100:
        #     await asyncio.sleep(0.2); retry_count += 1
        #
        # if app_logic.drivers[driver_id]['state'] == 'PAGE_GET_SUCCESS':
        #     return page_get_response(app_logic.drivers[driver_id]['selenium_session_id'])
        # elif app_logic.drivers[driver_id]['state'] == 'PAGE_GET_FAILED':
        #     return page_get_response(app_logic.drivers[driver_id]['selenium_session_id'], 'error')

        # otherwise, continue as normal and proxy request below

    if request_type == QUIT_COMMAND:
        await app_logic.quit_driver(selenium_id)
        return quit_response(selenium_id)

    container_name = app_logic.drivers[selenium_id]['container']
    url = 'http://' + container_name + ':5555/' + driver_url
    sess = app_logic.drivers[selenium_id]['aiohttp_session']

    # resp = await loop.run_in_executor(
    #     None, do_selenium_request, (request, sess, url)
    # )
    # if request.method == 'POST':
    #     resp = await loop.run_in_executor(None, sess.post, (url, request.body))
    #     # resp = sess.post(url, data=request.body)
    # elif request.method == 'GET':
    #     resp = await loop.run_in_executor(None, sess.get, (url, request.body))
    #     resp = sess.get(url, params=dict(request.args))
    # elif request.method == 'DELETE':
    #     resp = sess.delete(url)

    # to read: http://mahugh.com/2017/05/23/http-requests-asyncio-aiohttp-vs-requests/
    # to read: https://gist.github.com/snehesht/c8ef95850c550dc47126
    # need an asyn version of requests.get()  (possibility: https://stackoverflow.com/questions/22190403/how-could-i-use-requests-in-asyncio and client example here: https://aiohttp.readthedocs.io/en/stable/)
    # todo: I think this is what it needs: https://aiohttp.readthedocs.io/en/stable/client_reference.html

    #return text_resp(resp.content.decode(), 200)

    resp = await do_selenium_request(request, sess, url)
    #return json_resp(await resp.read())
    return HTTPResponse((await resp.read()).decode(), status=200, content_type="application/json")


async def do_selenium_request(request, sess, url):  # todo: what about http headers?
    if request.method == 'GET':
        resp = await sess.get(url,  params=dict(request.args))
    elif request.method == 'POST':
        resp = await sess.post(url, data=request.body)
    elif request.method == 'DELETE':
        resp = await sess.delete(url)
    return resp


# old ver:
# async def do_selenium_request(request, sess, url):
#     if request.method == 'POST':
#         resp = sess.post(url, data=request.body)
#     elif request.method == 'GET':
#         resp = sess.get(url, params=dict(request.args))
#     elif request.method == 'DELETE':
#         resp = sess.delete(url)
#     return resp

from proxy.logic import sys_call

if __name__ == '__main__':
    # from django.core.wsgi import get_wsgi_application
    # django_application = get_wsgi_application()

    # from data.models import Driver
    # for driver_obj in Driver.objects.filter(status='active'):
    #     app.driver_container_map[driver_obj.id] = driver_obj.node.container_name
    # app.run(host="0.0.0.0", port=5000, debug=True, workers=1)

    # another method for starting server, gives access to the event loop NOTE: this way doesn't support multiple processes
    server = sanic_app.create_server(host="0.0.0.0", port=5000, debug=True)  # num_workers?
    loop = asyncio.get_event_loop()

    succ, container_id, err = sys_call('hostname')
    if succ is False:
        exit('failed to get container_id')
    if not container_id.strip():
        container_id = uuid(10)
        print('warning: container_id is blank (are you running outside a container?), generating false id: %s' % container_id)

    app_logic = AppLogic(loop, container_id)

    task = asyncio.ensure_future(server)
    signal(SIGINT, lambda s, f: loop.stop())

    try:
        loop.run_forever()
    except:
        loop.stop()
