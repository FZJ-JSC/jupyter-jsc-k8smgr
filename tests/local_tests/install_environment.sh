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

git clone -b ${1} https://github.com/jupyterhub/jupyterhub.git ${DIR}/${1}/jupyterhub

for f in `ls ${BASE}/patches/${1}/patch_files/*.patch`
do
    patch -d ${DIR}/${1} -p1 < $f
done

${BASE}/venvs/${1}/bin/pip3 install -U pip
${BASE}/venvs/${1}/bin/pip3 install -e ${DIR}/${1}/jupyterhub
cp ${DIR}/jupyterhub_config.py ${DIR}/${1}/. 
sed -i -e "s|<CUSTOM_PATH>|${BASE}/custom/${1}|g" ${DIR}/${1}/jupyterhub_config.py
