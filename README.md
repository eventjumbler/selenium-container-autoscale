# Selenium Container Autoscale

This project provides an easy way to set up an autoscaling container-hosted selenium service. It works by proxying selenium's http (JSONWire)
requests to containers that run browser instances, spinning up new containers dynamically, reusing browsers instances that have been
released and shutting down idle containers.

Currently, Selenium Hub resides with Proxy server and service will scale Selenium Node automaticaly.
It may better to separate Proxy server and Selenium Hub in future

This is a work in progress and so should be used with some caution. In particular it may be prone to race conditions when
launching lots of instances concurrently.

## Architecture
![image](https://user-images.githubusercontent.com/10863525/33980476-afc88250-e0db-11e7-9de6-326eb4ecc3a7.png)

## Getting Started

### Prerequisites

hyper.sh cli:  https://console.hyper.sh/cli/download  (you will need to sign up, the free tier will not be sufficient)

docker:        https://docs.docker.com/engine/installation/  if you wish to modify and build this project or run locally in your machine

### Setup

#### Configure hyper.sh credentials

Go to https://console.hyper.sh/account/credential and click 'Create credential' and save the keys somewhere safe.

Set environment variables and run hyper config:

```
export HYPERSH_ACCESS_KEY=<your_access_key>
export HYPERSH_SECRET=<your_secret_key>
export HYPERSH_REGION=eu-central-1  # or us-west-1

hyper config --accesskey $HYPERSH_ACCESS_KEY --secretkey $HYPERSH_SECRET --default-region $HYPERSH_REGION
```

#### Enable Docker REST API

* Create config file:
    * Centos 7
        ```bash
        sudo touch /etc/systemd/system/docker.service.d/docker.conf
        ```
    * Ubuntu 16
        ```bash
        sudo touch /lib/systemd/system/docker.service
        ```
* Update new file with content
    ```bash
    [Service]
    ExecStart=
    ExecStart=/usr/bin/dockerd -H tcp://0.0.0.0:2375 -H unix://var/run/docker.sock
    ```
* Restart docker service
    ```bash
    sudo systemctl daemon-reload
    sudo systemctl restart docker
    ```

### Running

Running the service is easy. 1) Pull the docker images 2) create a public IP address and 3) run the proxy container and attach the IP address

1) Pull the images for the proxy into your hyper.sh account:
```
hyper pull zero88/selenium-proxy
```

```
docker pull zero88/selenium-proxy
```

2) Create a public IP address (note: hyper.sh charges $1/month per address). We need an IP for the proxy if we're running our tests/clients outside of hyper.sh's network.
```
hyper fip allocate 1
hyper fip ls   # returns your new IP
```

3) Run the proxy container and attach the IP address. We'll need to pass it our hypersh keys:
* Hyper
    ```bash
    hyper run -p 5000:5000 -d --name seleniumproxy -e HYPERSH_ACCESS_KEY=$HYPERSH_ACCESS_KEY -e HYPERSH_SECRET=$HYPERSH_SECRET -e HYPERSH_REGION=$HYPERSH_REGION zero88/selenium-proxy
    hyper fip attach <ip_address> seleniumproxy
    ```

* Docker: Due to some changes of code, will remove `HYPER_*` parameter later
    ```bash
    docker run -p 5000:5000 -d --name seleniumproxy -e PROXY_MODE="docker" -e PROXY_SELENIUM_ENDPOINT="http://172.28.128.6:2375" -e HYPERSH_ACCESS_KEY=$HYPERSH_ACCESS_KEY -e HYPERSH_SECRET=$HYPERSH_SECRET -e HYPERSH_REGION=$HYPERSH_REGION zero88/selenium-proxy
    ```

`PROXY_MODE` default is hypersh. Available values: `docker|hypersh`

#### Testing that it's running

```bash
hyper ps -a

CONTAINER ID        IMAGE                                COMMAND             CREATED             STATUS              PORTS                    NAMES                    PUBLIC IP
c268a11ea31f        zero88/selenium-proxy               "./startup.sh"         3 minutes ago       Up 3 minutes      0.0.0.0:5000->5000/tcp   selenium-proxy            <ip_address>


curl http://<ip_address>:5000/test/

success!
```

