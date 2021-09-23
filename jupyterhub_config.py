from jupyterhub.auth import DummyAuthenticator

from custom.apihandler import SpawnProgressUpdateAPIHandler
from custom.apihandler import user_cancel_message
from custom.spawner import BackendSpawner

c.JupyterHub.cleanup_proxy = True
c.ConfigurableHTTPProxy.debug = True

c.JupyterHub.spawner_class = BackendSpawner
c.BackendSpawner.http_timeout = 40
c.BackendSpawner.default_url = "/hub/home"

c.JupyterHub.authenticator_class = DummyAuthenticator

c.DummyAuthenticator.enable_auth_state = True

c.JupyterHub.template_paths = ["data/templates"]
c.JupyterHub.template_vars = {
    "spawn_progress_update_url": "users/progress/update",
    "user_cancel_message": user_cancel_message,
}

c.JupyterHub.extra_handlers = [
    ("/api/users/progress/update/([^/]+)/", SpawnProgressUpdateAPIHandler),
    ("/api/users/progress/update/([^/]+)/([^/]+)", SpawnProgressUpdateAPIHandler),
]
