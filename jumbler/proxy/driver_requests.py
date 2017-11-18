from proxy.util import CAPABILITIES


NEW_SESSION_REQ_BODY = {
    "capabilities": {
        "firstMatch": [{}],
        "alwaysMatch": {
            "acceptInsecureCerts": True,
            "browserName": "firefox"
        }
    },
    "desiredCapabilities": CAPABILITIES
}


def get_page(driver_dict, url):
    req_session = driver_dict['requests_session']
    selenium_sess_id = driver_dict['selenium_session_id']
    container = driver_dict['container']
    post_url = 'http://' + container + ':5555' + ('/wd/hub/session/%s/url' % selenium_sess_id)
    resp = req_session.post(post_url, json={'sessionId': selenium_sess_id, 'url': url})
    return resp == 200 and '"state": "success"' in resp.content.decode()


'''
# driver.get() request

POST /wd/hub/session/38f188b5-62d0-429b-b8d3-298926c9fb0b/url HTTP/1.1
Accept-Encoding: identity
User-Agent: Python http auth
Content-Length: 81
Accept: application/json
Content-Type: application/json;charset=UTF-8
Connection: close
Host: 199.245.57.93:5555

{"sessionId": "38f188b5-62d0-429b-b8d3-298926c9fb0b", "url": "http://google.com"}

'''
