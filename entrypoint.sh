#!/bin/bash
export PYTHONPATH=${PYTHONPATH}:/src/jupyterhub
/usr/bin/jupyterhub ${@}
