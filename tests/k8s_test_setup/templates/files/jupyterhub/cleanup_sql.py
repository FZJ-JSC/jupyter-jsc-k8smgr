import datetime
import json
import os
import sqlite3 as sql
import time

import requests

custom_conf_file = os.environ.get(
    "CUSTOM_CONFIG_PATH", "/home/jupyterhub/jupyterhub_custom_config.json"
)

uuidcode = "jupyterhubs-side-cleanup-cronjob"

drf_headers = {
    "Content-Type": "application/json",
    "Accept": "application/json",
    "uuidcode": uuidcode,
}


def now():
    return datetime.datetime.now().strftime("%Y_%m_%d %H:%M:%S.%f")[:-3]


def get_jhub_server(db):
    connection = sql.connect(db)
    query = "SELECT spawners.name FROM spawners WHERE spawners.started IS NOT NULL"
    cur = connection.cursor()
    cur.execute(query)
    output = cur.fetchall()
    ret = [x[0] for x in output]
    return ret


def started_n_minutes_ago(n, started):
    now = datetime.datetime.now()
    started_d = datetime.datetime.strptime(started, "%Y-%m-%dT%H:%M:%S.%fZ")
    running_since = (now - started_d).total_seconds()
    if divmod(running_since, 60)[0] > n:
        return True
    return False


def cleanup_drf_services(jhub_server, custom_conf, grace_period):
    drf_services = [
        k
        for k, v in custom_conf.get("drf-services", {}).items()
        if "services" in v.get("urls", {}).keys()
    ]
    for drf_name in drf_services:
        drf_env = f"{drf_name.upper()}_AUTHENTICATION_TOKEN"
        authentication_token = os.environ.get(drf_env, None)
        if not authentication_token:
            print(f"{now()} {uuidcode} - {drf_env} not defined. Skip {drf_name}")
            continue
        services_url = (
            custom_conf.get("drf-services", {})
            .get(drf_name, {})
            .get("urls", {})
            .get("services", "")
        )
        drf_headers["Authorization"] = authentication_token
        verify = (
            custom_conf.get("drf-services", {})
            .get(drf_name, {})
            .get("certificate_path", False)
        )
        request_timeout = (
            custom_conf.get("drf-services", {})
            .get(drf_name, {})
            .get("request_timeout", 20)
        )
        r = requests.get(
            services_url, headers=drf_headers, verify=verify, timeout=request_timeout
        )
        services_to_delete = [
            x["servername"]
            for x in r.json()
            if started_n_minutes_ago(grace_period, x["start_date"])
            and x["servername"] not in jhub_server
        ]
        if not services_to_delete:
            print(f"{now()} {uuidcode} - Nothing to cleanup for {drf_name}")
            continue
        for service in services_to_delete:
            service_url = f"{services_url}{service}/"
            print(f"{now()} {uuidcode} - Delete to {service_url} ... ")
            r = requests.delete(
                service_url, headers=drf_headers, verify=verify, timeout=request_timeout
            )
            print(
                f"{now()} {uuidcode} - Delete to {service_url} ... done ({r.status_code})"
            )


if __name__ == "__main__":
    sleep_time = int(os.environ.get("SLEEP", 60))
    db = os.environ.get("SQL_DATABASE", "/home/jupyterhub/jupyterhub.sqlite")
    grace_period = int(os.environ.get("START_DATE_GRACE_PERIOD_IN_MIN", 5))
    while True:
        if os.path.exists(db):
            break
        print(f"{now()} {uuidcode} - Wait for {db}")
        time.sleep(5)
    while True:
        print(f"{now()} {uuidcode} - Cleanup falsely running services ...")
        with open(custom_conf_file, "r") as f:
            custom_conf = json.load(f)
        jhub_server = get_jhub_server(db)
        cleanup_drf_services(jhub_server, custom_conf, grace_period)
        print(f"{now()} {uuidcode} - Cleanup falsely running services ... done")
        time.sleep(sleep_time)
