#!/bin/bash
mkdir -p /home/jupyterhub/.ssh
for f in /tmp/ssh/* ; do
    if [[ -f $f ]]; then
        cp -rp $f /home/jupyterhub/.ssh/.
    fi
done
chmod -R 400 /home/jupyterhub/.ssh/*

apt update && apt install -y vim rsync openssh-server libc6 libstdc++6 ca-certificates tar bash curl wget
sed -i -r -e "s/^#PasswordAuthentication yes/PasswordAuthentication no/g" -e "s/^AllowTcpForwarding no/AllowTcpForwarding yes/g" -e "s/^#Port 22/Port 2222/g" /etc/ssh/sshd_config
/etc/init.d/ssh start

if [[ -d /tmp/.vscode ]]; then
    cp -r /tmp/.vscode /home/jupyterhub/.
fi
if [[ -d /tmp/home ]]; then
    cp -r /tmp/home/* /home/jupyterhub/.
fi
chown -R jupyterhub:users /home/jupyterhub

cp -rp /src/jupyterhub /src/jupyterhub-patched
pip install -e /src/jupyterhub-patched/

while true; do
    sleep 30
done
