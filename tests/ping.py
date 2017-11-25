from selenium.webdriver import DesiredCapabilities, Remote

capabilities = DesiredCapabilities.FIREFOX.copy()
capabilities['platform'] = "UNIX"
driver = Remote('http://172.28.128.3:5000/node/wd/hub', desired_capabilities=capabilities)
driver.get('https://google.com')
assert('Google' == driver.title)
