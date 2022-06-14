#!/bin/bash

NAMESPACE=devel
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

if [[ -f ${DIR}/generated/pids/port-forward.pid ]]; then
    kill -9 $(cat ${DIR}/generated/pids/port-forward.pid)
    rm ${DIR}/generated/pids/port-forward.pid
fi
if [[ -f ${DIR}/generated/pids/rsync.pid ]]; then
    kill -9 $(cat ${DIR}/generated/pids/rsync.pid)
    rm ${DIR}/generated/pids/rsync.pid
fi

if [[ -d ${DIR}/generated/yaml ]]; then
    kubectl -n ${NAMESPACE} delete -f ${DIR}/generated/yaml
fi
