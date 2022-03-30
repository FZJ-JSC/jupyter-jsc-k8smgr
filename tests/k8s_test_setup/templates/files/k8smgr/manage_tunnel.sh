#!/bin/bash
while getopts ":a:" opt; do
    case $opt in
        a) ACTION="$OPTARG"
        ;;
        \?) exit 255
        ;;
    esac
done


HOSTNAME_=$(hostname | cut -d'.' -f1)
LOCAL_PORT=56789

PRIVATE_KEY="~k8smgr/.ssh/k8smgr"
TUNNEL_SSH_PORT=2222
TUNNEL_SSH_USER=tunnel
TUNNEL_SSH_HOST=<TUNNEL_ALT_NAME>

JUPYTERHUB_HOST=<JUPYTERHUB_ALT_NAME>
JUPYTERHUB_PORT=<JUPYTERHUB_PORT>

get_pid () {
    PID=$(netstat -ltnp 2>/dev/null | tr -s ' ' | grep ":${LOCAL_PORT}" | cut -d' ' -f7 | cut -d'/' -f1)
    echo $PID
}

check_tunnel () {
    PID=$(get_pid)
    if [[ -n $PID ]]; then
        # Process is running, try to call it with curl, if curl's available
        which curl &> /dev/null
        if [[ $? -eq 0 ]]; then
            STATUS_CODE=$(curl --write-out '%{http_code}' --silent --output /dev/null http://localhost:${LOCAL_PORT}/hub/api)
            if [[ ${STATUS_CODE} -eq 200 ]]; then
                return 217
            else
                return 218
            fi
        else
            # Curl not available, return 217 (running)
            return 217
        fi
    else
        return 218
    fi
}

start_tunnel () {
    ssh -p ${TUNNEL_SSH_PORT} -i ${PRIVATE_KEY} -oLogLevel=ERROR -oUserKnownHostsFile=/dev/null -oServerAliveInterval=30 -oExitOnForwardFailure=yes -oStrictHostKeyChecking=no -L${HOSTNAME_}:${LOCAL_PORT}:${JUPYTERHUB_HOST}:${JUPYTERHUB_PORT} ${TUNNEL_SSH_USER}@${TUNNEL_SSH_HOST} -f -N
}

stop_tunnel () {
    PID=$(get_pid)
    if [[ -n $PID ]]; then
        kill -9 ${PID}
    fi
}

START="0aca3fdbc4023500b5e2bb254f95f55932785e6dc33c4f12011f25f3d47403875343a985c07de18e6a568c9fcc04ef8a1400cf2e3118dfb28ace4b58ead3c962"
STATUS="2eca457db671091b7ac46ba48bea07d541f379523a0bdf232bc2261198bbe9289774a9ba7d0d1cf69a3c235762e266927158e8a23f0f1a3e50acc529948df01d"
STOP="deb7ef7b249b1df1352525c37b8bbe3d1f6c8f36c6993e4dd6a7f87de38b8ac3dec37ee87d53024fdfa0aeeea7fc43a6147cb6df42431cc1ee66028838bfac39"

if [[ ${ACTION} == ${START} ]]; then
    check_tunnel
    if [[ $? -eq 217 ]]; then
        exit 217
    else
        start_tunnel
    fi
elif [[ ${ACTION} == ${STOP} ]]; then
    stop_tunnel
elif [[ ${ACTION} == ${STATUS} ]]; then
    :;
else
    exit 255
fi

check_tunnel
exit $?
