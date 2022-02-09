#!/bin/bash
export PYTHONPATH=${PYTHONPATH}:/src/jupyterhub:/src/jupyterhub-custom

if [[ ${DEVEL,,} == "true" ]]; then
    mkdir -p /home/jupyterhub/.ssh
    for f in /tmp/ssh/* ; do
        if [[ -f $f ]]; then
            cp -rp $f /home/jupyterhub/.ssh/.
        fi
    done
    chmod -R 400 /home/jupyterhub/.ssh/*

    apt update && apt install -y vim rsync openssh-server libc6 libstdc++6 ca-certificates tar bash curl wget
    sed -i -r -e "s/^#PasswordAuthentication yes/PasswordAuthentication no/g" -e "s/^AllowTcpForwarding no/AllowTcpForwarding yes/g" -e "s/^#Port 22/Port 2222/g" /etc/ssh/sshd_config
    /usr/sbin/sshd -f /etc/ssh/sshd_config -E /home/jupyterhub/sshd.log

    if [[ -d /tmp/.vscode ]]; then
        cp -r /tmp/.vscode /home/jupyterhub/.
    fi
    if [[ -d /tmp/home ]]; then
        cp -r /tmp/home/* /home/jupyterhub/.
    fi
    cp -rp /src/jupyterhub /src/jupyterhub-patched
    pip install -e /src/jupyterhub-patched/

    ln -s /src/jupyterhub-patched /home/jupyterhub/jupyterhub-patched
    ln -s /src/jupyterhub-custom /home/jupyterhub/jupyterhub-custom
    ln -s /src/jupyterhub-static /home/jupyterhub/jupyterhub-static

    if [[ -n ${STATIC_FILES_SRC} && -n ${STATIC_FILES_DEST} ]]; then
        mkdir -p $(dirname ${STATIC_FILES_DEST})
        ln -s ${STATIC_FILES_SRC} ${STATIC_FILES_DEST}
    fi

    chown -R jupyterhub:users /home/jupyterhub
    while true; do
        sleep 30
    done
else
    /usr/bin/jupyterhub ${@}
fi
