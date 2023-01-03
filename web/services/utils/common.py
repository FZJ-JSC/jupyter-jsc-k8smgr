import copy
import logging
import uuid

from jupyterjsc_k8smgr.settings import LOGGER_NAME
from services.utils import _config
from services.utils import get_error_message
from services.utils import k8s
from services.utils import MgrExceptionError
from services.utils import ssh

log = logging.getLogger(LOGGER_NAME)
assert log.__class__.__name__ == "ExtraLoggerClass"


def start_service(
    validated_data, initial_data, custom_headers, jhub_credential, logs_extra
):
    log.debug("Service start", extra=logs_extra)

    servername = validated_data["servername"]
    drf_id = f"{servername}-{validated_data['start_id']}"
    config = _config()

    try:
        k8s.start_service(
            servername,
            drf_id,
            config,
            validated_data,
            initial_data,
            custom_headers,
            jhub_credential,
            logs_extra=logs_extra,
        )
        log.info("Service start finished", extra=logs_extra)
        return
    except (MgrExceptionError, Exception) as e:
        log.warning(
            "Service start failed",
            extra=logs_extra,
            exc_info=True,
        )
        stop_service_data = copy.deepcopy(validated_data)
        stop_service_data["id"] = drf_id
        stop_service(
            stop_service_data,
            custom_headers,
            raise_exception=False,
            logs_extra=logs_extra,
        )
        if e.__class__.__name__ == "MgrExceptionError":
            e_args = e.args
        else:
            user_error_msg = get_error_message(
                config,
                logs_extra,
                "services.utils.common.start_service_2",
                "Could not start service",
            )
            e_args = (user_error_msg, str(e))
        raise MgrExceptionError(*e_args)


def status_service(instance_dict, custom_headers, logs_extra):
    log.debug("Service status check", extra=logs_extra)

    drf_id = f"{instance_dict['servername']}-{instance_dict['start_id']}"
    config = _config()
    try:
        ret = k8s.status_service(drf_id, config, logs_extra=logs_extra)
        log.debug(f"Service status check finished - {ret}", extra=logs_extra)
        return ret
    except (MgrExceptionError, Exception) as e:
        log.warning(
            "Service status check failed",
            extra=logs_extra,
            exc_info=True,
        )
        if e.__class__.__name__ == "MgrExceptionError":
            e_args = e.args
        else:
            user_error_msg = get_error_message(
                config,
                logs_extra,
                "services.utils.status_service",
                "Could not check status service.",
            )
            e_args = (user_error_msg, str(e))
        raise MgrExceptionError(*e_args)


def stop_service(instance_dict, custom_headers, logs_extra, raise_exception=True):
    log.debug("Service stop", extra=logs_extra)

    drf_id = f"{instance_dict['servername']}-{instance_dict['start_id']}"
    config = _config()

    try:
        k8s.stop_service(drf_id, config, logs_extra=logs_extra)
        log.info("Service stop finished", extra=logs_extra)
        return
    except (MgrExceptionError, Exception) as e:
        log.warning(
            "Service stop failed",
            extra=logs_extra,
            exc_info=True,
        )
        if e.__class__.__name__ == "MgrExceptionError":
            e_args = e.args
        else:
            user_error_msg = get_error_message(
                config,
                logs_extra,
                "services.utils.common.stop_service",
                "Could not stop service",
            )
            e_args = (user_error_msg, str(e))
        log.debug(
            f"Error message (raise_exception={raise_exception}): {e_args}",
            extra=logs_extra,
        )
        if raise_exception:
            raise MgrExceptionError(*e_args)


def initial_data_to_logs_extra(servername, initial_data, custom_headers):
    # Remove secrets for logging
    logs_extra = copy.deepcopy(initial_data)
    logs_extra.update(copy.deepcopy(custom_headers))

    if "env" in logs_extra.keys():
        logs_extra["env"]["JUPYTERHUB_API_TOKEN"] = "***"
    if "access_token" in logs_extra.get("auth_state", {}).keys():
        logs_extra["auth_state"]["access_token"] = "***"
    if "JPY_API_TOKEN" in logs_extra.get("env", {}).keys():  # deprecated in JupyterHub
        logs_extra["env"]["JPY_API_TOKEN"] = "***"
    if "access-token" in logs_extra.keys():
        logs_extra["access-token"] = "***"
    if "uuidcode" not in logs_extra.keys():
        logs_extra["uuidcode"] = servername
    if "certs" in logs_extra.keys():
        logs_extra["certs"] = "***"
    return logs_extra


def instance_dict_and_custom_headers_to_logs_extra(instance_dict, custom_headers):
    # Remove secrets for logging
    logs_extra = copy.deepcopy(instance_dict)
    logs_extra.update(copy.deepcopy(custom_headers))
    if "start_date" in logs_extra.keys():
        if logs_extra["start_date"].__class__.__name__ == "datetime":
            logs_extra["start_date"] = logs_extra["start_date"].isoformat()
    if "_state" in logs_extra.keys():
        del logs_extra["_state"]
    if "access-token" in logs_extra.keys():
        logs_extra["access-token"] = "***"
    if "uuidcode" not in logs_extra.keys():
        logs_extra["uuidcode"] = uuid.uuid4().hex
    return logs_extra


def userjobs_create_ssh_tunnels(target_ports, hostname, target_node, logs_extra):
    log.debug("UserJobs - Create ssh tunnel", extra=logs_extra)
    ssh.check_connection(hostname, logs_extra)
    used_ports, returncode = ssh.forward(
        target_ports, hostname, target_node, logs_extra
    )
    log.debug("UserJobs - Create ssh tunnel done", extra=logs_extra)
    return used_ports, returncode


def userjobs_create_k8s_svc(servername, suffix, used_ports, logs_extra):
    k8s.k8s_create_userjobs_svc(servername, suffix, used_ports, logs_extra)


def userjobs_delete_ssh_tunnels(used_ports, hostname, target_node, logs_extra):
    ssh.cancel(used_ports, hostname, target_node, logs_extra)


def userjobs_delete_k8s_svc(servername, suffix, logs_extra):
    k8s.k8s_delete_userjobs_svc(f"{servername}-{suffix}", logs_extra)
