#!/bin/bash

# curl to remote node to build up tunnel

# Check quota in here.
# We'll have an cronjob which puts actual quota in users home directory

if [[ -f ${HOME}/.disk_usage_bytes ]]; then
    DISK_USAGE_BYTES=$(cat ${HOME}/.disk_usage_bytes)
    # DISK_USAGE_MAX is added via voquota-<vo> ConfigMap
    # DISK_USAGE_WARNING is added via voquota-<vo> ConfigMap
    if [[ $DISK_USAGE_BYTES -gt $DISK_USAGE_MAX ]]; then
        # curl JHub : "You're not allowed to start. Please contact administrator"
        # echo "You're not allowed, blabla"
        # exit 1
        echo "x"
    elif [[ $DISK_USAGE_BYTES -gt $DISK_USAGE_WARNING ]]; then
        # curl JHub: "You use x gb of $DISK_USAGE_ALLOWED", "If it's more than ... you're not allowed to start anything"
        # echo "WARNING" > /etc/motd
        echo "y"
    else
        # curl JHub: "Disk Quota checked x gb of $ALLOWED. All good
        echo "y"
    fi
fi

# start
jupyter-lab
