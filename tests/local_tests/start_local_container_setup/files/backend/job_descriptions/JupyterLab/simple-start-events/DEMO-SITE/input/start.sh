#!/bin/bash
echo "Hello World from my Script"

export JUPYTERHUB_API_TOKEN=$(cat .jupyter.token)

sleep 2
curl -H "Authorization: token ${JUPYTERHUB_API_TOKEN}" -H "Content-Type: application/json" -d '{"progress": 25, "failed": false, "html_message": "Msg 25"}' -X "POST" http://localhost:8000/hub/api/users/progress/update/demo-user-1@example.com
sleep 2
curl -H "Authorization: token ${JUPYTERHUB_API_TOKEN}" -H "Content-Type: application/json" -d '{"progress": 50, "failed": false, "html_message": "Msg 50"}' -X "POST" http://localhost:8000/hub/api/users/progress/update/demo-user-1@example.com
sleep 2
curl -H "Authorization: token ${JUPYTERHUB_API_TOKEN}" -H "Content-Type: application/json" -d '{"progress": 75, "failed": false, "html_message": "Msg 75"}' -X "POST" http://localhost:8000/hub/api/users/progress/update/demo-user-1@example.com

