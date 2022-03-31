#!/bin/bash
if [[ -z ${1} ]]; then
    echo "Argument (Namespace) required. Run 'bash create_yaml_files.sh namespace'"
    exit 1
fi

DEVEL_JUPYTERHUB="false"
DEVEL_UNICOREMGR="false"
DEVEL_K8SMGR="false"
DEVEL_TUNNEL="false"


JUPYTERHUB_VERSION="latest"
UNITY_VERSION="3.8.1-1"
UNICORE_VERSION="8.3.0-p1"
UNICOREMGR_VERSION="1.0.1-7"
TUNNEL_VERSION="1.0.1-7"
K8SMGR_VERSION="1.0.1-17"


DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
BASE_TESTS=$(dirname $DIR)
BASE=$(dirname $BASE_TESTS)

ID_LONG=$(uuidgen | tr 'A-Z' 'a-z')
ID=${ID_LONG:0:8}
NAMESPACE=${1}
echo "Create yaml files and JupyterHub configurations for unique identifier: ${ID}"

# Create Certs
mkdir -p ${DIR}/${ID}/certs
cp ${DIR}/templates/certs/ca-root.pem ${DIR}/${ID}/certs/.
create_certificate () {
    SERVICE=${1}
    CN=${2}
    ALT_NAME=${3}
    KEYSTORE_PASS=${4}
    KEYSTORE_NAME=${5}
    sed -e "s@<CN>@${CN}@g" -e "s@<ALT_NAME>@${ALT_NAME}@g" ${DIR}/templates/certs/template.cnf > ${DIR}/${ID}/certs/${SERVICE}.cnf
    openssl genrsa -out ${DIR}/${ID}/certs/${SERVICE}.key 2048 &> /dev/null
    openssl req -new -key ${DIR}/${ID}/certs/${SERVICE}.key -out ${DIR}/${ID}/certs/${SERVICE}.csr -config  ${DIR}/${ID}/certs/${SERVICE}.cnf
    openssl x509 -req -in ${DIR}/${ID}/certs/${SERVICE}.csr -CA ${DIR}/templates/certs/ca-root.pem -CAkey ${DIR}/templates/certs/ca.key -CAcreateserial -out ${DIR}/${ID}/certs/${SERVICE}.crt -days 365 -sha512 -extfile ${DIR}/${ID}/certs/${SERVICE}.cnf -extensions v3_req &> /dev/null
    # Create keystores with pass
    if [[ ${KEYSTORE_NAME} == "" ]]; then
        openssl pkcs12 -export -in ${DIR}/${ID}/certs/${SERVICE}.crt -inkey ${DIR}/${ID}/certs/${SERVICE}.key -certfile ${DIR}/templates/certs/ca-root.pem -out ${DIR}/${ID}/certs/${SERVICE}.p12 -password pass:${KEYSTORE_PASS};
    else
        openssl pkcs12 -export -name ${KEYSTORE_NAME} -in ${DIR}/${ID}/certs/${SERVICE}.crt -inkey ${DIR}/${ID}/certs/${SERVICE}.key -certfile ${DIR}/templates/certs/ca-root.pem -out ${DIR}/${ID}/certs/${SERVICE}.p12 -password pass:${KEYSTORE_PASS};
    fi
}
create_certificate "gateway" "unicore-gateway" "unicore-${ID}.${NAMESPACE}.svc" 'the!gateway'
create_certificate "unicorex" "unicore-unicorex" "unicore-${ID}.${NAMESPACE}.svc" 'the!njs'
create_certificate "tsi" "unicore-tsi" "unicore-${ID}.${NAMESPACE}.svc" 'the!tsi'
create_certificate "unity" "unity" "unity-${ID}.${NAMESPACE}.svc" 'the!unity' "unity-test-server"
create_certificate "tunnel" "tunnel" "tunnel-${ID}.${NAMESPACE}.svc" 'the!tunnel' 
create_certificate "unicoremgr" "unicoremgr" "unicoremgr-${ID}.${NAMESPACE}.svc" 'the!unicoremgr' 
create_certificate "k8smgr" "k8smgr" "k8smgr-${ID}.${NAMESPACE}.svc" 'the!k8smgr' 

# Create KeyPairs
mkdir -p ${DIR}/${ID}/keypairs
create_keypair () {
    ssh-keygen -f ${DIR}/${ID}/keypairs/${1} -t ed25519 -q -N ""
}
create_keypair "ljupyter"
create_keypair "tunnel"
create_keypair "k8smgr"
create_keypair "remote"
create_keypair "reservation"
create_keypair "devel"


