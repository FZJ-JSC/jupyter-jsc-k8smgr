#!/bin/bash

while true; do
    sleep 60
    rsync -r -c -q -b -e "ssh -p 2222 -i <DIR>/<ID>/keypairs/jupyterhub_devel -oLogLevel=ERROR -oUserKnownHostsFile=/dev/null -oStrictHostKeyChecking=no" jupyterhub@localhost:/src/jupyterhub-patched <DIR>/<ID>/rsync || true
    rsync -r -c -q -b -e "ssh -p 2222 -i <DIR>/<ID>/keypairs/jupyterhub_devel -oLogLevel=ERROR -oUserKnownHostsFile=/dev/null -oStrictHostKeyChecking=no" jupyterhub@localhost:/src/jupyterhub-custom <DIR>/<ID>/rsync || true
done
