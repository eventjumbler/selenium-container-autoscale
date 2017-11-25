FROM selenium/hub:3.7.1
LABEL authors="zero <sontt246@gmail.com>"

USER root

## Python and Utilities
RUN apt-get update \
    && apt-get install -qqy --no-install-recommends software-properties-common build-essential libssl-dev libffi-dev net-tools git cron rsyslog supervisor \
    && add-apt-repository ppa:jonathonf/python-3.6 \
    && apt-get update \
    && apt-get install -qqy --no-install-recommends python3.6 python3.6-dev \
    && python3.6 --version \
    && wget https://bootstrap.pypa.io/get-pip.py -P /tmp/ \
    && python3.6 /tmp/get-pip.py \
    && sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.5 2 \
    && sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.6 1 \
    && sudo rm /usr/bin/python3 \
    && sudo ln -s python3.6 /usr/bin/python3

ENV PYTHONIOENCODING=utf-8

# HyperSh
ENV HYPERSH_ACCESS_KEY ""
ENV HYPERSH_SECRET ""
ENV HYPERSH_REGION ""
# Remove it after using all REST API of hyper
RUN wget https://hyper-install.s3.amazonaws.com/hyper-linux-x86_64.tar.gz -P /tmp/ \
    && tar -xzf /tmp/hyper-linux-x86_64.tar.gz -C /usr/bin/

# Supervisor
RUN mkdir -p /var/log/supervisor \
    && mkdir -p /etc/supervisor/conf.d
ENV SUPERVISOR_CFG /etc/supervisor.conf
ADD conf/supervisor.conf ${SUPERVISOR_CFG}

# SELENIUM PROXY SERVER
RUN mkdir -p /opt/selenium-proxy
WORKDIR /opt/selenium-proxy
ADD jumbler/ jumbler/
ADD setup.py setup.py
ADD requirements.txt requirements.txt
ADD README.md README.md
ADD LICENSE.txt LICENSE.txt
RUN pip3 install . --upgrade --process-dependency-links
ADD startup.sh startup.sh
RUN chmod a+x startup.sh

ENV PROXY_MODE ""
ENV PROXY_SELENIUM_ENDPOINT ""
ENV PROXY_DEBUG ""
EXPOSE 5000

ENTRYPOINT ["./startup.sh"]