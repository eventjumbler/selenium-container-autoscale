import asyncio
from asyncio.subprocess import PIPE
from subprocess import Popen, PIPE

async def sys_call_async(command):
    proc = await asyncio.create_subprocess_exec(*command.split(), stdout=PIPE, stderr=PIPE)   # or loop.subprocess_exec?
    await proc.wait()
    stdout, stderr = await proc.communicate()
    success = proc.returncode == 0
    return success, stdout.decode(), stderr.decode()


def sys_call(cmd_str, shell=False, suppress_errors=True):
    p = Popen(cmd_str.split(), stdout=PIPE, stderr=PIPE, stdin=PIPE, shell=shell)  # stderr=PIPE,
    # p.communicate()
    stdout, stderr = p.stdout.read(), p.stderr.read()
    p.wait()
    success = p.returncode == 0
    return success, stdout, stderr


async def ping_wait(container_name, wait=9):
    num_loops = round(wait / 0.35)
    # host = container_name if PRODUCTION else HYPER_FIP
    command = "ping -c 1 " + container_name  # + " >/dev/null 2>&1"

    # command = 'ls -la sdfsdf'
    print('num loops: %s' % num_loops)

    for i in range(num_loops):  # wait up to 9 seconds
        print('ping!')
        success, stdout, stderr = await sys_call_async(command)

        if success:
            return True
        print('stdout: ' + stdout)
        print('stderr: ' + stderr)

        await asyncio.sleep(0.35)
    print('finished pinging without succeeding')
    return False
