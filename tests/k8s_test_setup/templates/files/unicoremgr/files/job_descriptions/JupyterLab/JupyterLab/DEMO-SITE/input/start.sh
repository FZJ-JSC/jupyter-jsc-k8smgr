#!/bin/bash
_term() {
  echo "Caught SIGTERM signal!"
  kill -TERM "$child" 2>/dev/null
}
trap _term SIGTERM

# Run through all Login Nodes and search for a working one
# for x in login_nodes: curl -X "GET" http://${x}:56789/hub/api ...
export JUPYTERHUB_API_URL="http://demo-site-login-01-<ID>:56789/hub/api"
export JUPYTERHUB_ACTIVITY_URL=${JUPYTERHUB_API_URL}/users/${JUPYTERHUB_USER}/activity

echo "Hello World from my Script"

# Give UNICORE time to create files correctly
sleep 2
# Get current directory
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

export JUPYTERHUB_API_TOKEN=$(cat ${DIR}/.jupyter.token)
export JUPYTERHUB_OAUTH_SCOPES=$(cat ${DIR}/.oauth.scopes)

export JUPYTER_JSC_HOME=${HOME}
export PORT=$(python3 -c 'import socket; s=socket.socket(); s.bind(("", 0)); print(s.getsockname()[1]); s.close()')

sed -i -e "s|_port_|${PORT}|g" -e "s|_home_|${JUPYTER_JSC_HOME}|g" -e "s|_servername_|${JUPYTERHUB_SERVER_NAME}|g" -e "s|_username_|${JUPYTERHUB_USER}|g" -e "s|_remotenode_|${JUPYTER_JSC_REMOTENODE}|g" -e "s|_remoteport_|${JUPYTER_JSC_REMOTEPORT}|g" ${DIR}/config.py

sleep 1
curl -H "Authorization: token ${JUPYTERHUB_API_TOKEN}" -H "Content-Type: application/json" -d '{"progress": 35, "failed": false, "html_message": "Setup Tunnel", "setup_tunnel": {"hostname": "demo_site", "target_node": "localhost", "target_port": "'${PORT}'"}}' -X "POST" ${JUPYTERHUB_API_URL}/${JUPYTERHUB_STATUS_URL}
EC=$?                                                                                                                                                                                                                                         
if [[ ! EC -eq 0 ]]; then                                                                                                                                                                                                                     
    echo "Could not reach ${JUPYTERHUB_API_URL} ; Exit"                                                                                                                                                                                       
    exit 1                                                                                                                                                                                                                                    
fi 
sleep 1
curl -H "Authorization: token ${JUPYTERHUB_API_TOKEN}" -H "Content-Type: application/json" -d '{"progress": 50, "failed": false, "html_message": "Msg 50"}' -X "POST" ${JUPYTERHUB_API_URL}/${JUPYTERHUB_STATUS_URL}
sleep 1
curl -H "Authorization: token ${JUPYTERHUB_API_TOKEN}" -H "Content-Type: application/json" -d '{"progress": 75, "failed": false, "html_message": "Msg 75"}' -X "POST" ${JUPYTERHUB_API_URL}/${JUPYTERHUB_STATUS_URL}

timeout 3d jupyterhub-singleuser --debug --config ${DIR}/config.py &
child=$!
wait $child
