from oauthenticator.generic import GenericOAuthenticator
from oauthenticator.oauth2 import OAuthLoginHandler
from oauthenticator.traitlets import Callable
from traitlets import Dict
from traitlets import Union
from jupyterhub.handlers.login import LogoutHandler

class BackendLogoutHandler(LogoutHandler):
    async def backend_call(self):
        arguments = self.request.query_arguments
        user = self.current_user
        if not user:
            # log warning
            return
        custom_config = self.app.custom_config
        jhub_user_id = user.orm_user.id
        auth_state = await user.get_auth_state()
        access_token = auth_state.get("access_token", None)
        refresh_token = auth_state.get("refresh_token", None)
        tokens = {}
        if access_token:
            tokens["access_token"] = access_token
        if refresh_token:
            tokens["refresh_token"] = refresh_token
        body = {
            "stop_services": arguments.get("stop_services", [b'false'])[0].decode().lower() == "true",
            "tokens": tokens,
            "jhub_user_id": jhub_user_id
        }
        
        return await super().handle_logout()
    
    async def get(self):
        await self.backend_call()
        return await super().get()

class CustomGenericLoginHandler(OAuthLoginHandler):
    def authorize_redirect(self, *args, **kwargs):
        extra_params = kwargs.setdefault("extra_params", {})
        if self.authenticator.extra_params_allowed_runtime:
            if callable(self.authenticator.extra_params_allowed_runtime):
                extra_params_allowed = self.authenticator.extra_params_allowed_runtime()
            else:
                extra_params_allowed = self.authenticator.extra_params_allowed_runtime
            extra_params.update(
                {
                    k[len("extra_param_") :]: "&".join([x.decode("utf-8") for x in v])
                    for k, v in self.request.arguments.items()
                    if k.startswith("extra_param_")
                    and set([x.decode("utf-8") for x in v]).issubset(
                        extra_params_allowed.get(k[len("extra_param_") :], [])
                    )
                }
            )
        return super().authorize_redirect(*args, **kwargs)


class CustomGenericOAuthenticator(GenericOAuthenticator):
    login_handler = CustomGenericLoginHandler
    logout_handler = BackendLogoutHandler
    

    extra_params_allowed_runtime = Union(
        [Dict(), Callable()],
        config=True,
        help="""Allowed extra GET params to send along with the initial OAuth request
        to the OAuth provider.
        Usage: GET to localhost:8000/hub/oauth_login?extra_param_<key>=<value>
        This argument defines the allowed keys and values.
        Example:
        ```
        {
            "key": ["value1", "value2"],
        }
        ```
        All accepted extra params will be forwarded without the `extra_param_` prefix.
        """,
    )

    def get_callback_url(self, handler=None):
        # Replace _host_ in callback_url with current request
        ret = super().get_callback_url(handler)
        if self.oauth_callback_url and handler and "_host_" in ret:
            ret = ret.replace("_host_", handler.request.host)
        return ret