### Creating a selenium browser instance

In python you would do:

```python
>>> from selenium.webdriver import DesiredCapabilities, Remote
>>> capabilities = DesiredCapabilities().FIREFOX
>>> driver = Remote('http://<ip_address>:5000/node/wd/hub', desired_capabilities=capabilities)
>>> driver.get('https://google.com')
>>> driver.title
'Google'
```

Now we will be able to see that hyper.sh/docker has launched a new container:

```bash
hyper ps -a

CONTAINER ID        IMAGE                                COMMAND                CREATED             STATUS              PORTS                       NAMES                    PUBLIC IP
c268a11ea31f        zero88/selenium-proxy               "./startup.sh"          3 minutes ago       Up 3 minutes        0.0.0.0:5000->5000/tcp      selenium-proxy           <ip_address>
530a67042f52        selenium/node-firefox:latest        "/opt/bin/entry_point"  2 minutes ago       Up 2 minutes                                    firefox-3902c6ad1e
```

Note: the system is configured to run up to 3 Firefox instances per "M2" (dual-core, 2GB RAM) container so creating another Remote driver won't spin up another container.

When a driver is quit, the proxy will keep it for later reuse:
```python
>>> driver.session_id
'0eded26f-06af-af4f-84b2-13b689385499'
>>> driver.quit()
>>> driver = Remote('http://<ip_address>:5000/driver/wd/hub', desired_capabilities=capabilities)  # notice how quickly this returns!
>>> driver.session_id
'0eded26f-06af-af4f-84b2-13b689385499'   # same as above
```

### Shutting it all down

This will shutdown all the selenium containers but keep the main proxy service running on the public IP address
```bash
curl -X POST http://<ip_address>:5000/shutdown_nodes/
```

Or to remove ALL of your containers completely do:
```bash
hyper rm -f `hyper ps -aq`
```

## Building and deploying from the source code

First, create a new public Docker repository at: https://hub.docker.com

* Build the container and push to your docker repository:
```bash
./build_docker.sh <repo_path>       # <repo_path> will be something like: myaccount/myrepo
```

* Pull the image into hyper.sh
```bash
hyper pull <repo_path>
hyper pull zero88/selenium-proxy
```

## Limitations

* Limited to the firefox browser and hyper.sh hosting

* The system is hard-coded to use hyper.sh's M2 (2 CPU cores, 2GB RAM) container instances for selenium nodes with a maximum of three Firefox instances per container.

* The proxy server only runs in a single process and so cannot take advantage of multiple cores on its host container. This was necessary in order to gain access to
the asyncio event loop that Sanic uses. I'm open to suggestions on how to fix this. Each process could run on a separate port and perhaps be routed to by nginx, but
the state stored in AppLogic would have to be shared somehow.

* Still use hypersh CLI because hyper REST API issues: [#689](https://github.com/hyperhq/hyperd/issues/689)

* Docker provider can be expanded on some cloud services such as: AWS, GCP, Azure by enhance [docker-rest](https://github.com/zero-88/docker_rest)

* Allocate worker process for Docker provider.


## Known Issues

* Dockerfile installation items don't have any versions set, so the build risks breaking in future.

* Container auto-shutdown is not implemented yet. Ideally selenium nodes would detect that no requests have arrived in quite a while and shut themselves down. This is partially implemented here: https://github.com/eventjumbler/selenium-container-node/blob/master/detect_idle.py but needs testing more and to be run as a cron job.

* It doesn't fail gracefully when you exceed your hyper.sh container quota. This is max 10 containers by default, to increase this you need to request a quota increase with them.

## Contributing

There is no process for this yet but I would love some help! Please contact me on: digiology(_at_)gmail.com to discuss anything you'd like to improve.

## License

This project is licensed under the MIT License - see the LICENSE.txt file for details

## Acknowledgments

* Hyper.sh for being awesome : )