# Prepare input files for each services
JUPYTERHUB_ALT_NAME="jupyterhub-${ID}.${NAMESPACE}.svc"
TUNNEL_ALT_NAME="tunnel-${ID}.${NAMESPACE}.svc"
UNICOREMGR_ALT_NAME="unicoremgr-${ID}.${NAMESPACE}.svc"
K8SMGR_ALT_NAME="k8smgr-${ID}.${NAMESPACE}.svc"
UNICORE_ALT_NAME="unicore-${ID}.${NAMESPACE}.svc"
UNITY_ALT_NAME="unity-${ID}.${NAMESPACE}.svc"
TUNNEL_PUBLIC_KEY=$(cat ${DIR}/${ID}/keypairs/tunnel.pub)
ESCAPED_TPK=$(printf '%s\n' "$TUNNEL_PUBLIC_KEY" | sed -e 's/[\@&]/\\&/g')
REMOTE_PUBLIC_KEY="$(cat ${DIR}/${ID}/keypairs/remote.pub)"
ESCAPED_RPK=$(printf '%s\n' "$REMOTE_PUBLIC_KEY" | sed -e 's/[\@&]/\\&/g')
K8SMGR_PUBLIC_KEY="$(cat ${DIR}/${ID}/keypairs/k8smgr.pub)"
ESCAPED_KPK=$(printf '%s\n' "$K8SMGR_PUBLIC_KEY" | sed -e 's/[\@&]/\\&/g')
LJUPYTER_PUBLIC_KEY="$(cat ${DIR}/${ID}/keypairs/ljupyter.pub)"
ESCAPED_LPK=$(printf '%s\n' "$LJUPYTER_PUBLIC_KEY" | sed -e 's/[\@&]/\\&/g')
DEVEL_PUBLIC_KEY="$(cat ${DIR}/${ID}/keypairs/devel.pub)"
ESCAPED_DPK=$(printf '%s\n' "$DEVEL_PUBLIC_KEY" | sed -e 's/[\@&]/\\&/g')
UNICORE_SSH_PORT="22"

JUPYTERHUB_PORT="80"

# Create passwords / secrets for Django services
UNICOREMGR_SECRET=$(uuidgen)
K8SMGR_SECRET=$(uuidgen)
TUNNEL_SECRET=$(uuidgen)

TUNNEL_SUPERUSER_PASS=$(uuidgen)
TUNNEL_K8SMGR_PASS=$(uuidgen)
TUNNEL_JHUB_PASS=$(uuidgen)
TUNNEL_REMOTECHECK_PASS=$(uuidgen)
UNICOREMGR_SUPERUSER_PASS=$(uuidgen)
UNICOREMGR_JHUB_PASS=$(uuidgen)
K8SMGR_SUPERUSER_PASS=$(uuidgen)
K8SMGR_JHUB_PASS=$(uuidgen)


get_basic_token () {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        TMP=$(echo -n "${1}:${2}" | base64)
    else
        TMP=$(echo -n "${1}:${2}" | base64 -w 0)
    fi
    echo "Basic ${TMP}"
}
TUNNEL_K8SMGR_BASIC=$(get_basic_token "k8smgr" ${TUNNEL_K8SMGR_PASS})
TUNNEL_JHUB_BASIC=$(get_basic_token "jupyterhub" ${TUNNEL_JHUB_PASS})
TUNNEL_REMOTECHECK_BASIC=$(get_basic_token "remotecheck" ${TUNNEL_REMOTECHECK_PASS})
UNICOREMGR_JHUB_BASIC=$(get_basic_token "jupyterhub" ${UNICOREMGR_JHUB_PASS})
K8SMGR_JHUB_BASIC=$(get_basic_token "jupyterhub" ${K8SMGR_JHUB_PASS})

# Prepare yaml files
cp -rp ${DIR}/templates/yaml ${DIR}/${ID}/.

select_yaml_file () {
    if [[ ${1} == "true" ]]; then
        mv ${DIR}/${ID}/yaml/${2}_devel.yaml ${DIR}/${ID}/yaml/${2}.yaml
    else
        rm ${DIR}/${ID}/yaml/${2}_devel.yaml
    fi
}
select_yaml_file ${DEVEL_JUPYTERHUB} "jupyterhub"
select_yaml_file ${DEVEL_UNICOREMGR} "unicoremgr"
select_yaml_file ${DEVEL_K8SMGR} "k8smgr"
select_yaml_file ${DEVEL_TUNNEL} "tunnel"

