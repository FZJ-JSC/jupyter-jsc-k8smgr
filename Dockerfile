ARG JUPYTERHUB_VERSION=2.1.1
ENV JUPYTERHUB_VERSION=$JUPYTERHUB_VERSION
FROM jupyterhub/jupyterhub:${JUPYTERHUB_VERSION}
RUN apt update && apt install -y git \
 && git clone -b ${JUPYTERHUB_VERSION} https://github.com/jupyterhub/jupyterhub.git /src/jupyterhub \
 && rm -rf /src/jupyterhub/.git* \
 && apt remove -y git
COPY ./patches /src/patches
RUN /src/patches/install_patches.sh
COPY ./custom /src/jupyterhub-custom

COPY ./entrypoint.sh /src/entrypoint.sh
CMD ["/src/entrypoint.sh"]
