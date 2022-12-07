import logging
import os
import socket
import subprocess

from jupyterjsc_k8smgr.settings import LOGGER_NAME


log = logging.getLogger(LOGGER_NAME)
assert log.__class__.__name__ == "ExtraLoggerClass"


def set_uid():
    try:
        os.setuid(1000)
    except:
        pass


def check_connection(hostname, logs_extra):
    check = [
        "ssh",
        "-F",
        os.environ.get("SSHCONFIGFILE", "/home/k8smgr/.ssh/config"),
        "-O",
        "check",
        f"tunnel_{hostname}",
    ]

    # gunicorn preload app feature does not use gunicorn user/group but
    # the current uid instead. Which is root. We don't want to run commands as root.

    logs_extra["cmd"] = check
    log.debug("UserJobs - check connection", extra=logs_extra)
    with subprocess.Popen(
        check, stderr=subprocess.PIPE, stdout=subprocess.PIPE, preexec_fn=set_uid
    ) as p:
        stdout, stderr = p.communicate()
        returncode = p.returncode
        logs_extra["stdout"] = stdout
        logs_extra["stderr"] = stderr
        logs_extra["returncode"] = returncode
        log.debug("UserJobs - check connection done", extra=logs_extra)
        del logs_extra["stdout"]
        del logs_extra["stderr"]
        del logs_extra["returncode"]

    if returncode == 255:
        connect = [
            "ssh",
            "-F",
            os.environ.get("SSHCONFIGFILE", "/home/k8smgr/.ssh/config"),
            f"tunnel_{hostname}",
        ]
        logs_extra["cmd"] = connect
        log.debug("UserJobs - create connection", extra=logs_extra)
        with subprocess.Popen(
            connect, stderr=subprocess.PIPE, stdout=subprocess.PIPE, preexec_fn=set_uid
        ) as p:
            stdout, stderr = p.communicate()
            returncode = p.returncode
            logs_extra["stdout"] = stdout
            logs_extra["stderr"] = stderr
            logs_extra["returncode"] = returncode
            log.debug("UserJobs - create connection done", extra=logs_extra)
            del logs_extra["stdout"]
            del logs_extra["stderr"]
            del logs_extra["returncode"]
            del logs_extra["cmd"]

        if returncode != 0:
            raise Exception(f"Could not create connection to tunnel_{hostname}")


def get_port():
    with socket.socket() as s:
        s.bind(("", 0))
        return s.getsockname()[1]


def forward(target_ports, hostname, target_node, logs_extra):
    ret = {}
    log.debug("Forward ports", logs_extra)
    base_cmd = [
        "ssh",
        "-F",
        os.environ.get("SSHCONFIGFILE", "/home/k8smgr/.ssh/config"),
    ]
    for key, value in target_ports.items():
        if type(value) == set:
            port = value[0]
            v = value[1]
        else:
            port = get_port()
            v = value
        cmd = base_cmd + [
            "-O",
            "forward",
            f"0.0.0.0:{port}:{target_node}:{v}",
            f"tunnel_{hostname}",
        ]
        ret[key] = (port, v)
        with subprocess.Popen(
            cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE, preexec_fn=set_uid
        ) as p:
            stdout, stderr = p.communicate()
            returncode = p.returncode
            logs_extra["stdout"] = stdout
            logs_extra["stderr"] = stderr
            logs_extra["returncode"] = returncode
            logs_extra["cmd"] = cmd
            log.debug("Forward port done", extra=logs_extra)
            del logs_extra["stdout"]
            del logs_extra["stderr"]
            del logs_extra["returncode"]
            del logs_extra["cmd"]
            if returncode != 0:
                return ret, returncode
    return ret, 0


def cancel(used_ports, hostname, target_node, logs_extra):
    log.debug("Forward ports", logs_extra)
    base_cmd = [
        "ssh",
        "-F",
        os.environ.get("SSHCONFIGFILE", "/home/k8smgr/.ssh/config"),
    ]
    for key, value in used_ports.items():
        cmd = base_cmd + [
            "-O",
            "cancel",
            f"0.0.0.0:{value[0]}:{target_node}:{value[1]}",
            f"tunnel_{hostname}",
        ]
        with subprocess.Popen(
            cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE, preexec_fn=set_uid
        ) as p:
            stdout, stderr = p.communicate()
            returncode = p.returncode
            logs_extra["stdout"] = stdout
            logs_extra["stderr"] = stderr
            logs_extra["returncode"] = returncode
            logs_extra["cmd"] = cmd
            log.debug("Forward port done", extra=logs_extra)
            del logs_extra["stdout"]
            del logs_extra["stderr"]
            del logs_extra["returncode"]
            del logs_extra["cmd"]
