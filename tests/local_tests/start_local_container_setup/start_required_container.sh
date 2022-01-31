#!/bin/bash

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
FILES=${DIR}/files

# Setup docker network
NETWORK_NAME="host"
# NETWORK_NAME="jhub-test-network"
NETWORK_EXISTS=$(docker network ls | grep $NETWORK_NAME | wc -l)
if [[ $NETWORK_EXISTS -eq 0 ]]; then
    docker network create $NETWORK_NAME
fi

# Define JupyterHub Version to prepare configuration
export JUPYTERHUB_VERSION="2.1.1"

# Define unity server
export UNITY_NAME="unity.gitlab.svc"
export UNITY_IMAGE="registry.jsc.fz-juelich.de/jupyterjsc/k8s/images/unity-test-server"
export UNITY_VERSION="3.8.1-rc3"
export UNITY_ALLOWED_CALLBACK_URLS="['http://localhost:8000/hub/oauth_callback']"

# Define UNICORE server
export UNICORE_NAME="unicore.gitlab.svc"
export UNICORE_IMAGE="registry.jsc.fz-juelich.de/jupyterjsc/k8s/images/unicore-test-server/unicore-server"
export UNICORE_VERSION="8.3.0-ljupyter-8"
export UNICORE_EXTERNALURL="https://${UNICORE_NAME}:9112/DEMO-SITE/"

# Define Backend server
export BACKEND_NAME="backend.gitlab.svc"
export BACKEND_IMAGE="registry.jsc.fz-juelich.de/jupyterjsc/k8s/images/backend-relaunch"
export BACKEND_VERSION="1.0.0-rc2"
export BACKEND_PORT=8090

# Define tunneling server
export TUNNEL_NAME="tunnel.gitlab.svc"
export TUNNEL_IMAGE="registry.jsc.fz-juelich.de/jupyterjsc/k8s/images/tunneling-relaunch"
export TUNNEL_VERSION="1.0.0-rc10"
export TUNNEL_PORT=8091

if [[ $NETWORK_NAME == "host" ]]; then
    ETC_HOSTS_LINES=$(grep $TUNNEL_NAME /etc/hosts | grep $BACKEND_NAME | grep $UNICORE_NAME | grep $UNITY_NAME | wc -l)
    if [[ $ETC_HOSTS_LINES -eq 0 ]]; then
        echo "You have to add '127.0.0.1 $TUNNEL_NAME $BACKEND_NAME $UNICORE_NAME $UNITY_NAME' to your /etc/hosts file, if you want to use Network host"
        exit 0
    fi
fi

# Define user passwords for django webservices
if [[ -z $TUNNEL_SUPERUSER_PASS ]]; then
    export TUNNEL_SUPERUSER_PASS=$(uuidgen)
fi
if [[ -z $TUNNEL_BACKEND_PASS ]]; then
    export TUNNEL_BACKEND_PASS=$(uuidgen)
fi
if [[ -z $TUNNEL_JHUB_PASS ]]; then
    export TUNNEL_JHUB_PASS=$(uuidgen)
fi
if [[ -z $BACKEND_SUPERUSER_PASS ]]; then
    export BACKEND_SUPERUSER_PASS=$(uuidgen)
fi
if [[ -z $BACKEND_JHUB_PASS ]]; then
    export BACKEND_JHUB_PASS=$(uuidgen)
fi

TUNNEL_BACKEND_BASIC_B64=$(echo -n "backend:${TUNNEL_BACKEND_PASS}" | base64 -w 0)
export TUNNEL_BACKEND_BASIC="Basic ${TUNNEL_BACKEND_BASIC_B64}"

TUNNEL_JHUB_BASIC_B64=$(echo -n "jupyterhub:${TUNNEL_JHUB_PASS}" | base64 -w 0)
export TUNNEL_JHUB_BASIC="Basic ${TUNNEL_JHUB_BASIC_B64}"

BACKEND_JHUB_BASIC_B64=$(echo -n "jupyterhub:${BACKEND_JHUB_PASS}" | base64 -w 0)
export BACKEND_JHUB_BASIC="Basic ${BACKEND_JHUB_BASIC_B64}"


# Start Unity
docker rm -f ${UNITY_NAME} &> /dev/null; docker container run --network ${NETWORK_NAME} -d -p 2443:2443 --env ALT_NAME=${UNITY_NAME} --env JHUB_CALLBACK_URLS_AS_LIST=${UNITY_ALLOWED_CALLBACK_URLS} --name ${UNITY_NAME} ${UNITY_IMAGE}:${UNITY_VERSION}

if [[ ! $? -eq 0 ]]; then
    echo "Could not start Unity service. Test environment will not work"
    exit 1
fi

# Start UNICORE
sed -e "s/<tunnel_host>/${TUNNEL_NAME}/g" ${FILES}/unicore/manage_tunnel.sh.template > ${FILES}/unicore/manage_tunnel.sh
docker rm -f ${UNICORE_NAME} &> /dev/null ; docker run --network ${NETWORK_NAME} -d --env EXTERNALURL=${UNICORE_EXTERNALURL} -v ${FILES}/unicore/manage_tunnel.sh:/home/ljupyter/manage_tunnel.sh --name ${UNICORE_NAME} ${UNICORE_IMAGE}:${UNICORE_VERSION} 

if [[ ! $? -eq 0 ]]; then
    echo "Could not start UNICORE service. Test environment will not work"
    exit 1
fi

