import datetime
import json
import os
import sqlite3 as sql
import time
import uuid

import requests

custom_conf_file = os.environ.get(
    "CUSTOM_CONFIG_PATH", "/home/jupyterhub/jupyterhub_custom_config.json"
)
with open(custom_conf_file, "r") as f:
    custom_conf = json.load(f)

uuidcode = uuid.uuid4().hex
drf_headers = {
    "Content-Type": "application/json",
    "Accept": "application/json",
    "uuidcode": uuidcode,
}


def now():
    return datetime.datetime.now().strftime("%Y_%m_%d %H:%M:%S.%f")[:-3]


def get_jhub_server():
    db = os.environ.get("SQL_DATABASE", "/home/jupyterhub/jupyterhub.sqlite")
    connection = sql.connect(db)
    query = "SELECT spawners.name FROM servers INNER JOIN spawners ON spawners.server_id = servers.id"
    cur = connection.cursor()
    # Execute the query and then fetch the results
    cur.execute(query)
    output = cur.fetchall()
    return output


def cleanup_drf_services(jhub_server):
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
            x["servername"] for x in r.json() if x["servername"] not in jhub_server
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
    while True:
        print(f"{now()} {uuidcode} - Cleanup falsely running services ...")
        jhub_server_tuple = get_jhub_server()
        jhub_server = [x[0] for x in jhub_server_tuple]
        cleanup_drf_services(jhub_server)
        print(f"{now()} {uuidcode} - Cleanup falsely running services ... done")
        time.sleep(sleep_time)
