from selenium.webdriver import DesiredCapabilities, Remote

capabilities = DesiredCapabilities.FIREFOX.copy()
capabilities['platform'] = "LINUX"
# capabilities['applicationName'] = 'firefox_6e20c0fa1c'
driver = Remote('http://172.28.128.3:5000/node/wd/hub', desired_capabilities=capabilities)
# driver = Remote('http://172.28.128.3:4444/wd/hub', desired_capabilities=capabilities)
driver.get('https://google.com')
print(driver.title)
assert 'Google' == driver.title
