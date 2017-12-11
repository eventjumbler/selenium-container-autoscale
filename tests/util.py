import os

from main.main import sys_call

PROXY_IP = '185.207.112.221'
NODE_IP = '185.207.112.31'


#CAPABILITIES = {'desired_capabilities': {'platform': 'ANY', 'browserName': 'firefox', 'marionette': True, 'javascriptEnabled': True}}
#CAPABILITIES = {"capabilities": {"firstMatch": [{}], "alwaysMatch": {"browserName": "firefox"}}, "desiredCapabilities": {"javascriptEnabled": True, "marionette": True, "platform": "ANY", "browserName": "firefox", }}
#CAPABILITIES = {"capabilities": {"firstMatch": [{}], "alwaysMatch": {"browserName": "firefox"}}, "desiredCapabilities": {"javascriptEnabled": True, "marionette": True, "platform": "ANY", "browserName": "firefox", "version": ""}}


def setup_proxy_mode():
    sys_call('hyper rm -f seleniumproxy')

    sys_call('hyper run -p 5000:5000 -d --name seleniumproxy -e HYPERSH_ACCESS_KEY=%s -e HYPERSH_SECRET=%s -e HYPERSH_REGION=%s eventjumbler/selenium-proxy' %
        (os.environ['HYPERSH_ACCESS_KEY'], os.environ['HYPERSH_SECRET'], os.environ['HYPERSH_REGION'])
    )

    # hyper run -p 5000:5000 -d --name seleniumproxy -e HYPERSH_ACCESS_KEY=$HYPERSH_ACCESS_KEY -e HYPERSH_SECRET=$HYPERSH_SECRET -e HYPERSH_REGION=$HYPERSH_REGION eventjumbler/selenium-proxy

    sys_call('hyper fip attach %s seleniumproxy' % PROXY_IP)


def setup_node_mode():
    sys_call('hyper rm -f seleniumnode')
    sys_call('hyper run -p 5555:5555 -p 4444:4444 -d --name seleniumnode --size M2 eventjumbler/selenium-node')
    sys_call('hyper fip attach %s seleniumnode' % NODE_IP)

