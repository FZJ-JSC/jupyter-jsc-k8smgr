#!/bin/bash

if [[ -z ${1} ]]; then
    echo "Argument (JupyterHub version) required. Run 'bash setup_patched_jhub.sh 2.1.1' to download JupyterHub Version 2.1.1"
    exit 1
fi

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
if [[ -d ${DIR}/jupyterhub ]]; then
    echo "Folder jupyterhub in patches already exists. Stop"
    exit 1
fi
if [[ -d ${DIR}/jupyterhub-patched ]]; then
    echo "Folder jupyterhub-patched in patches already exists. Stop"
    exit 1
fi
git clone -b ${1} https://github.com/jupyterhub/jupyterhub.git ${DIR}/jupyterhub

for f in `ls ${DIR}/patch_files/*.patch`
do
    patch -d ${DIR} -p1 < $f
done

cp -rp ${DIR}/jupyterhub ${DIR}/jupyterhub-patched
