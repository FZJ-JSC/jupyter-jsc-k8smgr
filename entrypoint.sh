#!/bin/bash
export PYTHONPATH=${PYTHONPATH}:/src/jupyterhub:/src/jupyterhub-custom

USERNAME=jupyterhub

if [[ -d /tmp/${USERNAME}_certs ]]; then
    mkdir -p /home/${USERNAME}/certs
    cp -rp /tmp/${USERNAME}_certs/* /home/${USERNAME}/certs/.
    chmod -R 400 /home/${USERNAME}/certs/*
    chown -R ${USERNAME}:users /home/${USERNAME}/certs
fi

if [[ ${DEVEL,,} == "true" ]]; then
    if [[ -d /tmp/${USERNAME}_ssh ]]; then
        mkdir -p /home/${USERNAME}/.ssh
        cp -rp /tmp/${USERNAME}_ssh/* /home/${USERNAME}/.ssh/.
        chmod -R 400 /home/${USERNAME}/.ssh/*
        chown -R ${USERNAME}:users /home/${USERNAME}/.ssh
    fi

    apt update && apt install -y vim rsync openssh-server libc6 libstdc++6 ca-certificates tar bash curl wget
    sed -i -r -e "s/^#PasswordAuthentication yes/PasswordAuthentication no/g" -e "s/^AllowTcpForwarding no/AllowTcpForwarding yes/g" -e "s/^#Port 22/Port 2222/g" /etc/ssh/sshd_config
    mkdir -p /run/sshd
    /usr/sbin/sshd -f /etc/ssh/sshd_config -E /home/${USERNAME}/sshd.log

    if [[ -d /tmp/${USERNAME}_vscode ]]; then
        mkdir -p /home/${USERNAME}/.vscode
        cp -rp /tmp/${USERNAME}_vscode/* /home/${USERNAME}/.vscode/.
        chmod -R 400 /home/${USERNAME}/.vscode/*
        chown -R ${USERNAME}:users /home/${USERNAME}/.vscode
    fi
    if [[ -d /tmp/${USERNAME}_home ]]; then
        cp -rp /tmp/${USERNAME}_home/* /home/${USERNAME}/.
    fi
    cp -rp /src/jupyterhub /src/jupyterhub-patched
    pip install -e /src/jupyterhub-patched/
    pip install -r /src/jupyterhub/dev-requirements.txt

    ln -s /src/jupyterhub-patched /home/jupyterhub/jupyterhub-patched
    ln -s /src/jupyterhub-custom /home/jupyterhub/jupyterhub-custom
    ln -s /src/jupyterhub-static /home/jupyterhub/jupyterhub-static

    if [[ -n ${STATIC_FILES_SRC} && -n ${STATIC_FILES_DEST} ]]; then
        STATIC_FILES_DEST_DIR=$(dirname ${STATIC_FILES_DEST})
        mkdir -p ${STATIC_FILES_DEST_DIR}
        ln -s ${STATIC_FILES_SRC} ${STATIC_FILES_DEST}
    fi
    if [[ -n ${TEMPLATE_FILES_SRC} && -n ${TEMPLATE_FILES_DEST} ]]; then
        mkdir -p $(dirname ${TEMPLATE_FILES_DEST})
        ln -s ${TEMPLATE_FILES_SRC} ${TEMPLATE_FILES_DEST}
    fi

    chown -R ${USERNAME}:users /home/${USERNAME}
    while true; do
        sleep 30
    done
else
    /usr/bin/jupyterhub ${@}
fi