cp -rp ${DIR}/templates/files ${DIR}/${ID}/.

set_drf_service_address () {
    if [[ ${1} == "true" ]]; then
        find ${DIR}/${ID}/files -type f -exec sed -i '' -e "s@<${2}_CERT_PATH>@false@g" -e "s@<${2}_PROTOCOL>@http@g" -e "s@<${2}_PORT>@:8080@g" {} \; 2> /dev/null
        sed -e "s@<SVC_NAME>@${3}@g" ${DIR}/${ID}/yaml/ingress-http.host.template >> ${DIR}/${ID}/yaml/ingress-http.yaml
    else
        find ${DIR}/${ID}/files -type f -exec sed -i '' -e "s@<${2}_CERT_PATH>@\"/home/jupyterhub/ca-root.pem\"@g" -e "s@<${2}_PROTOCOL>@https@g" -e "s@<${2}_PORT>@@g" {} \; 2> /dev/null
        sed -i -e "/<APPLY_HOST>/r ${DIR}/${ID}/yaml/ingress-https.host.template" ${DIR}/${ID}/yaml/ingress-https.yaml
        sed -i -e "s@<SVC_NAME>@${3}@g" ${DIR}/${ID}/yaml/ingress-https.yaml
        sed -e "s@<SVC_NAME>@${3}@g" ${DIR}/${ID}/yaml/ingress-tls.host.template >> ${DIR}/${ID}/yaml/ingress-https.yaml
    fi
}

set_drf_service_address ${DEVEL_UNICOREMGR} "UNICOREMGR" "unicoremgr"
set_drf_service_address ${DEVEL_K8SMGR} "K8SMGR" "k8smgr"
set_drf_service_address ${DEVEL_TUNNEL} "TUNNEL" "tunnel"

if [[ ${DEVEL_JUPYTERHUB} == "true" ]]; then
    find ${DIR}/${ID}/files -type f -exec sed -i '' -e "s@/src/jupyterhub-static@/home/jupyterhub/jupyterhub-static@g" {} \; 2> /dev/null
fi
find ${DIR}/${ID}/files -type f -exec sed -i '' -e "s@<DIR>@${DIR}@g" -e "s@<TUNNEL_JHUB_BASIC>@${TUNNEL_JHUB_BASIC}@g" -e "s@<TUNNEL_K8SMGR_BASIC>@${TUNNEL_K8SMGR_BASIC}@g" -e "s@<UNICOREMGR_JHUB_BASIC>@${UNICOREMGR_JHUB_BASIC}@g" -e "s@<K8SMGR_JHUB_BASIC>@${K8SMGR_JHUB_BASIC}@g" -e "s@<NAMESPACE>@${NAMESPACE}@g" -e "s@<ID>@${ID}@g" -e "s@<K8SMGR_ALT_NAME>@${K8SMGR_ALT_NAME}@g" -e "s@<UNITY_ALT_NAME>@${UNITY_ALT_NAME}@g" -e "s@<UNICORE_ALT_NAME>@${UNICORE_ALT_NAME}@g" -e "s@<TUNNEL_ALT_NAME>@${TUNNEL_ALT_NAME}@g" -e "s@<JUPYTERHUB_ALT_NAME>@${JUPYTERHUB_ALT_NAME}@g" -e "s@<JUPYTERHUB_PORT>@${JUPYTERHUB_PORT}@g" -e "s@<TUNNEL_PUBLIC_KEY>@${ESCAPED_TPK}@g" -e "s@<REMOTE_PUBLIC_KEY>@${ESCAPED_RPK}@g" -e "s@<K8SMGR_PUBLIC_KEY>@${ESCAPED_KPK}@g" -e "s@<LJUPYTER_PUBLIC_KEY>@${ESCAPED_LPK}@g" -e "s@<DEVEL_PUBLIC_KEY>@${ESCAPED_DPK}@g" -e "s@<UNICORE_SSH_PORT>@${UNICORE_SSH_PORT}@g" {} \; 2> /dev/null

tar -czf ${DIR}/${ID}/files/unicoremgr/files.tar.gz -C ${DIR}/${ID}/files/unicoremgr files
tar -czf ${DIR}/${ID}/files/k8smgr/files.tar.gz -C ${DIR}/${ID}/files/k8smgr files

