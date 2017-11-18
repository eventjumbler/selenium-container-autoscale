import asyncio
import json
import logging
import os
import re
import subprocess
import sys
import traceback
from uuid import uuid4

import aiohttp
import proxy.rest_client as rest_client
from selenium.webdriver import DesiredCapabilities

SIMULATION_MODE = False

PORT = '5555'
CAPABILITIES = DesiredCapabilities().FIREFOX
SESSION_ID_REGEXP = r'/(?P<selenium_id>\w{8}-\w{4}-\w{4}-\w{4}-\w{12})'

_LOG = logging.getLogger(__name__)


async def get_running_containers_async(loop, image=None):

    # temporary
    return await loop.run_in_executor(
        None, get_running_containers, (image,)
    )

    proc = asyncio.create_subprocess_exec('hyper', 'ps')
    stdout, stderr = await proc.communicate()
    await proc.wait()

    return_code = proc.returncode
    if not return_code:
        call_result = bytes(stdout).decode()
    else:
        raise Exception('call to hyper ps failed')

    # call_result = subprocess.run(['hyper', 'ps'], stdout=subprocess.PIPE)
    # call_result = call_result.stdout.decode()
    container_details = []
    for i, row in enumerate(call_result.split('\n')):
        if i == 0 or not row.strip():
            continue
        cols = re.findall(r'([^\s].+?[^\s])\s{3,}', row)
        id = cols[0]
        container_image = cols[1]
        status = cols[4]
        name = cols[6]
        if not status.startswith('Up '):
            continue
        if image is not None and container_image != image:
            continue
        container_details.append(
            {'container_id': id, 'status': status, 'name': name, 'image': container_image}
        )
    return container_details


def get_running_containers(image=None):
    # todo: or use:  https://docs.hyper.sh/Reference/API/2016-04-04%20[Ver.%201.23]/Container/list.html
    call_result = subprocess.run(['hyper', 'ps'], stdout=subprocess.PIPE)
    call_result = call_result.stdout.decode()
    container_details = []
    for i, row in enumerate(call_result.split('\n')):
        if i == 0 or not row.strip():
            continue
        cols = re.findall(r'([^\s].+?[^\s])\s{3,}', row)
        id = cols[0]
        container_image = cols[1]
        status = cols[4]
        name = cols[6]
        if not status.startswith('Up '):
            continue
        if image is not None and container_image != image:
            continue
        container_details.append(
            {'container_id': id, 'status': status, 'name': name, 'image': container_image}
        )
    return container_details


async def is_online(container_name, wait=9):
    num_loops = round(wait / 0.3)
    # host = container_name if PRODUCTION else HYPER_FIP
    for i in range(num_loops):  # wait up to 9 seconds
        response = os.system("ping -c 1 " + container_name + " >/dev/null 2>&1")
        if response == 0:
            return True
        asyncio.sleep(0.3)  # time.sleep(0.3)
    return False


def exception_info(e):
    """
    Gets a stack trace of an exception, useful for writing details to the report file.
    """
    except_type, except_class, tb = sys.exc_info()
    error_tuple = (except_type, except_class, traceback.extract_tb(tb))
    return error_tuple


def uuid(len):
    return uuid4().hex[:len]


def do_selenium_request(request, sess, url):
    if request.method == 'POST':
        resp = sess.post(url, data=request.body)
    elif request.method == 'GET':
        resp = sess.get(url, params=dict(request.args))
    elif request.method == 'DELETE':
        resp = sess.delete(url)
    return resp


async def do_selenium_request_async(request, sess, url):
    # todo: what about http headers?
    if request.method == 'POST':
        return await rest_client.http_post(url, data=request.body, session=sess)
    elif request.method == 'GET':
        return await rest_client.http_get(url, params=dict(request.args), session=sess)
    elif request.method == 'DELETE':
        return await rest_client.http_delete(url, session=sess)
    raise Exception('unexpected http method: ' + request.method)


def get_session_id(driver_url, body_str):
    match = re.search(SESSION_ID_REGEXP, driver_url)

    if match:
        selenium_id = match.groupdict()['selenium_id']
    elif body_str == '':
        import pdb
        pdb.set_trace()
    else:
        selenium_id = json.loads(body_str)['sessionId']  # based on assumption that this will always be in the response
    return selenium_id
