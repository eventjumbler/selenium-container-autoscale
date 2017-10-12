from sanic.response import json as json_resp
from sanic.response import text as text_resp


def new_driver_resp(session_id):
    st = '''{
        "sessionId": "%(session_id)s",
        "state": null,
        "hCode": 1392544916,
        "value": {
            "moz:profile": "/tmp/rust_mozprofile.yF5RazbLPPcX",
            "rotatable": false,
            "timeouts": {
                "implicit": 0.0,
                "pageLoad": 300000.0,
                "script": 30000.0
            },
            "pageLoadStrategy": "normal",
            "platform": "ANY",
            "specificationLevel": 0.0,
            "moz:accessibilityChecks": false,
            "webdriver.remote.sessionid": "%(session_id)s",
            "acceptInsecureCerts": false,
            "browserVersion": "%(browser_version)s",
            "platformVersion": "4.4.62-hyper",
            "moz:processID": 65.0,
            "browserName": "firefox",
            "takesScreenshot": true,
            "javascriptEnabled": true,
            "platformName": "linux",
            "cssSelectorsEnabled": true
        },
        "class": "org.openqa.selenium.remote.Response",
        "status": 0
    }''' % {
        'browser_version': '53.0.3',  # todo: will need to be updated
        'session_id': session_id,
    }
    return text_resp(st)


def page_get_response(session_id, state='success'):  # for state strings see: https://github.com/SeleniumHQ/selenium/blob/ceaf3da79542024becdda5953059dfbb96fb3a90/third_party/closure/goog/net/eventtype.js
    return text_resp('''{
        "sessionId": "%(session_id)s",
        "state": "success",
        "hCode": 1105373391,
        "value": null,
        "class": "org.openqa.selenium.remote.Response",
        "status": 0
    }''' % {'session_id': session_id}
    )


def quit_response(session_id):
    st = '''{
        "sessionId": "%(session_id)s",
        "state": "success",
        "hCode": 225874638,
        "value": null,
        "class": "org.openqa.selenium.remote.Response",
        "status": 0
    }''' % {'session_id': session_id}
    return text_resp(st)