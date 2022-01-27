ARG JUPYTERHUB_VERSION=2.1.1
FROM jupyterhub/jupyterhub:${JUPYTERHUB_VERSION}
# FROM keyword removes all ARG definitions
ARG JUPYTERHUB_VERSION=2.1.1
ENV JUPYTERHUB_VERSION=$JUPYTERHUB_VERSION

# Add custom files
COPY ./custom/${JUPYTERHUB_VERSION} /src/jupyterhub-custom
RUN pip3 install -r /src/jupyterhub-custom/requirements.txt

# Install patches for specific JupyterHub Version
RUN apt update && apt install -y git \
 && git clone -b ${JUPYTERHUB_VERSION} https://github.com/jupyterhub/jupyterhub.git /src/jupyterhub \
 && rm -rf /src/jupyterhub/.git* \
 && apt remove -y git
COPY ./patches/${JUPYTERHUB_VERSION}/patch_files /src/patches/${JUPYTERHUB_VERSION}/patch_files
COPY ./patches/install_patches.sh /src/patches/install_patches.sh
RUN /src/patches/install_patches.sh

# Add entrypoint
COPY ./entrypoint.sh /src/entrypoint.sh
CMD ["/src/entrypoint.sh"]
