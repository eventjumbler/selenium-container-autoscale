

from main.main import sys_call

PROXY_IP = '185.207.112.221'
NODE_IP = '185.207.112.31'



#CAPABILITIES = {'desired_capabilities': {'platform': 'ANY', 'browserName': 'firefox', 'marionette': True, 'javascriptEnabled': True}}
#CAPABILITIES = {"capabilities": {"firstMatch": [{}], "alwaysMatch": {"browserName": "firefox"}}, "desiredCapabilities": {"javascriptEnabled": True, "marionette": True, "platform": "ANY", "browserName": "firefox", }}
#CAPABILITIES = {"capabilities": {"firstMatch": [{}], "alwaysMatch": {"browserName": "firefox"}}, "desiredCapabilities": {"javascriptEnabled": True, "marionette": True, "platform": "ANY", "browserName": "firefox", "version": ""}}


def setup_proxy_mode():
    sys_call('hyper rm -f seleniumproxy')

    sys_call('hyper run -p 5000:5000 -d --name seleniumproxy eventjumbler/selenium-proxy')
    sys_call('hyper fip attach %s seleniumproxy' % PROXY_IP)


def setup_node_mode():
    sys_call('hyper rm -f seleniumnode')
    sys_call('hyper run -p 5555:5555 -p 4444:4444 -d --name seleniumnode --size M2 eventjumbler/selenium-node')
    sys_call('hyper fip attach %s seleniumnode' % NODE_IP)

