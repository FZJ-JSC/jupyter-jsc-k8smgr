#!/bin/bash
export PYTHONPATH=${PYTHONPATH}:/src/jupyterhub:/src/jupyterhub-custom

USERNAME=jovyan

/usr/bin/jupyterhub ${@}
