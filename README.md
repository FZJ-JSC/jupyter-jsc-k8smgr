# JupyterHub for Jupyter-JSC

## Current Status

Currently it's a JupyterHub with a skeleton BackendSpawner including Cancel and StatusUpdates features.
There are a few functional tests already to test the website.

## TODOs

A lot.  
Next steps:

- Let skeleton BackendSpawner use our BackendService. Let it send hard coded the correct user_options and tokens.
- If we're able to start a Job in the Unicore Images with Basic-JupyterHub and BackendService we can move forward.

- Configure Unity TestInstance to allow Login with Unity-local test user
- Configure UNICORE TestInstances to use Unity as authenticator.
- Use OAuthenticator with Unity as Login, use received access_token to start Job via Backend and UNICORE

## Build

geckodriver required

```
git clone <this_repo>
python3 -m venv venv
source venv/bin/activate
pip3 install -U pip
pip3 install -r build-requirements.txt
pip3 install -e custom

set -a ; source .env ; set +a; jupyterhub -f jupyterhub_config.py
pytest
```
