# Selenium Container Autoscale

This project provides an easy way to set up an autoscaling container-hosted selenium service. It works by proxying selenium's http (JSONWire)
requests to containers that run browser instances, spinning up new containers dynamically, reusing browsers instances that have been
released and shutting down idle containers.

It currently only works with Firefox hosted on hyper.sh containers but may expand to other browsers and container hosts in future.

This is a work in progress and so should be used with some caution. In particular it may be prone to race conditions when
launching lots of instances concurrently.

## Getting Started

### Prerequisites

hyper.sh cli:  https://console.hyper.sh/cli/download  (you will need to sign up, the free tier will not be sufficient)

docker:        https://docs.docker.com/engine/installation/  if you wish to modify and build this project

### Setup

#### Configure hyper.sh credentials

Go to https://console.hyper.sh/account/credential and click 'Create credential' and save the keys somewhere safe.

Set environment variables and run hyper config:
```
hyper config --accesskey $HYPERSH_ACCESS_KEY --secretkey $HYPERSH_SECRET --default-region $HYPERSH_REGION
```

### Running

Running the service is easy. 1) Pull the docker images 2) create a public IP address and 3) run the proxy container and attach the IP address

1) Pull the images for the proxy and selenium nodes into your hyper.sh account:
```
hyper pull eventjumbler/selenium-proxy
hyper pull eventjumbler/selenium-node
```

2) Create a public IP address (note: hyper.sh charges $1/month per address). We need an IP for the proxy if we're running our tests/clients outside of hyper.sh's network.
```
hyper fip allocate 1
hyper fip ls   # returns your new IP
```

3) Run the proxy container and attach the IP address
```
hyper run -p 5000:5000 -d --name seleniumproxy eventjumbler/selenium-proxy
hyper fip attach <ip_address> seleniumproxy
```

#### Testing that it's running

```
hyper ps -a

CONTAINER ID        IMAGE                                COMMAND             CREATED             STATUS              PORTS                    NAMES                    PUBLIC IP
c268a11ea31f        eventjumbler/selenium-proxy          "/bin/bash"         3 minutes ago       Up 3 minutes        0.0.0.0:5000->5000/tcp   seleniumproxy            <ip_address>


curl http://<ip_address>:5000/test/

success!
```

### Creating a selenium browser instance

In python you would do:

```
>>> from selenium.webdriver import DesiredCapabilities, Remote
>>> capabilities = DesiredCapabilities().FIREFOX
>>> driver = Remote('http://<ip_address>:5000/driver/wd/hub', desired_capabilities=capabilities)
>>> driver.get('https://google.com')
>>> driver.title
'Google'
```

Now we will be able to see that hyper.sh has launched a new container:

```
hyper ps -a

CONTAINER ID        IMAGE                                COMMAND             CREATED             STATUS              PORTS                    NAMES                    PUBLIC IP
c268a11ea31f        eventjumbler/selenium-proxy          "/bin/bash"         3 minutes ago       Up 3 minutes        0.0.0.0:5000->5000/tcp   seleniumproxy            <ip_address>
530a67042f52        eventjumbler/selenium-node           "/bin/bash"         2 minutes ago       Up 2 minutes        0.0.0.0:5000->5000/tcp   seleniumnode33shj34j3a
```

Note: the system is configured to run up to 3 Firefox instances per "M2" (dual-core, 2GB RAM) container so creating another Remote driver won't spin up another container.

When a driver is quit, the proxy will keep it for later reuse:
```
>>> driver.session_id
'0eded26f-06af-af4f-84b2-13b689385499'
>>> driver.quit()
>>> driver = Remote('http://<ip_address>:5000/driver/wd/hub', desired_capabilities=capabilities)  # notice how quickly this returns!
>>> driver.session_id
'0eded26f-06af-af4f-84b2-13b689385499'   # same as above
```

### Shutting it all down

This will shutdown all the selenium containers but keep the main proxy service running on the public IP address
```
curl -X POST http://<ip_address>:5000/shutdown_nodes/
```

Or to remove ALL of your containers completely do:
```
hyper rm -f `hyper ps -aq`
```

## Building and deploying from the source code

First, create a new public Docker repository at: https://hub.docker.com

Set the following environment variables
```
export HYPERSH_ACCESS_KEY=<your_access_key>
export HYPERSH_SECRET=<your_secret_key>
export HYPERSH_REGION=eu-central-1  # or us-west-1
```

Build the container and push to your docker repository:
```
./build_docker.sh <repo_path>       # <repo_path> will be something like: myaccount/myrepo
```

Pull the image into hyper.sh
```
hyper pull <repo_path>
hyper pull eventjumbler/selenium-node
```

You can also build your own version of the node servers:
```
export SELENIUM_NODE_IMAGE=<docker_repo_for_node_image>
git clone https://github.com/eventjumbler/selenium-container-node.git
cd selenium-container-node
./build_docker.sh <repo_for_node_image>
```

## Limitations

* Limited to the firefox browser and hyper.sh hosting

* The system is hard-coded to use hyper.sh's M2 (2 CPU cores, 2GB RAM) container instances for selenium nodes with a maximum of three Firefox instances per container.

* The proxy server only runs in a single process and so cannot take advantage of multiple cores on its host container. This was necessary in order to gain access to
the asyncio event loop that Sanic uses. I'm open to suggestions on how to fix this. Each process could run on a separate port and perhaps be routed to by nginx, but
the state stored in AppLogic would have to be shared somehow.


## Known Issues

* Dockerfile installation items don't have any versions set, so the build risks breaking in future.

* Container auto-shutdown is not implemented yet. Ideally selenium nodes would detect that no requests have arrived in quite a while and shut themselves down.

* It doesn't fail gracefully when you exceed your hyper.sh container quota. This is max 10 containers by default, to increase this you need to request a quota increase with them.

* Each selenium node runs selenium grid's hub, which is unnecessary. This is simply how I initially got it running during development and haven't changed it yet. I'm guessing the hub can run on the proxy server.

* No documentation for building your own version of: https://github.com/eventjumbler/selenium-container-node  (though it shouldn't be too hard: clone repo, run build_docker.sh, set the SELENIUM_NODE_IMAGE environment variable and rebuild the image for the proxy server)

## Contributing

There is no process for this yet but I would love some help! Please contact me on: digiology(_at_)gmail.com to discuss anything you'd like to improve.

## License

This project is licensed under the MIT License - see the LICENSE.txt file for details

## Acknowledgments

* Hyper.sh for being awesome : )