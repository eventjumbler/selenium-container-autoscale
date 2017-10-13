FROM ubuntu:16.04

RUN apt-get update --fix-missing
RUN apt-get install -y python3-pip python3-dev vim wget iputils-ping
RUN apt-get update --fix-missing
RUN apt-get install -y git cron rsyslog supervisor

ADD ./requirements.txt /requirements.txt
RUN pip3 install -r requirements.txt

RUN wget https://hyper-install.s3.amazonaws.com/hyper-linux-x86_64.tar.gz
RUN tar xzf hyper-linux-x86_64.tar.gz
RUN mv /hyper /usr/bin/hyper

ARG HYPERSH_ACCESS_KEY
ARG HYPERSH_SECRET
ENV HYPERSH_ACCESS_KEY ${HYPERSH_ACCESS_KEY}
ENV HYPERSH_SECRET ${HYPERSH_SECRET}
RUN hyper config --accesskey $HYPERSH_ACCESS_KEY --secretkey $HYPERSH_SECRET --default-region eu-central-1

RUN mkdir -p /var/log/supervisor
RUN mkdir -p /etc/supervisor/conf.d
ADD ./supervisor.conf /etc/supervisor.conf

ADD ./main /main
ADD ./proxy /proxy

#CMD ["/usr/local/bin/supervisord"]
#CMD ["supervisord", "-c", "/etc/supervisor.conf"]  # todo: this isn't working

ENTRYPOINT ["python3", "/main/main.py"]