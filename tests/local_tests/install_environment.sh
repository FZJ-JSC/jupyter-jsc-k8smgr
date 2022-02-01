#!/bin/bash

if [[ -z ${1} ]]; then
    echo "Argument (JupyterHub version) required. Run 'bash install_environment.sh 2.1.1' to setup a debug environment for JupyterHub version 2.1.1"
    exit 1
fi

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
BASE_TESTS=$(dirname $DIR)
BASE=$(dirname $BASE_TESTS)

if [[ ! -d ${BASE}/venvs ]]; then
    mkdir -p ${BASE}/venvs
fi
if [[ ! -d ${BASE}/venvs/${1} ]]; then
    python3 -m venv ${BASE}/venvs/${1}
fi

if [[ ! -d ${DIR}/${1} ]]; then
    mkdir -p ${DIR}/${1} 
fi

if [[ ! -d ${BASE}/patches/${1}/jupyterhub-patched ]]; then
    echo "patches/${1}/jupyterhub-patched does not exist. Will create it with patches/setup_patched_jhub.sh."
    /bin/bash ${BASE}/patches/setup_patched_jhub.sh ${1}
fi

${BASE}/venvs/${1}/bin/pip3 install -U pip
if [[ -f ${BASE}/custom/${1}/requirements.txt ]]; then
    ${BASE}/venvs/${1}/bin/pip3 install -r ${BASE}/custom/${1}/requirements.txt
    if grep -q nodeenv ${BASE}/custom/${1}/requirements.txt; then
        ${BASE}/venvs/${1}/bin/nodeenv -p
        ${BASE}/venvs/${1}/bin/npm install -g configurable-http-proxy
    fi
fi

${BASE}/venvs/${1}/bin/pip3 install -e ${BASE}/patches/${1}/jupyterhub-patched
sed -e "s|<BASE_PATH>|${BASE}|g" -e "s|<VERSION>|${1}|g" ${DIR}/jupyterhub_config.py.template > ${DIR}/${1}/jupyterhub_config.py

echo "You can start JupyterHub with vscode and use breakpoints in patches/${1}/jupyterhub-patched and custom/${1}"
