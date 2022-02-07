#!/bin/bash


if [[ -z ${1} ]]; then
    echo "Argument (JupyterHub version) required. Run 'bash create_patch_file.sh 2.1.1 my_patch' to create a patch for JupyterHub version 2.1.1"
    exit 1
fi

if [[ -z ${2} ]]; then
    echo "Argument (name of patch) required. Will be used in patch file name: xyz_<name>.patch"
    exit 1
fi

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

if [[ ! -d ${DIR}/${1}/patch_files ]]; then
    mkdir -p ${DIR}/${1}/patch_files
fi

NUMBER_OF_FILES=`ls ${DIR}/${1}/patch_files | wc -l | sed 's/ //g'`
if [[ $NUMBER_OF_FILES -lt 10 ]]; then
    PATCH_PREFIX="00${NUMBER_OF_FILES}_"
elif [[ $NUMBER_OF_FILES -lt 100 ]]; then
    PATCH_PREFIX="0${NUMBER_OF_FILES}_"
else
    PATCH_PREFIX="${NUMBER_OF_FILES}_"
fi

if [[ ${2} == *.patch ]]; then
    PATCH_FILENAME=${2}
else
    PATCH_FILENAME="${2}.patch"
fi

echo "Create patch file patches/${1}/patch_files/${PATCH_PREFIX}${PATCH_FILENAME}"
cd ${DIR}/${1}/patch_files && diff -Naurx .git -x node_modules -x share -x __pycache__ ../jupyterhub/jupyterhub ../jupyterhub-patched/jupyterhub > ${DIR}/${1}/patch_files/${PATCH_PREFIX}${PATCH_FILENAME}

patch -d ${DIR}/${1} -p1 < ${DIR}/${1}/patch_files/${PATCH_PREFIX}${PATCH_FILENAME}
