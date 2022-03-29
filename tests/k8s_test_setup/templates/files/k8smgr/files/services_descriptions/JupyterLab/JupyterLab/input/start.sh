#!/bin/bash

# Update env variables
export JUPYTERHUB_ACTIVITY_URL=${JUPYTERHUB_API_URL}/users/${JUPYTERHUB_USER}/activity

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
echo "Setup tunnel call"
curl -H "uuidcode: ${SERVERNAME}" -H "Authorization: token ${JUPYTERHUB_API_TOKEN}" -H "Content-Type: application/json" -d '{"progress": 35, "failed": false, "html_message": "Setup Tunnel", "setup_tunnel": {"hostname": "k8smgr_hdfcloud", "target_node": "svc-'"${SERVERNAME}"'", "target_port": "8443", "startuuidcode": "'"${SERVERNAME}"'"}}' -X "POST" ${JUPYTERHUB_API_URL}/${JUPYTERHUB_STATUS_URL} 2>&1
echo "Setup tunnel called"
# curl to remote node to build up tunnel


# Check quota in here.
# We'll have an cronjob which puts actual quota in users home directory

if [[ -f ${HOME}/.disk_usage_bytes ]]; then
    DISK_USAGE_BYTES=$(cat ${HOME}/.disk_usage_bytes)
    # DISK_USAGE_MAX is added via voquota-<vo> ConfigMap
    # DISK_USAGE_WARNING is added via voquota-<vo> ConfigMap
    if [[ $DISK_USAGE_BYTES -gt $DISK_USAGE_MAX ]]; then
        # curl JHub : "You're not allowed to start. Please contact administrator"
        # echo "You're not allowed, blabla"
        # exit 1
        echo "x"
    elif [[ $DISK_USAGE_BYTES -gt $DISK_USAGE_WARNING ]]; then
        # curl JHub: "You use x gb of $DISK_USAGE_ALLOWED", "If it's more than ... you're not allowed to start anything"
        # echo "WARNING" > /etc/motd
        echo "y"
    else
        # curl JHub: "Disk Quota checked x gb of $ALLOWED. All good
        echo "y"
    fi
fi

# start
timeout 3d /home/jovyan/venv/bin/jupyterhub-singleuser --config ${DIR}/config.py
