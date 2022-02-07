#!/bin/bash
if [[ -z ${1} ]]; then
    echo "Argument (id) required. Run 'bash delete_resources.sh <id>'"
    exit 1
fi

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
ID=${1}

kubectl delete -f ${DIR}/${ID}/yaml 2> /dev/null
if [[ -f ${DIR}/${ID}/pids/port-forward.pid ]]; then
    kill -9 $(cat ${DIR}/${ID}/pids/port-forward.pid)
fi
if [[ -f ${DIR}/${ID}/pids/rsync.pid ]]; then
    kill -9 $(cat ${DIR}/${ID}/pids/rsync.pid)
fi

rm -r ${DIR}/${ID}/certs
rm -r ${DIR}/${ID}/files
rm -r ${DIR}/${ID}/keypairs
rm -r ${DIR}/${ID}/pids
rm -r ${DIR}/${ID}/yaml

echo "rsync folder not deleted. To do so: "
echo "rm -r ${DIR}/${ID}"
