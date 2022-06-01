#!/bin/bash
export PYTHONPATH=${PYTHONPATH}:/src/jupyterhub:/src/jupyterhub-custom

USERNAME=jovyan

if [[ -n ${K8SMGRHDFCLOUD_JUPYTERHUB_USER_PASS} ]]; then
  export K8SMGRHDFCLOUD_AUTHENTICATION_TOKEN=${K8SMGRHDFCLOUD_AUTHENTICATION_TOKEN:-"Basic $(echo -n "jupyterhub:${K8SMGRHDFCLOUD_JUPYTERHUB_USER_PASS}" | base64 -w 0)"}
fi

if [[ -n ${UNICOREMGR_JUPYTERHUB_USER_PASS} ]]; then
  export UNICOREMGR_AUTHENTICATION_TOKEN=${UNICOREMGR_AUTHENTICATION_TOKEN:-"Basic $(echo -n "jupyterhub:${UNICOREMGR_JUPYTERHUB_USER_PASS}" | base64 -w 0)"}
fi

if [[ -n ${TUNNEL_JUPYTERHUB_USER_PASS} ]]; then
  export TUNNEL_AUTHENTICATION_TOKEN=${TUNNEL_AUTHENTICATION_TOKEN:-"Basic $(echo -n "jupyterhub:${TUNNEL_JUPYTERHUB_USER_PASS}" | base64 -w 0)"}
fi

if [[ -d /mnt/shared-data/tmp-internal-ssl ]]; then
  rm -rf /mnt/shared-data/tmp-internal-ssl/*
fi

/usr/bin/jupyterhub ${@}
