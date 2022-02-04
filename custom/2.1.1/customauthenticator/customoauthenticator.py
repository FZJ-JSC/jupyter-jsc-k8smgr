from oauthenticator.generic import GenericOAuthenticator
from oauthenticator.oauth2 import OAuthLoginHandler
from oauthenticator.traitlets import Callable
from traitlets import Dict
from traitlets import Union
from traitlets import Unicode
from jupyterhub.handlers.login import LogoutHandler

import os
import uuid
import json
from tornado.httpclient import HTTPRequest
from custom_utils.backend import backend_request_properties
from datetime import datetime
from datetime import timedelta

class TimedCacheProperty(object):
    '''decorator to create get only property; values are fetched once per `timeout`'''
    def __init__(self, timeout):
        self._timeout = timedelta(seconds=timeout)
        self._func = None
        self._values = {}

    def __get__(self, instance, cls):
        last_lookup, value = self._values.get(instance, (datetime.min, None))
        now = datetime.now()
        if self._timeout < now - last_lookup:
            value = self._func(instance)
            self._values[instance] = now, value
        return value

    def __call__(self, func):
        self._func = func
        return self

class BackendLogoutHandler(LogoutHandler):
    async def backend_call(self):
        user = self.current_user
        if not user:
            self.log.debug("Could not receive current user in backend logout call.")
            return
        custom_config = user.authenticator.custom_config
        backend_revoke_url = custom_config.get("backend", {}).get("unity_revoke", {}).get("url", None)
        if not backend_revoke_url:
            self.log.critical("backend.unity_revoke.url in custom_config not defined. Cannot revoke Unity tokens.")
            return        
        req_prop = backend_request_properties(custom_config, self.log)
        if not req_prop:
            return        
        jhub_user_id = user.orm_user.id
        auth_state = await user.get_auth_state()
        access_token = auth_state.get("access_token", None)
        refresh_token = auth_state.get("refresh_token", None)
        tokens = {}
        if access_token:
            tokens["access_token"] = access_token
        if refresh_token:
            tokens["refresh_token"] = refresh_token
        arguments = self.request.query_arguments
        body = {
            "stop_services": arguments.get("stop_services", [b'false'])[0].decode().lower() == "true",
            "tokens": tokens,
            "jhub_user_id": jhub_user_id
        }
        uuidcode = uuid.uuid4().hex
        req = HTTPRequest(
            f"{backend_revoke_url}?uuidcode={uuidcode}",
            method="POST",
            headers=req_prop["headers"],
            body=json.dumps(body),
            request_timeout=req_prop["request_timeout"],
            validate_cert=req_prop["validate_cert"],
            ca_certs=req_prop["ca_certs"]
        )
        
        try:
            resp = await user.authenticator.fetch(req, parse_json=False)
            self.log.debug(f"Token revokation. -- 'uuidcode': {uuidcode}, 'response': {resp}")
        except Exception:
            self.log.exception(
                "Exception while revoking tokens",
                extra={
                    "uuidcode": uuidcode,
                    "user": user.name,
                    "action": "revoke_error",
                },
            )
        
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


custom_config_timeout = os.environ.get("CUSTOM_CONFIG_CACHE_TIME", 60)

class CustomGenericOAuthenticator(GenericOAuthenticator):
    login_handler = CustomGenericLoginHandler
    logout_handler = BackendLogoutHandler
    
    
    custom_config_file = Unicode('jupyterhub_custom_config.json', help="The custom config file to load").tag(
        config=True
    )
        
    @TimedCacheProperty(timeout=custom_config_timeout)
    def custom_config(self):
        self.log.debug("Load custom config file.")
        try:
            with open(self.custom_config_file, "r") as f:
                ret = json.load(f)
        except:
            self.log.warning("Could not load custom config file.", exc_info=True)
            ret = {}
        return ret

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
