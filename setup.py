import re
import pip
from setuptools import setup, find_packages


_LINKS = []  # for repo urls (dependency_links)
_REQUIRES = []  # for package names


def __normalize(req):
    # Strip off -dev, -0.2, etc.
    match = re.search(r'^(.*?)(?:-dev|-\d.*)$', req)
    return match.group(1) if match else req

requirements = pip.req.parse_requirements(
    'requirements.txt', session=pip.download.PipSession()
)

for item in requirements:
    has_link = False
    if getattr(item, 'url', None):
        _LINKS.append(str(item.url))
        has_link = True
    if getattr(item, 'link', None):
        _LINKS.append(str(item.link))
        has_link = True
    if item.req:
        req = str(item.req)
        _REQUIRES.append(__normalize(req) if has_link else req)

print(find_packages(exclude=['tests']))

setup(
    name='jumbler',
    version='1.0.0.dev1',
    url='https://github.com/eventjumbler/selenium-container-autoscale',
    author='ross|zero',
    author_email='digiology@gmail.com|sontt246@gmail.com',
    license="MIT",
    description="Selenium auto scale based on Hyper",
    packages=find_packages(exclude=['tests']),
    install_requires=_REQUIRES,
    dependency_links=_LINKS,
    entry_points={
        'console_scripts': [
            'jumbler=jumbler:main',
        ],
    },
    zip_safe=False
)
