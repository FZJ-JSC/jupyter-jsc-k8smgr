#!/bin/bash

while true; do
    rsync -r -c -q -b -e "ssh -p 2222 -i <DIR>/<ID>/keypairs/jupyterhub_devel -oLogLevel=ERROR -oUserKnownHostsFile=/dev/null -oStrictHostKeyChecking=no" jupyterhub@localhost:/src/jupyterhub-patched <DIR>/<ID>/rsync
    rsync -r -c -q -b -e "ssh -p 2222 -i <DIR>/<ID>/keypairs/jupyterhub_devel -oLogLevel=ERROR -oUserKnownHostsFile=/dev/null -oStrictHostKeyChecking=no" jupyterhub@localhost:/src/jupyterhub-custom <DIR>/<ID>/rsync
    sleep 60
done
