# Update maintenances every n seconds
import fcntl
import json
import logging.handlers
import os
import socket
import sys
import time
import traceback

import requests
from dateutil import parser
from jsonformatter import JsonFormatter

LOGGER_NAME = os.environ.get("LOGGER_NAME", "MaintenanceCheck")
log = logging.getLogger(LOGGER_NAME)
log.level = 10


def acquireReadLock(filename):
    """acquire exclusive lock file access"""
    if not os.path.exists(filename):
        with open(filename, "w") as f:
            f.write("")
    locked_file_descriptor = open(filename, "r+")
    fcntl.lockf(locked_file_descriptor, fcntl.LOCK_EX)
    return locked_file_descriptor


def acquireLock(filename):
    """acquire exclusive lock file access"""
    if not os.path.exists(filename):
        with open(filename, "w") as f:
            f.write("")
    locked_file_descriptor = open(filename, "w+")
    fcntl.lockf(locked_file_descriptor, fcntl.LOCK_EX)
    return locked_file_descriptor


def releaseLock(locked_file_descriptor):
    """release exclusive lock file access"""
    if locked_file_descriptor:
        locked_file_descriptor.close()


def write_to_file(filename, fileinput):
    log.debug(f"Write to file {filename}: {fileinput}")
    try:
        lock_fd = acquireLock(filename) or None
        lock_fd.write(fileinput)
    except:
        log.exception(f"Could not write to file {filename}")
    finally:
        releaseLock(lock_fd)


def read_json_file(filename):
    try:
        lock_fd = acquireReadLock(filename) or None
        with open(filename, "r") as f:
            ret = json.load(f)
    except:
        log.exception(f"Could not read from file {filename}")
    finally:
        releaseLock(lock_fd)
    return ret


def setup_next_maintenance(system, id, all_incidents, next_maintenance, output_dir):
    system_incidents = [
        x for x in all_incidents if id in x.get("affected_services", [])
    ]
    next_maintenance_incident = [
        x
        for x in system_incidents
        if parser.parse(x["start_time"]) == parser.parse(next_maintenance)
    ]
    if len(next_maintenance_incident) == 0:
        raise Exception(f"Could not find matching start time in incidents for {system}")
    if len(next_maintenance_incident) > 1:
        log.warning(
            "Multiple incidents for the same datetime. Use first first one in list"
        )
    next_maintenance_incident = next_maintenance_incident[0]
    short_description = next_maintenance_incident["short_description"]
    if short_description:
        description = short_description
    else:
        description = next_maintenance_incident["description"]
    start_time = next_maintenance_incident["start_time"]
    if next_maintenance_incident["end_time"]:
        end_time = next_maintenance_incident["end_time"]
    else:
        end_time = "unknown"
    info_msg = f"{start_time} - {end_time}: {description}"
    write_to_file(f"{output_dir}/{system.upper()}.txt", info_msg)


def no_next_maintenance(system, output_dir):
    write_to_file(f"{output_dir}/{system.upper()}.txt", "")


def update_maintenance_file(
    system, output_dir, svc, systems_maintenance_list, maintenance_health_threshold
):
    # if svc["health"] > maintenance_health_threshold:
    if svc["next_maintenance"] and svc["health"] > maintenance_health_threshold:
        # System is in maintenance state, but not in the list
        if system.upper() not in systems_maintenance_list:
            systems_maintenance_list_update = read_json_file(
                f"{output_dir}/maintenance.json"
            )
            systems_maintenance_list_update.append(system.upper())
            log.info(f"Write to maintenance.json: {systems_maintenance_list_update}")
            write_to_file(
                f"{output_dir}/maintenance.json",
                json.dumps(systems_maintenance_list_update),
            )
    else:
        # System is not in maintenance state, but still in the list
        if system.upper() in systems_maintenance_list:
            systems_maintenance_list_prev = read_json_file(
                f"{output_dir}/maintenance.json"
            )
            systems_maintenance_list_new = [
                x for x in systems_maintenance_list_prev if x != system.upper()
            ]
            log.info(
                f"Write to {output_dir}/maintenance.json: {systems_maintenance_list_new}"
            )
            write_to_file(
                f"{output_dir}/maintenance.json",
                json.dumps(systems_maintenance_list_new),
            )


