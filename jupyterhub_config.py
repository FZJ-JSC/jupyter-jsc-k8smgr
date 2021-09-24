# from jupyterhub.auth import DummyAuthenticator
import os

from custom.apihandler import SpawnProgressUpdateAPIHandler
from custom.apihandler import user_cancel_message
from custom.oauthenticator import CustomGenericOAuthenticator
from custom.spawner import BackendSpawner

c.JupyterHub.cleanup_proxy = True
c.ConfigurableHTTPProxy.debug = True

c.JupyterHub.spawner_class = BackendSpawner
c.BackendSpawner.http_timeout = 40
c.BackendSpawner.default_url = "/hub/home"

# c.JupyterHub.authenticator_class = DummyAuthenticator
c.JupyterHub.authenticator_class = CustomGenericOAuthenticator

c.CustomGenericOAuthenticator.enable_auth_state = True
c.CustomGenericOAuthenticator.client_id = "jupyter-jsc.fz-juelich.de"
c.CustomGenericOAuthenticator.client_secret = os.environ.get("OAUTH_SECRET", "")
c.CustomGenericOAuthenticator.oauth_callback_url = "http://_host_/hub/oauth_callback"
# c.CustomGenericOAuthenticator.oauth_callback_url = "https://jupyter-jsc-devel.fz-juelich.de/hub/oauth_callback"
c.CustomGenericOAuthenticator.authorize_url = (
    "https://unity-jsc-integration.fz-juelich.de/jupyter-oauth2-as/oauth2-authz"
)
c.CustomGenericOAuthenticator.token_url = (
    "https://unity-jsc-integration.fz-juelich.de/jupyter-oauth2/token"
)
c.CustomGenericOAuthenticator.tokeninfo_url = (
    "https://unity-jsc-integration.fz-juelich.de/jupyter-oauth2/tokeninfo"
)
c.CustomGenericOAuthenticator.userdata_url = (
    "https://unity-jsc-integration.fz-juelich.de/jupyter-oauth2/userinfo"
)
c.CustomGenericOAuthenticator.username_key = "username_attr"
c.CustomGenericOAuthenticator.scope = (
    "single-logout;hpc_infos;x500;authenticator;eduperson_entitlement;username".split(
        ";"
    )
)
c.CustomGenericOAuthenticator.tls_verify = False


def foo():
    ret = {"key1": ["value1", "value2"]}
    return ret


c.CustomGenericOAuthenticator.extra_params_allowed_runtime = foo
# http://localhost:8000/hub/oauth_login?extra_param_key1=value1


c.JupyterHub.template_paths = ["data/templates"]
c.JupyterHub.template_vars = {
    "spawn_progress_update_url": "users/progress/update",
    "user_cancel_message": user_cancel_message,
}

c.JupyterHub.extra_handlers = [
    ("/api/users/progress/update/([^/]+)/", SpawnProgressUpdateAPIHandler),
    ("/api/users/progress/update/([^/]+)/([^/]+)", SpawnProgressUpdateAPIHandler),
]
