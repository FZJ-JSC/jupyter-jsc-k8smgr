FROM jupyterhub/jupyterhub:2.1.1
RUN apt update && apt install -y git \
 && git clone -b 2.1.1 https://github.com/jupyterhub/jupyterhub.git /src/jupyterhub \
 && rm -rf /src/jupyterhub/.git* \
 && apt remove -y git
RUN apt update && apt install -y vim
COPY ./patches /src/patches
RUN /src/patches/install_patches.sh
#RUN cd /src \
# && diff -Naur /src/jupyterhub /src/patches/jupyterhub > jhub.patch \
# && patch -p2 < jhub.patch \
# && pip3 install -e /src/jupyterhub
#COPY ./custom /src/jupyterhub-custom
#
COPY ./entrypoint.sh /src/entrypoint.sh
CMD ["/src/entrypoint.sh"]