find ${DIR}/${ID}/yaml -type f -exec sed -i '' -e "s@<JUPYTERHUB_ALT_NAME>@${JUPYTERHUB_ALT_NAME}@g" -e "s@<JUPYTERHUB_VERSION>@${JUPYTERHUB_VERSION}@g" -e "s@<K8SMGR_ALT_NAME>@${K8SMGR_ALT_NAME}@g" -e "s@<UNITY_VERSION>@${UNITY_VERSION}@g" -e "s@<UNICORE_VERSION>@${UNICORE_VERSION}@g" -e "s@<K8SMGR_VERSION>@${K8SMGR_VERSION}@g" -e "s@<TUNNEL_VERSION>@${TUNNEL_VERSION}@g" -e "s@<JUPYTERHUB_PORT>@${JUPYTERHUB_PORT}@g" -e "s@<UNICOREMGR_VERSION>@${UNICOREMGR_VERSION}@g" -e "s@<DIR>@${DIR}@g" -e "s@<UNICOREMGR_JHUB_BASIC>@${UNICOREMGR_JHUB_BASIC}@g" -e "s@<ID>@${ID}@g" -e "s@<NAMESPACE>@${NAMESPACE}@g" {} \; 2> /dev/null
kubectl -n ${NAMESPACE} create configmap --dry-run=client unicore-files-${ID} --from-file=${DIR}/${ID}/files/unicore --output yaml > ${DIR}/${ID}/yaml/cm-unicore-files.yaml
kubectl -n ${NAMESPACE} create configmap --dry-run=client unicoremgr-files-${ID} --from-file=${DIR}/${ID}/files/unicoremgr --output yaml > ${DIR}/${ID}/yaml/cm-unicoremgr-files.yaml
kubectl -n ${NAMESPACE} create configmap --dry-run=client k8smgr-files-${ID} --from-file=${DIR}/${ID}/files/k8smgr --output yaml > ${DIR}/${ID}/yaml/cm-k8smgr-files.yaml
kubectl -n ${NAMESPACE} create configmap --dry-run=client tunnel-files-${ID} --from-file=${DIR}/${ID}/files/tunnel --output yaml > ${DIR}/${ID}/yaml/cm-tunnel-files.yaml
kubectl -n ${NAMESPACE} create configmap --dry-run=client jupyterhub-files-${ID} --from-file=${DIR}/${ID}/files/jupyterhub --output yaml > ${DIR}/${ID}/yaml/cm-jupyterhub-files.yaml
kubectl -n ${NAMESPACE} create secret generic --dry-run=client unicoremgr-drf-${ID} --from-literal=SECRET_KEY=${UNICOREMGR_SECRET} --from-literal=SUPERUSER_PASS=${UNICOREMGR_SUPERUSER_PASS} --from-literal=JUPYTERHUB_USER_PASS=${UNICOREMGR_JHUB_PASS} --from-literal=JUPYTERHUB_USER_BASIC="${UNICOREMGR_JHUB_BASIC}" --output yaml > ${DIR}/${ID}/yaml/secret-unicoremgr-drf.yaml
kubectl -n ${NAMESPACE} create secret generic --dry-run=client k8smgr-drf-${ID} --from-literal=SECRET_KEY=${K8SMGR_SECRET} --from-literal=SUPERUSER_PASS=${K8SMGR_SUPERUSER_PASS} --from-literal=JUPYTERHUB_USER_PASS=${K8SMGR_JHUB_PASS} --from-literal=JUPYTERHUB_USER_BASIC="${K8SMGR_JHUB_BASIC}" --output yaml > ${DIR}/${ID}/yaml/secret-k8smgr-drf.yaml
kubectl -n ${NAMESPACE} create secret generic --dry-run=client tunnel-drf-${ID} --from-literal=SECRET_KEY=${TUNNEL_SECRET} --from-literal=SUPERUSER_PASS=${TUNNEL_SUPERUSER_PASS} --from-literal=JUPYTERHUB_USER_PASS=${TUNNEL_JHUB_PASS} --from-literal=JUPYTERHUB_USER_BASIC="${TUNNEL_JHUB_BASIC}" --from-literal=REMOTECHECK_USER_PASS=${TUNNEL_REMOTECHECK_PASS} --from-literal=REMOTECHECK_USER_BASIC="${TUNNEL_REMOTECHECK_BASIC}" --from-literal=K8SMGR_USER_PASS=${TUNNEL_K8SMGR_PASS} --from-literal=K8SMGR_USER_BASIC="${TUNNEL_K8SMGR_BASIC}" --output yaml > ${DIR}/${ID}/yaml/secret-tunnel-drf.yaml
kubectl -n ${NAMESPACE} create secret generic --dry-run=client --output yaml --from-file=${DIR}/${ID}/keypairs keypairs-${ID} > ${DIR}/${ID}/yaml/secret-keypairs.yaml
kubectl -n ${NAMESPACE} create secret generic --dry-run=client --output yaml --from-file=${DIR}/${ID}/certs certs-${ID} > ${DIR}/${ID}/yaml/secret-certs.yaml
kubectl -n ${NAMESPACE} create secret tls --dry-run=client --output yaml --cert=${DIR}/${ID}/certs/k8smgr.crt --key=${DIR}/${ID}/certs/k8smgr.key tls-k8smgr-${ID} > ${DIR}/${ID}/yaml/tls-k8smgr.yaml
kubectl -n ${NAMESPACE} create secret tls --dry-run=client --output yaml --cert=${DIR}/${ID}/certs/unicoremgr.crt --key=${DIR}/${ID}/certs/unicoremgr.key tls-unicoremgr-${ID} > ${DIR}/${ID}/yaml/tls-unicoremgr.yaml
kubectl -n ${NAMESPACE} create secret tls --dry-run=client --output yaml --cert=${DIR}/${ID}/certs/tunnel.crt --key=${DIR}/${ID}/certs/tunnel.key tls-tunnel-${ID} > ${DIR}/${ID}/yaml/tls-tunnel.yaml
kubectl -n ${NAMESPACE} create secret tls --dry-run=client --output yaml --cert=${DIR}/${ID}/certs/unity.crt --key=${DIR}/${ID}/certs/unity.key tls-unity-${ID} > ${DIR}/${ID}/yaml/tls-unity.yaml
kubectl -n ${NAMESPACE} create secret tls --dry-run=client --output yaml --cert=${DIR}/${ID}/certs/gateway.crt --key=${DIR}/${ID}/certs/gateway.key tls-gateway-${ID} > ${DIR}/${ID}/yaml/tls-gateway.yaml

