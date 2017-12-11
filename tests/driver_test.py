import sys
import time

from selenium.webdriver import Remote
from tests.util import PROXY_IP, NODE_IP, setup_proxy_mode, setup_node_mode
from proxy.util import CAPABILITIES


def main():

    if len(sys.argv) != 2 or sys.argv[1] not in ('proxy', 'node'):
        exit('usage: driver_test.py <proxy|node>')

    is_proxy = sys.argv[1] == 'proxy'

    if is_proxy:
        setup_proxy_mode()
        base_url = 'http://' + PROXY_IP + ':5000/driver'
    else:
        setup_node_mode()
        base_url = 'http://' + NODE_IP + ':5555'

    time.sleep(7)
    import pdb
    pdb.set_trace()
    driver = Remote(base_url + '/wd/hub', desired_capabilities=CAPABILITIES)
    driver.get('http://soas.ac.uk')
    links = driver.find_elements_by_xpath('//a')
    curr_link = links[1]
    outer_html = curr_link.get_attribute('outerHTML')
    import pdb
    pdb.set_trace()
    print('result:')
    print(outer_html)


if __name__ == "__main__":
    main()
