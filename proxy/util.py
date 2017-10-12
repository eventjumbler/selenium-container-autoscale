import re
import subprocess
import os
import time
import traceback
import sys
import aiohttp


SIMULATION_MODE = False


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
            {'container_id': id, 'status':status, 'name': name, 'image': container_image}
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
            {'container_id': id, 'status':status, 'name': name, 'image': container_image}
        )
    return container_details


async def is_online(container_name, wait=9):
    num_loops = round(wait / 0.3)
    #host = container_name if PRODUCTION else HYPER_FIP
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


async def http_get(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status not in (200, 201, 204):
                return resp.status, None
            return 200, (await resp.json())

'''
async def http_get(url, session=None):
    if session is None:
        session = aiohttp.ClientSession()
    with async_timeout.timeout(5):
        async with session.get(url) as response:
            if response.status != 200:
                return response.status, None
            return 200, (await response.json())
'''

async def http_post(url, data=None, json=None, session=None):
    if data is None and json is None:
        raise Exception('http_post: data is None and json is None')

    async with aiohttp.ClientSession() as session:
        async with session.post(url, data=data, json=json) as resp:
            if resp.status not in (200, 201, 204):
                return resp.status, None
            return 200, (await resp.json())

#
# async def http_post(url, data=None, json=None, session=None):
#     if data is None and json is None:
#         raise Exception('http_post: data is None and json is None')
#     if session is None:
#         session = aiohttp.ClientSession()
#     with async_timeout.timeout(5):
#         async with session.post(url, data=data, json=json) as response:
#             if response.status != 200:
#                 return response.status, None
#             return 200, (await response.json())