def check_maintenances(config_mc, output_dir):
    api_url = config_mc.get("url", "https://status.jsc.fz-juelich.de/api")
    maintenance_health_threshold = config_mc.get("health_threshold", 0)
    systems_maintenance_list = read_json_file(f"{output_dir}/maintenance.json")
    try:
        all_incidents_r = requests.get(f"{api_url}/incidents", timeout=5)
        all_incidents_r.raise_for_status()
        all_incidents = all_incidents_r.json()
        for name, id in config_mc["services"].items():
            try:
                svc_r = requests.get(f"{api_url}/services/{id}", timeout=5)
                svc_r.raise_for_status()
                svc = svc_r.json()
                update_maintenance_file(
                    name,
                    output_dir,
                    svc,
                    systems_maintenance_list,
                    maintenance_health_threshold,
                )
                next_maintenance = svc["next_maintenance"]
                if next_maintenance:
                    setup_next_maintenance(
                        name, id, all_incidents, next_maintenance, output_dir
                    )
                else:
                    no_next_maintenance(name, output_dir)
            except:
                log.exception(f"Could not check for maintenances for {name}")
    except:
        log.exception("Could not check for maintenances")


supported_handler_classes = {
    "stream": logging.StreamHandler,
    "file": logging.handlers.TimedRotatingFileHandler,
    "smtp": logging.handlers.SMTPHandler,
    "syslog": logging.handlers.SysLogHandler,
}

# supported formatters and their arguments
supported_formatter_classes = {"json": JsonFormatter, "simple": logging.Formatter}
json_fmt = '{"asctime": "asctime", "levelno": "levelno", "levelname": "levelname", "logger": "name", "file": "pathname", "line": "lineno", "function": "funcName", "Message": "message"}'
simple_fmt = "%(asctime)s logger=%(name)s levelno=%(levelno)s levelname=%(levelname)s file=%(pathname)s line=%(lineno)d function=%(funcName)s : %(message)s"
supported_formatter_kwargs = {
    "json": {"fmt": json_fmt},
    "simple": {"fmt": simple_fmt},
}


def setup_logger(handler_name, configuration):
    configuration_logs = {"configuration": str(configuration)}
    formatter_name = configuration.pop("formatter")
    level = configuration.pop("level")

    # catch some special cases
    for key, value in configuration.items():
        if key == "stream":
            if value == "ext://sys.stdout":
                configuration["stream"] = sys.stdout
            elif value == "ext://sys.stderr":
                configuration["stream"] = sys.stderr
        elif key == "socktype":
            if value == "ext://socket.SOCK_STREAM":
                configuration["socktype"] = socket.SOCK_STREAM
            elif value == "ext://socket.SOCK_DGRAM":
                configuration["socktype"] = socket.SOCK_DGRAM
        elif key == "address":
            configuration["address"] = tuple(value)
    handler = supported_handler_classes[handler_name](**configuration)
    formatter = supported_formatter_classes[formatter_name](
        **supported_formatter_kwargs[formatter_name]
    )
    handler.name = handler_name
    handler.setLevel(level)
    handler.setFormatter(formatter)
    logger = logging.getLogger(LOGGER_NAME)
    logger.addHandler(handler)
    log.debug(f"Logging handler added ({handler_name}): {configuration_logs}")


if __name__ == "__main__":
    with open(os.environ["CUSTOM_CONFIG_PATH"], "r") as f:
        config = json.load(f)
    output_dir = os.environ["OUTPUT_DIR"]
    maintenance_json = f"{output_dir}/maintenance.json"
    for name, logger_config in config["maintenance-check"].get("logger", {}).items():
        setup_logger(name, logger_config)
    if not os.path.exists(maintenance_json):
        with open(maintenance_json, "w") as f:
            f.write(json.dumps([]))
    if not os.path.isfile(maintenance_json):
        log.error(f"{maintenance_json} must be a file. Exit")
        exit(1)
    while True:
        check_maintenances(config["maintenance-check"], output_dir)
        time.sleep(config["maintenance-check"].get("interval", 60))
