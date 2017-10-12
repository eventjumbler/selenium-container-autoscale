# Selenium Container Autoscale

This project provides an easy way to set up a autoscaling container-hosted selenium service. It works by proxying selenium's http (JSONWire)
requests to containers that run browser instances, spinning up new containers dynamically, reusing browsers instances that have been
released and shutting down idle containers.

It currently only works with Firefox hosted on docker containers on hyper.sh but may expand to other browsers and container hosts in future.

This is a work in progress and so should be used with some caution. In particular, auto-shutdown has not yet been implemented so be sure to shut down
your containers when you're finished. It also has no unit tests and may be prone to race conditions when under heavy use (e.g. > 100 concurrent instances).

## Getting Started

### Prerequisites

docker:        https://docs.docker.com/engine/installation/
hyper.sh cli:  https://console.hyper.sh/cli/download  (you will need to sign up)


### Setup

#### Configure hyper.sh credentials

Go to https://console.hyper.sh/account/credential and click 'Create credential' and save the keys somewhere safe.

Set environment variables and run hyper config:
```
export HYPERSH_ACCESS_KEY=<your_access_key>
export HYPERSH_SECRET=<your_secret_key>

hyper config --accesskey $HYPERSH_ACCESS_KEY --secretkey $HYPERSH_SECRET --default-region eu-central-1    # or: us-west-1
```

#### Build, deploy and run container image

Create a Docker Repository at: https://hub.docker.com

To build the container and push to your docker repository do:

```
https://github.com/eventjumbler/selenium-container-autoscale.git
cd selenium-container-autoscale
./build_docker.sh <repo_path>       # <repo_path> will be something like: myaccount/myrepo
```

Pull the image into hyper.sh

```
hyper pull <repo_path>
```

Create a public IP address (note: hyper.sh charges $1/month per address).
We need an IP for the proxy if we're running out tests/clients outside of hyper.sh's network.

```
hyper fip allocate 1
hyper fip ls   # returns your new IP
```

Run a container and attach the IP address

```
hyper run -p 5000:5000 -d --name seleniumproxy <repo_path>   # TODO: check that main/main.py is actually launched
hyper fip attach <ip_address> seleniumproxy
```

## Test that seleniumproxy is running

```
hyper ps

CONTAINER ID        IMAGE                                COMMAND             CREATED             STATUS              PORTS                    NAMES                    PUBLIC IP
c268a11ea31f        <repo_path>                          "/bin/bash"         3 minutes ago       Up 3 minutes        0.0.0.0:5000->5000/tcp   seleniumproxy            <ip_address>


curl http://<ip_address>:5000/test/

success!
```

## Create a selenium browser instance

In python you would do:

```
>>> from selenium.webdriver import Remote
>>> desired_capabilities = {'platform': 'ANY', 'browserName': 'firefox', 'version': '', 'marionette': True, 'javascriptEnabled': True}
>>> driver = Remote('http://<ip_address>:5000/wd/hub', desired_capabilities=capabilities)
>>> driver.get('https://google.com')
>>> driver.title
'Google'
```

Now we will be able to see that hyper.sh has launched a new container:

```
hyper ps

CONTAINER ID        IMAGE                                COMMAND             CREATED             STATUS              PORTS                    NAMES                    PUBLIC IP
c268a11ea31f        <repo_path>                          "/bin/bash"         3 minutes ago       Up 3 minutes        0.0.0.0:5000->5000/tcp   seleniumproxy            <ip_address>
530a67042f52        digiology/selenium_node              "/bin/bash"         2 minutes ago       Up 2 minutes        0.0.0.0:5000->5000/tcp   seleniumnode33shj34j3a
```

Note: the system is configured to run up to 3 Firefox instances per "M2" (dual-core, 2GB RAM) container.

### Shutting down containers

This will shutdown all the selenium containers but keep the main proxy service running on the public IP address
```
curl -X POST http://<ip_address>:5000/shutdown_nodes/
```

Or to remove ALL of your containers completely do:
```
hyper rm -f `hyper ps -aq`
```

## Known Issues

* Limited to the firefox browser and hyper.sh hosting

* The system is hard-coded to use hyper.sh's M2 (2 CPU cores, 2GB RAM) container instances for selenium nodes with a maximum of three Firefox instances per container.

* Dockerfile installation items don't have any versions set, so the build risks breaking in future.

* Container auto-shutdown is not implemented yet. Ideally selenium nodes would detect that no requests have arrived in quite a while and shut themselves down.

* The proxy server only runs in a single process and so cannot take advantage of multiple cores on its host container. This was necessary in order to gain access to
the asyncio event loop that Sanic uses. I'm open to suggestions on how to fix this. Each process could run on a separate port and perhaps be routed to by nginx, but
the state stored in AppLogic would have to be shared somehow.

* New remote connections sometimes timeout when a new container needs to be launched. It simply takes too long to both launch
the container and launch a new browser instance (about 40-50 seconds). It's possible to change the timeout on the client side but
it seems to require a bit of hacking (e.g. subclassing the Remote and RemoteConnection classes). A possible solution would be to prelaunch
containers before they are required.

* It doesn't fail gracefully when you exceed your hyper.sh container quota. This is max 10 containers by default, to increase this you can contact them.

## Contributing

There is no process for this yet but I would love some help! Please contact me on: digiology(_at_)gmail.com to discuss anything you'd like to improve.

## License

This project is licensed under the MIT License - see the LICENSE.txt file for details

## Acknowledgments

* Hyper.sh for being awesome : )