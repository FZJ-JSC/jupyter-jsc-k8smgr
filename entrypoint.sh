#!/bin/sh

if [[ -n ${K8SMGR_PRIVATE_KEY_B64} ]]; then
    mkdir -p /home/k8smgr/.ssh
    chown k8smgr:users /home/k8smgr/.ssh
    chmod 755 /home/k8smgr/.ssh
    echo -n "${K8SMGR_PRIVATE_KEY_B64}" | base64 -d > /home/k8smgr/.ssh/ssh_key
    chown k8smgr:users /home/k8smgr/.ssh/ssh_key
    chmod 400 /home/k8smgr/.ssh/ssh_key
fi

if [[ -n ${K8SMGR_AUTHORIZED_KEYS_B64} ]]; then
    mkdir -p /home/k8smgr/.ssh
    chown k8smgr:users /home/k8smgr/.ssh
    chmod 755 /home/k8smgr/.ssh
    echo -n "${K8SMGR_AUTHORIZED_KEYS_B64}" | base64 -d > /home/k8smgr/.ssh/authorized_keys
    chown k8smgr:users /home/k8smgr/.ssh/authorized_keys
    chmod 600 /home/k8smgr/.ssh/authorized_keys
fi

if [[ -n ${K8SMGR_MANAGE_TUNNEL_SH_B64} ]]; then
    echo -n "${K8SMGR_MANAGE_TUNNEL_SH_B64}" | base64 -d > /home/k8smgr/manage_tunnel.sh
    chown k8smgr:users /home/k8smgr/manage_tunnel.sh
    chmod 644 /home/k8smgr/manage_tunnel.sh
fi

# Start ssh daemon
if [ -z ${SSHD_LOG_PATH} ]; then
    SSHD_LOG_PATH=/home/k8smgr/sshd.log
fi
/usr/sbin/sshd -f /etc/ssh/sshd_config -E ${SSHD_LOG_PATH}

if [[ -z $K8SMGR_SUPERUSER_PASS ]]; then
    export K8SMGR_SUPERUSER_PASS=$(uuidgen)
fi

# Database setup / wait for database
if [ "$SQL_ENGINE" == "postgres" ]; then
    echo "Waiting for postgres..."
    while ! nc -z $SQL_HOST $SQL_PORT; do
      sleep 0.1
    done
    echo "PostgreSQL started"
elif [[ -z ${SQL_DATABASE} ]]; then
    su k8smgr -c "/usr/local/bin/python3 /home/k8smgr/web/manage.py makemigrations"
    su k8smgr -c "/usr/local/bin/python3 /home/k8smgr/web/manage.py migrate"
    su k8smgr -c "echo \"import os; from django.contrib.auth.models import User; k8smgrpass=os.environ.get('K8SMGR_SUPERUSER_PASS'); User.objects.create_superuser('admin', 'admin@example.com', k8smgrpass)\" | python manage.py shell"
    su k8smgr -c "echo \"import os; from django.contrib.auth.models import Group; Group.objects.create(name='access_to_webservice'); Group.objects.create(name='access_to_logging');\" | python manage.py shell"
    if [[ -n ${BACKEND_USER_PASS} ]]; then
        su k8smgr -c "echo \"import os; from django.contrib.auth.models import Group, User; from rest_framework.authtoken.models import Token; backend_pass=os.environ.get('BACKEND_USER_PASS'); user = User.objects.create(username='backend'); user.set_password(backend_pass); user.save(); user.auth_token = Token.objects.create(user=user); os.environ['BACKEND_USER_TOKEN'] = user.auth_token.key; group1 = Group.objects.filter(name='access_to_webservice').first(); group2 = Group.objects.filter(name='access_to_logging').first(); user.groups.add(group1); user.groups.add(group2)\" | python manage.py shell"
    fi
fi


if [[ ! -d /home/k8smgr/web/static ]]; then
    echo "$(date) Collect static files ..."
    su k8smgr -c "SQL_DATABASE=/dev/null /usr/local/bin/python3 /home/k8smgr/web/manage.py collectstatic"
    echo "$(date) ... done"
fi

if [[ -z $WORKER ]]; then
        echo "Use 1 worker (default)"
        WORKER=1
fi

if [ -z ${UWSGI_PATH} ]; then
    UWSGI_PATH=/home/k8smgr/web/uwsgi.ini
fi

if [[ -n ${DELAYED_START_IN_SEC} ]]; then
    echo "$(date): Delay start by ${DELAYED_START_IN_SEC} seconds ..."
    sleep ${DELAYED_START_IN_SEC}
    echo "$(date): ... done"
fi

su k8smgr -c "uwsgi --ini ${UWSGI_PATH} --processes ${WORKER}"
