import sys
custom_path = "<CUSTOM_PATH>"
sys.path.insert(1, custom_path)

from spawner import BackendSpawner
from apihandler import SpawnProgressUpdateAPIHandler
from apihandler import user_cancel_message
# from oauthenticator import CustomGenericOAuthenticator

from jupyterhub.auth import DummyAuthenticator

c.JupyterHub.cleanup_proxy = True
c.JupyterHub.default_url = "/hub/home"


c.JupyterHub.spawner_class = BackendSpawner
c.BackendSpawner.http_timeout = 900
c.JupyterHub.authenticator_class = DummyAuthenticator

import os
def dummy_hook(authenticator, handler, authentication):
    if authentication['auth_state'] is None:
        authentication['auth_state'] = {}
    authentication['auth_state']['access_token'] = "access_token"

    return authentication


c.DummyAuthenticator.post_auth_hook = dummy_hook
#c.JupyterHub.authenticator_class = CustomGenericOAuthenticator

#c.CustomGenericOAuthenticator.enable_auth_state = True
#c.CustomGenericOAuthenticator.client_id = "oauth-client"
#c.CustomGenericOAuthenticator.client_secret = "oauth-pass1"
#c.CustomGenericOAuthenticator.oauth_callback_url = "http://_host_/hub/oauth_callback"
#c.CustomGenericOAuthenticator.authorize_url = (
#    "https://localhost:2443/oauth2-as/oauth2-authz"
#)
#c.CustomGenericOAuthenticator.token_url = "https://localhost:2443/oauth2/token"
#c.CustomGenericOAuthenticator.tokeninfo_url = "https://localhost:2443/oauth2/tokeninfo"
#c.CustomGenericOAuthenticator.userdata_url = "https://localhost:2443/oauth2/userinfo"
#c.CustomGenericOAuthenticator.username_key = "email"
#c.CustomGenericOAuthenticator.scope = "single-logout;profile".split(";")
#c.CustomGenericOAuthenticator.tls_verify = False


#def foo():
#    ret = {"key1": ["value1", "value2"]}
#    return ret


#c.CustomGenericOAuthenticator.extra_params_allowed_runtime = foo
# http://localhost:8000/hub/oauth_login?extra_param_key1=value1


#c.JupyterHub.template_paths = ["data/templates"]
c.JupyterHub.template_vars = {
    "spawn_progress_update_url": "users/progress/update",
    "user_cancel_message": user_cancel_message,
}

c.JupyterHub.extra_handlers = [
    ("/api/users/progress/update/([^/]+)", SpawnProgressUpdateAPIHandler),
    ("/api/users/progress/update/([^/]+)/([^/]+)", SpawnProgressUpdateAPIHandler),
]