while true; do
    read -p "Do you want to deploy the created resources to the cluster? (y/n): " yn
    case $yn in
        [Yy]* ) kubectl -n ${NAMESPACE} apply -f ${DIR}/${ID}/yaml; break;;
        [Nn]* ) echo "Add this to /etc/hosts:"; echo "<IP> jupyterhub-${ID}.${NAMESPACE}.svc unicoremgr-${ID}.${NAMESPACE}.svc k8smgr-${ID}.${NAMESPACE}.svc tunnel-${ID}.${NAMESPACE}.svc unity-${ID}.${NAMESPACE}.svc unicore-${ID}.${NAMESPACE}.svc"; exit 0;;
        * ) echo "That's not yes or no";;
    esac
done

echo "Waiting for ingress to setup address ..."
COUNTER=30
IP=$(kubectl -n ${NAMESPACE} get ingress ingress-http-${ID} --output=jsonpath={.status.loadBalancer.ingress[0].ip})
while [[ ${IP} == "" ]]; do
    let COUNTER-=1
    sleep 4
    IP=$(kubectl -n ${NAMESPACE} get ingress ingress-http-${ID} --output=jsonpath={.status.loadBalancer.ingress[0].ip})
done

if [[ $COUNTER -eq 0 ]]; then
    echo "Received no external IP address for ingress resource ingress-http-${ID}"
    kubectl -n ${NAMESPACE} get ingress ingress-http-${ID}
    exit 1
fi

echo "${IP} jupyterhub-${ID}.${NAMESPACE}.svc unicoremgr-${ID}.${NAMESPACE}.svc k8smgr-${ID}.${NAMESPACE}.svc tunnel-${ID}.${NAMESPACE}.svc unity-${ID}.${NAMESPACE}.svc unicore-${ID}.${NAMESPACE}.svc"
read -p "Add the line above to /etc/hosts and press Enter to continue: "

wait_for_service () {
    echo "Wait for ${1} ..."
    COUNTER=30
    STATUS_CODE=$(curl --write-out '%{http_code}' --silent --output /dev/null -X "GET" ${1})
    while [[ ! $STATUS_CODE -eq 200 ]]; do
        let COUNTER-=1
        sleep 2
        STATUS_CODE=$(curl --write-out '%{http_code}' --silent --output /dev/null -X "GET" ${1})
    done
    if [[ $COUNTER -eq 0 ]]; then
        echo "${1} not reachable after 60 seconds. Exit"
        exit 1
    fi
}

