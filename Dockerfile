# pull official base image
# FROM alpine
FROM python:3.10.1-alpine3.15

RUN apk update && apk upgrade && apk add bash mailcap

# create directory for the app user
RUN mkdir -p /home/k8smgr/ssh_socket

# create the app user
RUN adduser --uid 1094 -D --ingroup users k8smgr

# create the appropriate directories
ENV HOME=/home/k8smgr
ENV APP_HOME=/home/k8smgr/web
RUN mkdir $APP_HOME
WORKDIR $APP_HOME

# install dependencies
RUN apk update &&\
    apk add --no-cache bash openssh rssh libpq util-linux uwsgi uwsgi-python3 uwsgi-logfile &&\
    sed -i -r "s/^#PasswordAuthentication yes/PasswordAuthentication no/g" /etc/ssh/sshd_config &&\
    sed -i -r "s/^AllowTcpForwarding no/AllowTcpForwarding yes/g" /etc/ssh/sshd_config &&\
    sed -i -r "s/^#Port 22/Port 2222/g" /etc/ssh/sshd_config &&\
    ssh-keygen -A

RUN echo k8smgr:$(uuidgen) | chpasswd

# copy project
COPY . $APP_HOME

RUN apk update && \
    apk add --no-cache --virtual .build-dependencies \
        gcc \
        build-base \
        linux-headers && \
    pip install -r ${APP_HOME}/requirements.txt && \
    apk del .build-dependencies

# chown all the files to the app user
RUN chown -R k8smgr:users $APP_HOME
RUN chown -R k8smgr:users /home/tunnel/ssh_socket

EXPOSE 2222

# run entrypoint.prod.sh
ENTRYPOINT ["/home/k8smgr/web/entrypoint.sh"]
