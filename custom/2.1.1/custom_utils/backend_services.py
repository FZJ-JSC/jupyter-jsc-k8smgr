import json
import os
import uuid

from tornado.httpclient import HTTPClientError
from tornado.httpclient import HTTPResponse


class BackendException(Exception):
    error = "Unexpected error."
    error_detail = ""

    def __init__(self, error, error_detail=""):
        self.error = error
        self.error_detail = error_detail
        super().__init__(f"{error} --- {error_detail}")


def drf_request_properties(
    drf_service, custom_config, app_log, access_token=None, uuidcode=""
):
    drf_config = custom_config.get("drf-services")
    authentication_token_os = os.environ.get(
        f"{drf_service.upper()}_AUTHENTICATION_TOKEN", None
    )
    if authentication_token_os:
        authentication_token = authentication_token_os
    else:
        app_log.warning(
            f"{drf_service.upper()}_AUTHENTICATION_TOKEN not set in environment."
        )
        authentication_token_config = drf_config.get(drf_service, {}).get(
            "authentication_token", None
        )
        if authentication_token_config:
            app_log.warning(
                f"{drf_service}.authentication_token found in custom_config. You should not store secrets in config files in production"
            )
            authentication_token = authentication_token_config
        else:
            app_log.critical(
                f"{drf_service} authentication_token in custom_config not defined. Cannot communicate with {drf_service}."
            )
            return {}
    if not uuidcode:
        uuidcode = uuid.uuid4().hex
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": authentication_token,
        "uuidcode": uuidcode,
    }
    if access_token:
        headers["access-token"] = access_token
    certificate_path = drf_config.get(drf_service, {}).get("certificate_path", False)
    ca_certs = certificate_path if certificate_path else None
    validate_cert = True if ca_certs else False
    request_timeout = drf_config.get(drf_service, {}).get("request_timeout", 20)
    urls = drf_config.get(drf_service, {}).get("urls", {})
    ret = {
        "headers": headers,
        "ca_certs": ca_certs,
        "validate_cert": validate_cert,
        "request_timeout": request_timeout,
        "urls": urls,
    }
    return ret


async def drf_request(
    req,
    app_log,
    auth_fetch,
    action="",
    username="",
    log_name="",
    parse_json=True,
    raise_exception=False,
):
    safe_url = req.url.split("?")[0]
    app_log.debug(
        f"Communicate {action} with backend service {safe_url}",
        extra={
            "uuidcode": req.headers["uuidcode"],
            "log_name": log_name,
            "user": username,
            "action": action,
        },
    )
    try:
        resp = await auth_fetch(req, parse_json=parse_json)
        return resp
    except Exception as e:
        error = "Jupyter-JSC backend service communication failed."
        error_detail = str(e)
        if isinstance(e, HTTPClientError):
            if len(e.args) > 2:
                orig_response = e.args[2]
                if isinstance(orig_response, HTTPResponse):
                    error_json = json.loads(orig_response.body.decode("utf-8"))
                    try:
                        error = error_json.get("error", error)
                        error_detail = error_json.get("detailed_error", error_detail)
                    except:
                        # returned json is a list not a dictionary
                        # for example for missing access_token key in header
                        error_detail = error_json[0]
        app_log.exception(
            "Exception while communicating with backend drf service",
            extra={
                "uuidcode": req.headers["uuidcode"],
                "log_name": log_name,
                "user": username,
                "action": action,
                "error_msg": error,
                "error_msg_detail": error_detail,
            },
        )
        if raise_exception:
            raise BackendException(error, error_detail)
    return {}
