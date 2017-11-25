import asyncio
import logging
from subprocess import Popen, PIPE

import proxy.util as util

_LOG = logging.getLogger(__name__)

async def sys_call_async(command):
    proc = await asyncio.create_subprocess_exec(*command.split(), stdout=PIPE, stderr=PIPE)
    await proc.wait()
    stdout, stderr = await proc.communicate()
    success = proc.returncode == 0
    return success, stdout.decode(), stderr.decode()


def sys_call(cmd_str, shell=False):
    p = Popen(cmd_str.split(), stdout=PIPE, stderr=PIPE, stdin=PIPE, shell=shell, universal_newlines=True)
    stdout, stderr = p.communicate()
    success = p.returncode == 0
    return success, stdout, stderr


async def ping_wait(container_name, wait=9):
    num_loops = round(wait / 0.35)
    # host = container_name if PRODUCTION else HYPER_FIP
    command = "ping -c 1 " + container_name  # + " >/dev/null 2>&1"

    _LOG.info('num loops: %s', num_loops)

    for _ in range(num_loops):  # wait up to 9 seconds
        _LOG.info('ping!')
        success, stdout, stderr = await sys_call_async(command)

        if success:
            return True
        _LOG.info('stdout: ' + stdout)
        _LOG.info('stderr: ' + stderr)

        await asyncio.sleep(0.35)
    _LOG.info('finished pinging without succeeding')
    return False


def get_host():
    success, container_id, _ = sys_call('hostname')
    if success is False or not container_id.strip():
        _LOG.warning('Failed to get container_id. Try to generate id')
        container_id = util.uuid(10)
        _LOG.warning('No container_id found, generated id: %s', container_id)
    return container_id.strip()