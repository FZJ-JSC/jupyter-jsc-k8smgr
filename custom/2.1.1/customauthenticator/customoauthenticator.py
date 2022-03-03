import json
import os
import re
import uuid
from audioop import adpcm2lin
from datetime import datetime
from datetime import timedelta

from custom_utils import get_vos, VoException
from custom_utils.backend_services import drf_request
from custom_utils.backend_services import drf_request_properties
from oauthenticator.generic import GenericOAuthenticator
from oauthenticator.oauth2 import OAuthLoginHandler, OAuthLogoutHandler
from oauthenticator.traitlets import Callable
from tornado.httpclient import HTTPClientError
from tornado.httpclient import HTTPRequest
from traitlets import Dict
from traitlets import Unicode
from traitlets import Union


class TimedCacheProperty(object):
    """decorator to create get only property; values are fetched once per `timeout`"""

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


class BackendLogoutHandler(OAuthLogoutHandler):
    async def backend_call(self):
        user = self.current_user
        if not user:
            self.log.debug("Could not receive current user in backend logout call.")
            return
        custom_config = user.authenticator.custom_config
        req_prop = drf_request_properties("backend", custom_config, self.log)
        if not req_prop:
            return
        backend_revoke_url = req_prop.get("urls", {}).get("token_revokation", "None")
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
            "stop_services": arguments.get("stop_services", [b"false"])[0]
            .decode()
            .lower()
            == "true",
            "tokens": tokens,
            "jhub_user_id": jhub_user_id,
        }
        uuidcode = uuid.uuid4().hex
        req = HTTPRequest(
            f"{backend_revoke_url}?uuidcode={uuidcode}",
            method="POST",
            headers=req_prop["headers"],
            body=json.dumps(body),
            request_timeout=req_prop["request_timeout"],
            validate_cert=req_prop["validate_cert"],
            ca_certs=req_prop["ca_certs"],
        )
        max_revocation_attempts = 1
        return await drf_request(
            uuidcode,
            req,
            self.log,
            user.authenticator.fetch,
            "revocation",
            user.name,
            f"{user.name}::token_revocation",
            max_revocation_attempts,
            parse_json=False,
            raise_exception=False,
        )

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

    custom_config_file = Unicode(
        "jupyterhub_custom_config.json", help="The custom config file to load"
    ).tag(config=True)
    tokeninfo_url = Unicode(
        config=True,
        help="""The url retrieving information about the access token""",
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

    async def post_auth_hook(self, authenticator, handler, authentication):
        access_token = authentication["auth_state"]["access_token"]
        headers = {
            "Accept": "application/json",
            "User-Agent": "JupyterHub",
            "Authorization": f"Bearer {access_token}",
        }
        req = HTTPRequest(self.tokeninfo_url, method="GET", headers=headers)
        try:
            resp = await authenticator.fetch(req)
        except HTTPClientError as e:
            authenticator.log.warning(
                "Could not request user information - {}".format(e)
            )
            raise Exception(e)
        authentication["auth_state"]["exp"] = resp.get("exp")
        authentication["auth_state"]["last_login"] = datetime.now().strftime(
            "%H:%M:%S %Y-%m-%d"
        )

        used_authenticator = (
            authentication["auth_state"]
            .get("oauth_user", {})
            .get("used_authenticator_attr", "unknown")
        )
        hpc_list = (
            authentication.get("auth_state", {})
            .get("oauth_user", {})
            .get("hpc_infos_attribute", [])
        )
        hpc_infos_via_unity = str(len(hpc_list) > 0).lower()
        handler.statsd.incr(f"login.authenticator.{used_authenticator}")
        handler.statsd.incr(f"login.hpc_infos_via_unity.{hpc_infos_via_unity}")

        username = authentication.get("name", "unknown")
        admin = authentication.get("admin", False)

        try:
            vo_active, vo_available = get_vos(
                authentication["auth_state"], self.custom_config, username, admin=admin
            )
        except VoException as e:
            authenticator.log.warning(
                "Could not get vo for user - {}".format(e)
            )
            raise e
        authentication["auth_state"]["vo_active"] = vo_active
        authentication["auth_state"]["vo_available"] = vo_available

        default_partitions = self.custom_config.get("default_partitions")
        to_add = []
        if type(hpc_list) == str:
            hpc_list = [hpc_list]
        elif type(hpc_list) == list and len(hpc_list) > 0 and len(hpc_list[0]) == 1:
            hpc_list = ["".join(hpc_list)]
        for entry in hpc_list:
            try:
                partition = re.search("[^,]+,([^,]+),[^,]+,[^,]+", entry).groups()[0]
            except:
                authenticator.log.info(
                    f"----- {username} - Failed to check for defaults partitions: {entry} ---- {hpc_list}"
                )
                continue
            if partition in default_partitions.keys():
                for value in default_partitions[partition]:
                    to_add.append(entry.replace(f",{partition},", ",{},".format(value)))
        hpc_list.extend(to_add)
        if hpc_list:
            authentication["auth_state"]["oauth_user"]["hpc_infos_attribute"] = hpc_list

        authenticator.log.info(authentication)
        return authentication
