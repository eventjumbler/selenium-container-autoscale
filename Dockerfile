FROM ubuntu:16.04

RUN apt-get update --fix-missing
RUN apt-get install -y python3-pip python3-dev vim wget iputils-ping
RUN apt-get update --fix-missing
RUN apt-get install -y git cron rsyslog supervisor

ADD ./requirements.txt /requirements.txt
RUN pip3 install -r requirements.txt
# for some reason hypersh_client isn't getting updated, so run this again
RUN pip3 install -e git+https://github.com/eventjumbler/hypersh_client.git#egg=hypersh_client

RUN wget https://hyper-install.s3.amazonaws.com/hyper-linux-x86_64.tar.gz
RUN tar xzf hyper-linux-x86_64.tar.gz
RUN mv /hyper /usr/bin/hyper

ENV HYPERSH_ACCESS_KEY ""
ENV HYPERSH_SECRET ""
ENV HYPERSH_REGION ""

RUN mkdir -p /var/log/supervisor
RUN mkdir -p /etc/supervisor/conf.d
ADD ./supervisor.conf /etc/supervisor.conf

ENV PYTHONPATH /
ADD ./main /main
ADD ./proxy /proxy
ADD ./run.sh /run.sh
RUN chmod a+x /run.sh

#CMD ["/usr/local/bin/supervisord"]
#CMD ["supervisord", "-c", "/etc/supervisor.conf"]

ENTRYPOINT ["./run.sh"]