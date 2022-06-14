#!/bin/bash

while true; do
    sleep 60
    rsync -r -c -q -b -e "ssh -p 2235 -i <DIR>/generated/devel_keypair -oLogLevel=ERROR -oUserKnownHostsFile=/dev/null -oStrictHostKeyChecking=no" k8smgr@localhost:/home/k8smgr/web <DIR>/generated/rsync/k8smgr || true
done
