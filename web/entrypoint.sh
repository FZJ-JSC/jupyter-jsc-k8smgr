#!/bin/bash

USERNAME=k8smgr

if [[ -n $POD_IP ]]; then
    echo "${POD_IP} ${DEPLOYMENT_NAME}-jupyterhub-forward" >> /etc/hosts
fi

# Start sshd service
if [[ -n $AUTHORIZED_KEYS_PATH ]]; then
    sed -i -e "s@.ssh/authorized_keys@${AUTHORIZED_KEYS_PATH}@g" /etc/ssh/sshd_config
fi
export SSHD_LOG_PATH=${SSHD_LOG_PATH:-/home/${USERNAME}/sshd.log}
/usr/sbin/sshd -f /etc/ssh/sshd_config -E ${SSHD_LOG_PATH}

if [[ -d /tmp/${USERNAME}_ssh ]]; then
    mkdir -p /home/${USERNAME}/.ssh
    cp -rp /tmp/${USERNAME}_ssh/* /home/${USERNAME}/.ssh/.
    chmod -R 400 /home/${USERNAME}/.ssh/*
    chown -R ${USERNAME}:users /home/${USERNAME}/.ssh
fi

if [[ -d /tmp/${USERNAME}_certs ]]; then
    mkdir -p /home/${USERNAME}/certs
    cp -rp /tmp/${USERNAME}_certs/* /home/${USERNAME}/certs/.
    chmod -R 400 /home/${USERNAME}/certs/*
    chown -R ${USERNAME}:users /home/${USERNAME}/certs
fi

# Set secret key
export SECRET_KEY=${SECRET_KEY:-$(uuidgen)}

# Support Tokens and Password
# Option A: TUNNELSVC_K8SMGR_USER_TOKEN = Bearer secret
# Option B: TUNNELSVC_K8SMGR_USER_PASSWORD = secret
export TUNNEL_BASIC=${TUNNELSVC_K8SMGR_USER_TOKEN:-Basic $(echo -n "k8smgr:${TUNNELSVC_K8SMGR_USER_PASSWORD:-None}" | base64 -w 0 )}

# base64 -w 0 | echo "k8smgr:None" -> Basic azhz...
if [[ $TUNNEL_BASIC == "Basic azhzbWdyOk5vbmU=" ]]; then
    echo "--------------"
    echo "--------------"
    echo "------- Connection to tunneling Service will not work as expected -------"
    echo "No password or token defined to communicate with tunneling service"
    echo "--------------"
    echo "--------------"
    echo "--------------"
    export TUNNEL_BASIC=""
fi


# Database setup / wait for database
if [ "$SQL_ENGINE" == "postgres" ]; then
    echo "Waiting for postgres..."
    while ! nc -z $SQL_HOST $SQL_PORT; do
        sleep 0.1
    done
    echo "$(date) PostgreSQL started"
fi
export SUPERUSER_PASS=${SUPERUSER_PASS:-$(uuidgen)}
su ${USERNAME} -c "python3 /home/${USERNAME}/web/manage.py makemigrations"
su ${USERNAME} -c "python3 /home/${USERNAME}/web/manage.py migrate"
echo "$(date) Admin password: ${SUPERUSER_PASS}"

if [[ ! -d /home/${USERNAME}/web/static ]]; then
    echo "$(date) Collect static files ..."
    su ${USERNAME} -c "SQL_DATABASE=/dev/null python3 /home/${USERNAME}/web/manage.py collectstatic"
    echo "$(date) Collect static files ... done"
fi

if [ -z ${GUNICORN_PATH} ]; then
    export GUNICORN_SSL_CRT=${GUNICORN_SSL_CRT:-/home/${USERNAME}/certs/${USERNAME}.crt}
    export GUNICORN_SSL_KEY=${GUNICORN_SSL_KEY:-/home/${USERNAME}/certs/${USERNAME}.key}
    if [[ -f ${GUNICORN_SSL_CRT} && -f ${GUNICORN_SSL_KEY} ]]; then
        GUNICORN_PATH=/home/${USERNAME}/web/gunicorn_https.py
        echo "Use ${GUNICORN_PATH} as config file. Service will listen on port 8443."
        echo "Use these files for ssl: ${GUNICORN_SSL_CRT}, ${GUNICORN_SSL_KEY}"
    else
        GUNICORN_PATH=/home/${USERNAME}/web/gunicorn_http.py
        echo "Use ${GUNICORN_PATH} as config file. Service will listen on port 8080."
    fi
fi

# Set Defaults for gunicorn and start
export GUNICORN_PROCESSES=${GUNICORN_PROCESSES:-16}
export GUNICORN_THREADS=${GUNICORN_THREADS:-1}
gunicorn -c ${GUNICORN_PATH} jupyterjsc_k8smgr.wsgi
