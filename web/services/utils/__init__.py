import copy
import json
import logging
import os
from datetime import datetime
from datetime import timedelta

from jupyterjsc_k8smgr.settings import LOGGER_NAME

log = logging.getLogger(LOGGER_NAME)
assert log.__class__.__name__ == "ExtraLoggerClass"


class MgrExceptionError(Exception):
    pass


def get_error_message(config, logs_extra, key, default):
    if key in config.get("error_messages", {}):
        user_error_msg = config["error_messages"][key]
    else:
        log.critical(f"Missing error message in configuration: error_messages.{key}")
        user_error_msg = default
    log.critical(user_error_msg, extra=logs_extra, exc_info=True)
    return user_error_msg


global_config = {"last_lookup": datetime.min, "cached_value": {}}


def _config(timeout=60):
    global global_config
    now = datetime.now()
    if timedelta(seconds=timeout) < now - global_config["last_lookup"]:
        try:
            config_path = os.environ.get("CONFIG_PATH", "<CONFIG_PATH in Env not set>")
            log.debug(f"Reload configuration. - {config_path}")
            with open(config_path, "r") as f:
                config = json.load(f)
        except FileNotFoundError:
            log.critical(f"Could not load config ({config_path})", exc_info=True)
            config = {}
        global_config["cached_value"] = config
        global_config["last_lookup"] = now
    return global_config["cached_value"]


def get_custom_headers(request_headers):
    if "headers" in request_headers.keys():
        ret = copy.deepcopy(request_headers["headers"])
        return ret
    config = _config()
    custom_header_keys = config.get(
        "custom_headers_keys",
        {"HTTP_ACCESS_TOKEN": "access-token", "HTTP_UUIDCODE": "uuidcode"},
    )
    ret = {}
    for key, new_key in custom_header_keys.items():
        if key in request_headers.keys():
            ret[new_key] = request_headers[key]
    return ret
