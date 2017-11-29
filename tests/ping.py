from selenium.webdriver import DesiredCapabilities, Remote

capabilities = DesiredCapabilities.FIREFOX.copy()
capabilities['platform'] = "LINUX"
# capabilities['applicationName'] = 'firefox_6e20c0fa1c'
# driver = Remote('http://172.28.128.6:5000/node/wd/hub', desired_capabilities=capabilities)
driver = Remote('http://209.177.93.75:5000/node/wd/hub', desired_capabilities=capabilities)
# driver = Remote('http://172.28.128.6:4444/wd/hub', desired_capabilities=capabilities)
driver.get('https://google.com')
print(driver.title)
assert driver.title == 'Google'
