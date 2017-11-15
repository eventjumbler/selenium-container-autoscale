FROM selenium/hub:3.6.0
LABEL authors="zero <sontt246@gmail.com>"

USER root

## Python and Utilities
RUN apt-get update --fix-missing \
    && apt-get install -y python3-pip python3-dev vim wget iputils-ping \
    && apt-get install -y git cron rsyslog supervisor

# HyperSh
ENV HYPERSH_ACCESS_KEY ""
ENV HYPERSH_SECRET ""
ENV HYPERSH_REGION ""
RUN wget https://hyper-install.s3.amazonaws.com/hyper-linux-x86_64.tar.gz \
    && tar -xzf hyper-linux-x86_64.tar.gz -C /usr/bin/

# Supervisor
RUN mkdir -p /var/log/supervisor \
    && mkdir -p /etc/supervisor/conf.d
ENV SUPERVISOR_CFG /etc/supervisor.conf
ADD conf/supervisor.conf ${SUPERVISOR_CFG}

# SELENIUM PROXY SERVER
ENV APP_PATH selenium-proxy
WORKDIR ${APP_PATH}
ADD jumbler/ jumbler/
ADD setup.py setup.py
ADD requirements.txt requirements.txt
ADD README.md README.md
ADD LICENSE.txt LICENSE.txt
RUN pip3 install . --upgrade --process-dependency-links
ADD startup.sh startup.sh
RUN chmod a+x startup.sh
# Need configuartion
EXPOSE 5000

ENTRYPOINT ["./startup.sh"]