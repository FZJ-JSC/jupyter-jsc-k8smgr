ARG JUPYTERHUB_VERSION=2.1.1
FROM jupyterhub/jupyterhub:${JUPYTERHUB_VERSION}
# FROM keyword removes all ARG definitions
ARG JUPYTERHUB_VERSION=2.1.1
ENV JUPYTERHUB_VERSION=$JUPYTERHUB_VERSION

RUN adduser --uid 1000 --ingroup users --gecos "" --disabled-password jupyterhub


# Add custom files
COPY --chown=jupyterhub:users ./custom/${JUPYTERHUB_VERSION} /src/jupyterhub-custom
RUN pip3 install -r /src/jupyterhub-custom/requirements.txt

# Add static files and templates
COPY --chown=jupyterhub:users ./static/${JUPYTERHUB_VERSION} /src/jupyterhub-static

# Install patches for specific JupyterHub Version
RUN apt update && apt install -y git \
 && git clone -b ${JUPYTERHUB_VERSION} https://github.com/jupyterhub/jupyterhub.git /src/jupyterhub \
 && rm -rf /src/jupyterhub/.git* \
 && apt remove -y git \
 && chown -R jupyterhub:users /src/jupyterhub
COPY --chown=jupyterhub:users ./patches/${JUPYTERHUB_VERSION}/patch_files /src/patches/${JUPYTERHUB_VERSION}/patch_files
COPY --chown=jupyterhub:users ./patches/install_patches.sh /src/patches/install_patches.sh
RUN /src/patches/install_patches.sh

# Add entrypoint
COPY --chown=jupyterhub:users ./entrypoint.sh /src/.
COPY --chown=jupyterhub:users ./entrypoint_devel.sh /src/.
USER jupyterhub
ENTRYPOINT ["/src/entrypoint.sh"]
