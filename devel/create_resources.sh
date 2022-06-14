#!/bin/bash
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

NAMESPACE=devel

if [[ ! -d generated ]]; then
    mkdir -p generated/yaml

    ssh-keygen -f ${DIR}/generated/devel_keypair -t ed25519 -q -N ""
    kubectl create secret generic --dry-run=client --output yaml --from-file=${DIR}/generated/devel_keypair --from-file=${DIR}/generated/devel_keypair.pub secret-k8smgr-keypairs-devel > ${DIR}/generated/yaml/secret.yaml
fi

sed -e "s!<DIR>!${DIR}!g" ${DIR}/templates/ssh_config > ${DIR}/generated/ssh_config

sed -e "s!<NAMESPACE>!${NAMESPACE}!g" ${DIR}/templates/service_account.yaml > ${DIR}/generated/yaml/service_account.yaml
sed -e "s!<NAMESPACE>!${NAMESPACE}!g" ${DIR}/templates/launch.json > ${DIR}/generated/launch.json
FILES_TAR_GZ_B64=$(cd ${DIR}/templates && tar -czf files.tar.gz files && base64 -w 0 files.tar.gz && rm files.tar.gz)
LAUNCH_JSON_B64=$(base64 -w 0 ${DIR}/generated/launch.json)
sed -e "s!<LAUNCH_JSON_B64>!${LAUNCH_JSON_B64}!g" -e "s!<FILES_TAR_GZ_B64>!${FILES_TAR_GZ_B64}!g" ${DIR}/templates/service.yaml > ${DIR}/generated/yaml/service.yaml

kubectl -n ${NAMESPACE} apply -f ${DIR}/generated/yaml

sleep 5
kubectl -n ${NAMESPACE} wait --for=condition=ready pod -l app=deployment-k8smgr-devel --timeout=300s
EC=$?

sleep 10 
if [[ $EC -eq 0 ]]; then
    mkdir -p ${DIR}/generated/pids
    kubectl -n ${NAMESPACE} port-forward svc/svc-k8smgr-devel 2235:2222 1>/dev/null &
    PID=$!
    echo -n "${PID}" > ${DIR}/generated/pids/port-forward.pid

    mkdir -p generated/rsync
    cp -p ${DIR}/templates/rsync.sh ${DIR}/generated/rsync/rsync.sh
    sed -i -e "s!<DIR>!${DIR}!g" ${DIR}/generated/rsync/rsync.sh
    /bin/bash ${DIR}/generated/rsync/rsync.sh &
    PID=$!
    echo -n "${PID}" > ${DIR}/generated/pids/rsync.pid

    echo "SSH Config File:"
    echo "${DIR}/generated/ssh_config"
else
    echo "Pod could not be started"
fi