# Start Backend
sed -e "s/<tunnel_port>/${TUNNEL_PORT}/g" -e "s/<tunnel_name>/${TUNNEL_NAME}/g" -e "s/<unicore_name>/${UNICORE_NAME}/g" ${FILES}/backend/config.json.template > ${FILES}/backend/config.json
docker rm -f ${BACKEND_NAME} &> /dev/null ; docker run --network ${NETWORK_NAME} -d -v ${FILES}/backend/uwsgi.ini:/home/backend/web/uwsgi.ini -v ${FILES}/backend/config.json:/tmp/config.json -v ${FILES}/backend/job_descriptions:/tmp/job_descriptions --env REMOTE_NODE_TOKEN="${TUNNEL_BACKEND_BASIC}" --env DEBUG="true" --env BACKEND_SUPERUSER_PASS=${BACKEND_SUPERUSER_PASS} --env JUPYTERHUB_USER_PASS=${BACKEND_JHUB_PASS} --env CONFIG_PATH=/tmp/config.json --name ${BACKEND_NAME} ${BACKEND_IMAGE}:${BACKEND_VERSION}

if [[ ! $? -eq 0 ]]; then
    echo "Could not start backend service. Test environment will not work"
    exit 1
fi

# Start Tunneling
sed -e "s/<unicore_name>/${UNICORE_NAME}/g" ${FILES}/tunnel/ssh_config.template > ${FILES}/tunnel/ssh_config
docker rm -f ${TUNNEL_NAME} &> /dev/null ; docker run --network ${NETWORK_NAME} -d --env DEBUG="true" --env SSHCONFIGFILE="/home/tunnel/.ssh/config" --env TUNNEL_SUPERUSER_PASS="${TUNNEL_SUPERUSER_PASS}" --env BACKEND_USER_PASS="${TUNNEL_BACKEND_PASS}" --env JUPYTERHUB_USER_PASS=${TUNNEL_JHUB_PASS} -v ${FILES}/tunnel/uwsgi.ini:/home/tunnel/web/uwsgi.ini -v ${FILES}/tunnel/remote_key:/home/tunnel/.ssh/remote -v ${FILES}/tunnel/tunnel_key:/home/tunnel/.ssh/tunnel -v ${FILES}/tunnel/ssh_config:/home/tunnel/.ssh/config -v ${FILES}/tunnel/authorized_keys:/home/tunnel/.ssh/authorized_keys --name ${TUNNEL_NAME} ${TUNNEL_IMAGE}:${TUNNEL_VERSION}

if [[ ! $? -eq 0 ]]; then
    echo "Could not start tunneling service. Test environment will not work"
    exit 1
fi


echo "Wait for django services to start ..."
STATUS_CODE=$(curl --write-out '%{http_code}' --silent --output /dev/null -X "GET" http://localhost:${BACKEND_PORT}/api/health/)
while [[ ! $STATUS_CODE -eq 200 ]]; do
    STATUS_CODE=$(curl --write-out '%{http_code}' --silent --output /dev/null -X "GET" http://localhost:${BACKEND_PORT}/api/health/)
done

STATUS_CODE=$(curl --write-out '%{http_code}' --silent --output /dev/null -X "GET" http://localhost:${TUNNEL_PORT}/api/health/)
while [[ ! $STATUS_CODE -eq 200 ]]; do
    STATUS_CODE=$(curl --write-out '%{http_code}' --silent --output /dev/null -X "GET" http://localhost:${TUNNEL_PORT}/api/health/)
done

STATUS_CODE=$(curl --write-out '%{http_code}' --silent --output /dev/null -X "POST" -H "Content-Type: application/json" -H "Authorization: ${TUNNEL_JHUB_BASIC}" -d '{"handler": "stream", "configuration": {"formatter": "simple", "level": 5, "stream": "ext://sys.stdout"}}' http://localhost:${TUNNEL_PORT}/api/logs/handler/)
if [[ ! $STATUS_CODE -eq 201 ]]; then
    echo "Could not add stream handler to tunneling service. Status Code: $STATUS_CODE"
fi
STATUS_CODE=$(curl --write-out '%{http_code}' --silent --output /dev/null -X "POST" -H "Content-Type: application/json" -H "Authorization: ${BACKEND_JHUB_BASIC}" -d '{"handler": "stream", "configuration": {"formatter": "simple", "level": 5, "stream": "ext://sys.stdout"}}' http://localhost:${BACKEND_PORT}/api/logs/handler/)
if [[ ! $STATUS_CODE -eq 201 ]]; then
    echo "Could not add stream handler to backend service. Status Code: $STATUS_CODE"
fi
 
#echo "Add StreamHandler to log django services"

#echo "Secret for JupyterHub to communicate with ${TUNNEL_NAME}: ${TUNNEL_JHUB_BASIC}"
#echo "Secret for JupyterHub to communicate with ${BACKEND_NAME}: ${BACKEND_JHUB_BASIC}"

echo "docker container rm -f ${TUNNEL_NAME} ${BACKEND_NAME} ${UNICORE_NAME} ${UNITY_NAME}"

TMP1=$(dirname ${DIR})
TMP2=$(dirname ${TMP1})
BASE_PATH=$(dirname ${TMP2})
sed -e "s/<UNITY_HOST>/${UNITY_NAME}/g" -e "s/<BACKEND_TOKEN>/${BACKEND_JHUB_BASIC}/g" -e "s@<BASE_PATH>@${BASE_PATH}@g" -e "s/<VERSION>/${JUPYTERHUB_VERSION}/g" -e "s/<BACKEND_HOST>/${BACKEND_NAME}/g" -e "s/<BACKEND_PORT>/${BACKEND_PORT}/g" ${DIR}/../jupyterhub_config.py.template > ${DIR}/../${JUPYTERHUB_VERSION}/jupyterhub_config.py

echo "JupyterHub configuration updated. You should restart JupyterHub."