wait_for_service "https://${UNITY_ALT_NAME}/home/"
wait_for_service "https://${UNICORE_ALT_NAME}/"
if [[ ! ${DEVEL_TUNNEL} == "true" ]]; then
    wait_for_service "https://${TUNNEL_ALT_NAME}/api/health/" 
fi
if [[ ! ${DEVEL_UNICOREMGR} == "true" ]]; then
    wait_for_service "https://${UNICOREMGR_ALT_NAME}/api/health/" 
fi
if [[ ! ${DEVEL_K8SMGR} == "true" ]]; then
    wait_for_service "https://${K8SMGR_ALT_NAME}/api/health/" 
fi
if [[ ! ${DEVEL_JUPYTERHUB} == "true" ]]; then
    wait_for_service "http://${JUPYTERHUB_ALT_NAME}/hub/api" 
fi


# Prepare port forwarding from localhost to cluster
echo "---------- Port forwarding from localhost to JupyterHub devel Container ----------" 
mkdir -p ${DIR}/${ID}/pids
forward_port () {
    kubectl -n ${NAMESPACE} port-forward svc/${1}-${ID} ${2}:2222 1>/dev/null &
    PID=$!
    echo -n "${PID}" > ${DIR}/${ID}/pids/port-forward_${1}.pid
}

if [[ ${DEVEL_JUPYTERHUB} == "true" ]]; then
    forward_port "jupyterhub" "2222"
fi
if [[ ${DEVEL_TUNNEL} == "true" ]]; then
    forward_port "tunnel" "2223"
fi
if [[ ${DEVEL_UNICOREMGR} == "true" ]]; then
    forward_port "unicoremgr" "2224"
fi
if [[ ${DEVEL_K8SMGR} == "true" ]]; then
    forward_port "k8smgr" "2225"
fi

if [[ ${DEVEL_JUPYTERHUB} == "true" ]]; then
    # Start rsync
    mkdir -p ${DIR}/${ID}/rsync/jupyterhub-patched
    mkdir -p ${DIR}/${ID}/rsync/jupyterhub-custom
fi
if [[ ${DEVEL_JUPYTERHUB} == "true" || ${DEVEL_TUNNEL} == "true" || ${DEVEL_UNICOREMGR} == "true" || ${DEVEL_K8SMGR} == "true" ]]; then
    RSYNC=$(which rsync)
    if [[ $RSYNC == "" ]]; then
        echo "!!! Any changes are not stored automatically. If you install 'rsync' locally, you can start syncing the repositories !!!"
        exit 0
    fi

    mkdir -p ${DIR}/${ID}/rsync
    cp -p ${DIR}/templates/rsync.sh ${DIR}/${ID}/rsync/rsync.sh
    sed -i -e "s!<DIR>!${DIR}!g" -e "s!<ID>!${ID}!g" ${DIR}/${ID}/rsync/rsync.sh
    /bin/bash ${DIR}/${ID}/rsync/rsync.sh &
    PID=$!
    echo -n "${PID}" > ${DIR}/${ID}/pids/rsync.pid
    echo "${ID}/rsync/rsync.sh started. PID: ${PID}"
    echo "---------- Run remote JupyterHub in VSCode (Remote-SSH plugin required) ----------" 
    echo "1. Open empty VSCode"
    echo "2. ctrl+shift+p -> Remote-SSH: Open SSH Configuration File"
    echo "  - Add this: ${DIR}/${ID}/files/ssh_config"
    echo "3. ctrl+shift+p -> Remote-SSH: Connect to Host"
    echo "  - jupyterhub-${ID} (or any other service in debug mode)" 
    echo "4. Install 'Python' extension via VSCode on jupyterhub-${ID}"
    echo "5. Open folder /home/jupyterhub"
    echo "6. Run JupyterHub in debug mode via VSCode"
    echo "7. Open http://jupyterhub-${ID}.${NAMESPACE}.svc in your Browser."
    echo "8. /home/jupyterhub/jupyterhub-[custom|patched] will be synched every 60 seconds to ${ID}/rsync on your machine. So no need to panic if a pod crashes. Your changes are save"
else
    echo "1. Open http://jupyterhub-${ID}.${NAMESPACE}.svc in your Browser."
fi
