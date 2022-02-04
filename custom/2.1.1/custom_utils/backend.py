import os

def backend_request_properties(custom_config, app_log):
    backend_authentication_token_os = os.environ.get("BACKEND_AUTHENTICATION_TOKEN", None)
    if backend_authentication_token_os:
        backend_authentication_token = backend_authentication_token_os
    else:
        app_log.warning("BACKEND_AUTHENTICATION_TOKEN not set in environment.")
        backend_authentication_token_config = custom_config.get("backend", {}).get("authentication_token", None)
        if backend_authentication_token_config:
            app_log.warning("backend.authentication_token found in custom_config. You should not store secrets in config files in production")
            backend_authentication_token = backend_authentication_token_config
        else:
            app_log.critical("backend authentication_token in custom_config not defined. Cannot revoke Unity tokens.")
            return {}
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": backend_authentication_token
    }
    certificate_path = custom_config.get("backend", {}).get("certificate_path", False)
    ca_certs = certificate_path if certificate_path else None
    validate_cert = True if ca_certs else False
    request_timeout = custom_config.get("backend", {}).get("request_timeout", 20)
    ret = {
        "headers": headers,
        "ca_certs": ca_certs,
        "validate_cert": validate_cert,
        "request_timeout": request_timeout
    }
    return ret