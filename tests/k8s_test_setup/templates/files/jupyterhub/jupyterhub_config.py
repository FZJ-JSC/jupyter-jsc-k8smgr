from traitlets.config.application import get_config
c = get_config()

import sys
custom_path = "/src/jupyterhub-custom"
sys.path.insert(1, custom_path)

from spawner import BackendSpawner
from apihandler import SpawnCancelAPIHandler
from apihandler import SpawnUpdateOptionsAPIHandler
from apihandler import SpawnProgressUpdateAPIHandler, SpawnProgressStatusAPIHandler
from apihandler import user_cancel_message
from apihandler import SpawnNotificationAPIHandler
from customauthenticator import CustomGenericOAuthenticator, BackendLogoutHandler

c.JupyterHub.log_level = 10
c.JupyterHub.custom_config_file = '/home/jupyterhub/jupyterhub_custom_config.json'
c.JupyterHub.db_url = 'sqlite:////home/jupyterhub/jupyterhub.sqlite'
c.JupyterHub.pid_file = '/home/jupyterhub/jupyterhub.pid'
c.JupyterHub.cookie_secret_file = '/home/jupyterhub/jupyterhub_cookie_secret'
c.ConfigurableHTTPProxy.pid_file = '/home/jupyterhub/jupyterhub-proxy.pid'

c.JupyterHub.cleanup_proxy = True
c.JupyterHub.default_url = "/hub/home"
c.JupyterHub.allow_named_servers = True

c.JupyterHub.spawner_class = BackendSpawner
c.BackendSpawner.http_timeout = 900

c.JupyterHub.authenticator_class = CustomGenericOAuthenticator

c.CustomGenericOAuthenticator.custom_config_file = '/home/jupyterhub/jupyterhub_custom_config.json'
c.CustomGenericOAuthenticator.enable_auth_state = True
c.CustomGenericOAuthenticator.client_id = "oauth-client"
c.CustomGenericOAuthenticator.client_secret = "oauth-pass1"
c.CustomGenericOAuthenticator.oauth_callback_url = "http://jupyterhub-<ID>.<NAMESPACE>.svc/hub/oauth_callback"
c.CustomGenericOAuthenticator.authorize_url = (
    "https://unity-<ID>.<NAMESPACE>.svc/oauth2-as/oauth2-authz"
)
c.CustomGenericOAuthenticator.token_url = "https://unity-<ID>.<NAMESPACE>.svc/oauth2/token"
c.CustomGenericOAuthenticator.tokeninfo_url = "https://unity-<ID>.<NAMESPACE>.svc/oauth2/tokeninfo"
c.CustomGenericOAuthenticator.userdata_url = "https://unity-<ID>.<NAMESPACE>.svc/oauth2/userinfo"
c.CustomGenericOAuthenticator.username_key = "email"
c.CustomGenericOAuthenticator.scope = "single-logout;hpc_infos;x500;authenticator;eduperson_entitlement;username;profile".split(";")
c.CustomGenericOAuthenticator.tls_verify = False


#def foo():
#    ret = {"key1": ["value1", "value2"]}
#    return ret


#c.CustomGenericOAuthenticator.extra_params_allowed_runtime = foo
# http://localhost:8000/hub/oauth_login?extra_param_key1=value1


c.JupyterHub.template_paths = ["/home/jupyterhub/jupyterhub-static/templates"]
c.JupyterHub.template_vars = {
    "spawn_progress_update_url": "users/progress/update",
    "user_cancel_message": user_cancel_message,
    "hostname": "<JUPYTERHUB_ALT_NAME>"
}
c.JupyterHub.data_files_path = '/home/jupyterhub/jupyterhub-static'


from handler import page_handlers
from apihandler import twoFA, vo

c.JupyterHub.extra_handlers = [
    # PageHandlers
    (r"/links", page_handlers.LinksHandler),
    (r"/2FA", page_handlers.TwoFAHandler),
    (r"/imprint", page_handlers.ImprintHandler),
    (r"/privacy", page_handlers.DPSHandler),
    (r"/terms", page_handlers.ToSHandler),
    (r"/groups", page_handlers.VOHandler),
    (r"/signout", BackendLogoutHandler),
    # APIHandlers
    (r"/api/users/([^/]+)/servers/([^/]*)/cancel", SpawnCancelAPIHandler),
    (r"/api/users/([^/]+)/server/cancel", SpawnCancelAPIHandler),
    (r"/api/users/([^/]+)/server/update", SpawnUpdateOptionsAPIHandler),
    (r"/api/users/([^/]+)/servers/([^/]*)/update", SpawnUpdateOptionsAPIHandler),
    (r"/api/users/progress/update/([^/]+)", SpawnProgressUpdateAPIHandler),
    (r"/api/users/progress/update/([^/]+)/([^/]+)", SpawnProgressUpdateAPIHandler),
    (r"/api/users/progress/status/([^/]+)", SpawnProgressStatusAPIHandler),
    (r"/api/users/progress/status/([^/]+)/([^/]+)", SpawnProgressStatusAPIHandler),
    (r"/api/users/([^/]+)/notifications/spawners", SpawnNotificationAPIHandler),
    (r"/api/2FA", twoFA.TwoFAAPIHandler),
    (r"/2FA/([^/]+)", twoFA.TwoFACodeHandler),
    (r"/api/vo/([^/]+)", vo.VOAPIHandler),
    (r"/api/votoken/([^/]+)", vo.VOTokenAPIHandler),
]
