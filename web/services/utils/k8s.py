import base64
import copy
import html
import json
import logging
import os
import shutil
import tarfile

import lockfile
from jupyterjsc_k8smgr.settings import LOGGER_NAME
from kubernetes import client
from kubernetes import config
from kubernetes import utils as k8s_utils

import yaml

log = logging.getLogger(LOGGER_NAME)
assert log.__class__.__name__ == "ExtraLoggerClass"


def update_service(drf_id, config, logs_extra):
    filename = config.get("services", {}).get("yaml_filename_update", "update.yaml")
    update_yaml_file = _get_yaml_file_name(drf_id, config, filename=filename)
    _create_service_resource(update_yaml_file, logs_extra)


def start_service(
    servername,
    drf_id,
    config,
    validated_data,
    initial_data,
    custom_headers,
    jhub_credential,
    logs_extra,
):
    _create_user_home(config, validated_data, jhub_credential, logs_extra)
    _create_service_yaml(
        servername,
        drf_id,
        config,
        validated_data,
        initial_data,
        custom_headers,
        jhub_credential,
        logs_extra,
    )


def stop_service(drf_id, config, logs_extra={}):
    _delete_service_yaml(drf_id, config, logs_extra)


def k8s_delete_userjobs_svc(name, logs_extra):
    log.debug("Delete UserJobs svc", extra=logs_extra)
    v1 = _k8s_get_client_core()
    namespace = _k8s_get_namespace()
    v1.delete_namespaced_service(name, namespace)


def k8s_create_userjobs_svc(servername, used_ports, logs_extra):
    log.debug("Create UserJobs svc ...", extra=logs_extra)
    v1 = _k8s_get_client_core()
    namespace = _k8s_get_namespace()
    labels = {"userjobs_servername": servername}
    ports = [
        {"port": int(wanted), "protocol": "TCP", "targetPort": int(used[0])}
        for wanted, used in used_ports.items()
    ]
    k8smgr_name_label = os.environ.get("DEPLOYMENT_NAME", "drf-k8smgr")
    service_manifest = {
        "apiVersion": "v1",
        "kind": "Service",
        "metadata": {
            "labels": labels,
            "name": servername,
            "resourceversion": "v1",
        },
        "spec": {
            "ports": ports,
            "selector": {"name": k8smgr_name_label},
        },
    }
    logs_extra["service_manifest"] = service_manifest
    log.debug("Create UserJobs Manifest ...", extra=logs_extra)
    v1.create_namespaced_service(body=service_manifest, namespace=namespace)
    log.debug("Create UserJobs Manifest ... done", extra=logs_extra)
    del logs_extra["service_manifest"]
    log.info("Create UserJobs svc ... done", extra=logs_extra)


def _get_deployment_main(drf_id, config, min_log, logs_extra):
    service_yaml_file = _get_yaml_file_name(drf_id, config)
    deployment_main_name_prefix = config.get("services", {}).get(
        "deployment_main_name_prefix", "deployment-main-"
    )
    deployment_main_name = f"{deployment_main_name_prefix}{drf_id}"

    # Load configuration of all applied deployments
    with lockfile.LockFile(service_yaml_file):
        with open(service_yaml_file) as f:
            all_services = yaml.safe_load_all(f)
            deployments = [x for x in all_services if x["kind"] == "Deployment"]

    # Look for deployment with name deployment_main_name
    # Status of this deployment will determine the status of the service
    deployment_main_list = [
        x for x in deployments if x["metadata"]["name"] == deployment_main_name
    ]

    if not deployments:
        log.critical(
            f"No deployment configured in {service_yaml_file}", extra=logs_extra
        )
        raise Exception(f"No deployment configured in {service_yaml_file}")
    if len(deployment_main_list) != 1:
        log.critical(
            f"No deployment configured with name {deployment_main_name}",
            extra=logs_extra,
        )
        raise Exception(f"No deployment configured with name {deployment_main_name}")

    deployment_main = deployment_main_list[0]

    if min_log <= 5:
        # deployments may not be serializable, but at trace level we want to log it for debugging
        trace_logs_extra_deployments_dict = json.loads(
            json.dumps(deployment_main, default=str)
        )
        trace_logs_extra = copy.deepcopy(logs_extra)
        trace_logs_extra["deployment_main"] = trace_logs_extra_deployments_dict
        log.trace("Check pod status for deployment", extra=trace_logs_extra)

    return deployment_main


def _get_pod(k8s_client, namespace, deployment_main, min_log, logs_extra):
    # Look for main pod in deployment_main
    name_label = deployment_main["spec"]["selector"]["matchLabels"]["name"]
    pods = k8s_client.list_namespaced_pod(
        namespace=namespace, label_selector=f"name={name_label}"
    ).to_dict()
    pod_list = [x for x in pods.get("items", [])]

    if len(pod_list) != 1:
        log.critical(f"No pod found with name label {name_label}", extra=logs_extra)
        raise Exception(f"No pod found with name label {name_label}")

    pod = pod_list[0]

    if min_log <= 5:
        # pods is not serializable, but at trace level we want to log it for debugging
        trace_logs_extra_pods_dict = json.loads(json.dumps(pod, default=str))
        trace_logs_extra = copy.deepcopy(logs_extra)
        trace_logs_extra["pod"] = trace_logs_extra_pods_dict
        log.trace(
            f"Check pod status - namespace={namespace} label_selector=name={name_label}",
            extra=trace_logs_extra,
        )

    return pod


def _get_container_main(config, pod, min_log, logs_extra):
    container_main_name = config.get("services", {}).get("container_main_name", "main")
    container_main_list = [
        x
        for x in pod["status"]["container_statuses"]
        if x["name"] == container_main_name
    ]

    if len(container_main_list) != 1:
        log.critical(
            f"No container found with name {container_main_name}", extra=logs_extra
        )
        raise Exception(f"No container found with name {container_main_name}")

    container_main = container_main_list[0]

    if min_log <= 5:
        # pods is not serializable, but at trace level we want to log it for debugging
        trace_logs_extra_pods_dict = json.loads(json.dumps(container_main, default=str))
        trace_logs_extra = copy.deepcopy(logs_extra)
        trace_logs_extra["container_main"] = trace_logs_extra_pods_dict
        log.trace(
            f"Check container status with name {container_main_name}",
            extra=trace_logs_extra,
        )

    return container_main


def _get_detailed_error_logs(
    k8s_client, pod_name, namespace, config, min_log, logs_extra
):
    try:
        container_logs_keyword = "<CONTAINER_LOGS>"
        detailed_error_html_logs = (
            config.get("services", {})
            .get("status_information", {})
            .get(
                "detailed_error_html_logs",
                f"<details><summary>&nbsp&nbsp&nbsp&nbspContainer Logs</summary>{container_logs_keyword}</details>",
            )
        )
        if container_logs_keyword not in detailed_error_html_logs:
            return detailed_error_html_logs

        container_main_name = config.get("services", {}).get(
            "container_main_name", "main"
        )
        all_logs = k8s_client.read_namespaced_pod_log(
            name=pod_name, namespace=namespace, container=container_main_name
        )

        if min_log <= 5:
            # pods is not serializable, but at trace level we want to log it for debugging
            trace_logs_extra_pods_dict = json.loads(json.dumps(all_logs, default=str))
            trace_logs_extra = copy.deepcopy(logs_extra)
            trace_logs_extra["all_logs"] = trace_logs_extra_pods_dict
            log.trace(
                f"Check pod logs for {pod_name}",
                extra=trace_logs_extra,
            )
        if not all_logs:
            return detailed_error_html_logs.replace(
                container_logs_keyword, "No logs available"
            )

        container_logs_join = (
            config.get("services", {})
            .get("status_information", {})
            .get("container_logs_join", "<br>")
        )
        container_logs_lines = (
            config.get("services", {})
            .get("status_information", {})
            .get("container_logs_lines", 5)
        )
        container_logs_list_short = all_logs.rstrip().split("\n")[
            -container_logs_lines:
        ]
        container_logs_list_short_escaped = list(
            map(lambda x: html.escape(x), container_logs_list_short)
        )
        container_logs_s = container_logs_join.join(container_logs_list_short_escaped)
        return detailed_error_html_logs.replace(
            container_logs_keyword, container_logs_s
        )
    except:
        log.debug(
            f"Could not receive logs for pod {pod_name}.",
            extra=logs_extra,
            exc_info=True,
        )
        return "No logs available"


def _get_pod_recent_events(
    k8s_client, pod_name, namespace, config, min_log, logs_extra
):
    pod_events = k8s_client.list_namespaced_event(
        namespace=namespace, field_selector=f"involvedObject.name={pod_name}"
    ).to_dict()
    pod_events_items = pod_events["items"]

    if len(pod_events_items) == 0:
        log.critical(f"No pod event found for {pod_name}", extra=logs_extra)
        raise Exception(f"No pod event found for {pod_name}")

    if min_log <= 5:
        # pods is not serializable, but at trace level we want to log it for debugging
        trace_logs_extra_pods_dict = json.loads(
            json.dumps(pod_events_items, default=str)
        )
        trace_logs_extra = copy.deepcopy(logs_extra)
        trace_logs_extra["pod_events_items"] = trace_logs_extra_pods_dict
        log.trace(
            f"Check pod events - namespace={namespace} pod_name={pod_name}",
            extra=trace_logs_extra,
        )

    pod_events_no = (
        config.get("services", {}).get("status_information", {}).get("pod_events_no", 3)
    )

    full_pod_events_short = pod_events_items[-pod_events_no:]
    ret = [
        {
            key: value
            for (key, value) in event.items()
            if key in ["type", "reason", "message"]
        }
        for event in full_pod_events_short
    ]

    return ret


def status_service(drf_id, config, logs_extra={}):
    status = {}
    k8s_client = _k8s_get_client_core()
    namespace = _k8s_get_namespace()
    min_log = min([h.level for h in log.handlers], default=20)
    deployment_main = _get_deployment_main(drf_id, config, min_log, logs_extra)
    pod = _get_pod(k8s_client, namespace, deployment_main, min_log, logs_extra)

    # To define if a service is running, we check various things
    # https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/
    #   - Check the pods state
    #   - Check the main containers state
    #   - Check events
    #   - Get logs

    pod_phase = pod["status"]["phase"]
    if pod_phase not in ["Pending", "Running"]:
        # Succeeded might be strange, since it's normally a positive outcome
        # But we need a running container. Not a finished one.
        log.debug(f"Pod state not as expected ({pod_phase})", extra=logs_extra)
        if pod_phase == "Succeeded":
            pod_phase = "Failed"

        recent_logs = _get_detailed_error_logs(
            k8s_client,
            pod["metadata"]["name"],
            namespace,
            config,
            min_log,
            logs_extra,
        )
        status = {
            "running": False,
            "details": {
                "error": f"Service status is {pod_phase}",
                "detailed_error": recent_logs,
            },
        }
        return status

    # Pod is not finished yet. So let's check the container status
    container_main = _get_container_main(config, pod, min_log, logs_extra)

    if container_main["state"]["terminated"]:
        # Main container was terminated. We don't support restarts. So return False
        recent_logs = _get_detailed_error_logs(
            k8s_client,
            pod["metadata"]["name"],
            namespace,
            config,
            min_log,
            logs_extra,
        )
        log.debug("Container state not as expected (terminated))", extra=logs_extra)
        status = {
            "running": False,
            "details": {
                "error": "Service status is in state terminated",
                "detailed_error": recent_logs,
            },
        }
        return status
    elif container_main["state"]["running"]:
        # Main Container is running or waiting, then everything's fine.
        # Main Container has to ensure, that it's not running fine,
        # if everything else has problems.
        status = {"running": True}
        log.trace("Main Container status is running", extra=logs_extra)
        return status
    else:
        # Container is still in waiting state or in None. Let's check for events.
        # Maybe we find an ongoing problem, then we can send back False
        last_n_events = _get_pod_recent_events(
            k8s_client, pod["metadata"]["name"], namespace, config, min_log, logs_extra
        )
        bad_event_types = config.get("services", {}).get(
            "pod_events_to_fail", ["Warning"]
        )
        last_event_logs_extra = copy.deepcopy(logs_extra)
        last_event_logs_extra["last_event"] = last_n_events
        last_n_event_types = [x["type"] for x in last_n_events if "type" in x]
        if set(bad_event_types) <= set(last_n_event_types):
            recent_logs = _get_detailed_error_logs(
                k8s_client,
                pod["metadata"]["name"],
                namespace,
                config,
                min_log,
                logs_extra,
            )

            pod_events_keyword = "<POD_EVENTS_MESSAGES>"
            detailed_error_html_events = (
                config.get("services", {})
                .get("status_information", {})
                .get(
                    "detailed_error_html_events",
                    f"<details><summary>&nbsp&nbsp&nbsp&nbspKubernetes events</summary>{pod_events_keyword}</details>{recent_logs}",
                )
            )
            pod_events_join = (
                config.get("services", {})
                .get("status_information", {})
                .get("pod_events_join", "<br>")
            )
            pod_events_messages_list = [
                event.get("message", "") for event in last_n_events
            ]
            pod_events_messages_list_escaped = list(
                map(lambda x: html.escape(x), pod_events_messages_list)
            )
            pod_events_messages_s = pod_events_join.join(
                pod_events_messages_list_escaped
            )
            detailed_error = detailed_error_html_events.replace(
                pod_events_keyword, pod_events_messages_s
            )

            status["running"] = False
            status["details"] = {
                "error": "Service cannot start",
                "detailed_error": detailed_error,
            }
            log.debug(
                f"Last Pod event not as expected ({last_n_events[-1]})",
                extra=last_event_logs_extra,
            )
            return status
        else:
            # Looks like it's starting or running
            log.debug("Pod seems to be in a good state.", extra=last_event_logs_extra)

    # No problems noticed
    status = {"running": True}
    return status


def _create_user_home(config, validated_data, jhub_credential, logs_extra):
    from services.models import UserModel

    jhub_user_id = validated_data["jhub_user_id"]
    user_model = (
        UserModel.objects.filter(jhub_credential=jhub_credential)
        .filter(jhub_user_id=jhub_user_id)
        .first()
    )

    if not user_model:
        # Create user in db
        log.debug("Create UserModel", extra=logs_extra)
        UserModel(jhub_credential=jhub_credential, jhub_user_id=jhub_user_id).save()

    userhome_base = (
        config.get("userhomes", {}).get("base", "/tmp/userhomes").rstrip("/")
    )

    # Allow jhub_credential mapping. Multiple credentials may use the same home directories
    jhub_credential_home = (
        config.get("userhomes", {})
        .get("credential_mapping", {})
        .get(jhub_credential, jhub_credential)
    )

    # Allow service specific home directories. Different services may use different home directories
    service = validated_data.get("user_options", {}).get("service", "")
    service_suffix = (
        config.get("userhomes", {}).get("service_suffix", {}).get(service, "")
    )
    user_home_dir = f"{jhub_credential_home}{service_suffix}"

    userhome_skel_base = (
        config.get("userhomes", {}).get("skel", "/etc/skel").rstrip("/")
    )
    userhome_uid = (
        config.get("userhomes", {}).get("uid", 1000)
    )
    userhome_gid = (
        config.get("userhomes", {}).get("gid", 1000)
    )
    userhome_skel = f"{userhome_skel_base}/{jhub_credential_home}{service_suffix}"

    userhome_user_path = f"{userhome_base}/{user_home_dir}/{jhub_user_id}"
    if not os.path.exists(userhome_user_path):
        log.debug(f"Create home directory {userhome_user_path}", extra=logs_extra)
        os.makedirs(userhome_skel, exist_ok=True)
        ignore_files = config.get("userhomes", {}).get("skel_ignore_files", [])
        shutil.copytree(
            src=userhome_skel,
            dst=userhome_user_path,
            ignore=shutil.ignore_patterns(*ignore_files),
        )
        for dirpath, dirnames, filenames in os.walk(userhome_user_path):
            shutil.chown(dirpath, userhome_uid, userhome_gid)
            for filename in filenames:
                shutil.chown(os.path.join(dirpath, filename), userhome_uid, userhome_gid)
    else:
        log.debug(
            f"Home directory {userhome_user_path} already exists.", extra=logs_extra
        )


def _create_service_yaml(
    servername,
    drf_id,
    config,
    validated_data,
    initial_data,
    custom_headers,
    jhub_credential,
    logs_extra,
):
    jhub_user_id = validated_data["jhub_user_id"]
    log.debug("Create Service yaml", extra=logs_extra)

    input_dir = config.get("services", {}).get("input_dir", "input")
    service_yaml_file = _get_yaml_file_name(drf_id, config)
    service_yaml_s = _yaml_get_service_as_string(
        config,
        jhub_credential,
        validated_data,
        service_yaml_file,
        input_dir,
        logs_extra,
    )

    input_string = _create_input_string(service_yaml_file, input_dir)

    service_yaml_s = _yaml_replace(
        drf_id,
        config,
        service_yaml_s,
        jhub_credential,
        jhub_user_id,
        input_string,
        logs_extra,
    )
    with lockfile.LockFile(service_yaml_file):
        with open(service_yaml_file, "w") as f:
            f.write(service_yaml_s)

    _create_secret_resource(
        servername, drf_id, config, initial_data, custom_headers, logs_extra
    )
    if "certs" in initial_data.keys():
        _create_secret_certificate_resource(
            servername, drf_id, config, initial_data, custom_headers, logs_extra
        )
    _create_service_resource(service_yaml_file, logs_extra)

    # We've created service.yaml, no we want to prepare update.yaml, if it exists.
    # This allows us to update the service later during the starting phase (e.g. adding
    # a service)
    filename = config.get("services", {}).get("yaml_filename_update", "update.yaml")
    update_yaml_file = _get_yaml_file_name(drf_id, config, filename=filename)
    if os.path.isfile(update_yaml_file):
        with lockfile.LockFile(update_yaml_file):
            with open(update_yaml_file, "r") as f:
                update_yaml_s = f.read()
        update_yaml_s = _yaml_replace(
            drf_id,
            config,
            update_yaml_s,
            jhub_credential,
            jhub_user_id,
            input_string,
            logs_extra,
        )
        with lockfile.LockFile(update_yaml_file):
            with open(update_yaml_file, "w") as f:
                f.write(update_yaml_s)


def _get_yaml_file_name(drf_id, config, filename=None):
    services_base = (
        config.get("services", {}).get("base", "/tmp/services/services").rstrip("/")
    )
    services_service_path = f"{services_base}/{drf_id}"
    if not filename:
        filename = config.get("services", {}).get("yaml_filename", "service.yaml")
    service_yaml_file = f"{services_service_path}/{filename}"
    return service_yaml_file


def _yaml_get_service_as_string(
    config, jhub_credential, validated_data, service_yaml_file, input_dir, logs_extra
):
    services_skel_base = (
        config.get("services", {})
        .get("descriptions", "/tmp/services/descriptions")
        .rstrip("/")
    )

    # credential mapping: allow multiple accounts to use the same service descriptions
    jhub_credential_to_use = (
        config.get("services", {})
        .get("credential_mapping", {})
        .get(jhub_credential, jhub_credential)
    )

    services_skel = f"{services_skel_base}/{jhub_credential_to_use}/{validated_data['user_options']['service'].rstrip('/')}"
    services_service_path = os.path.dirname(service_yaml_file)

    if not os.path.exists(services_service_path):
        log.debug(
            f"Create service specific directory {services_service_path}",
            extra=logs_extra,
        )
        os.makedirs(services_skel, exist_ok=True)
        ignore_files = config.get("services", {}).get("descriptions_ignore_files", [])
        stage = os.environ.get("STAGE", "").lower()
        if stage:
            stages_to_skip = [
                f"{x}_*"
                for x in config.get("services", {}).get("skip", {}).get("stage", [])
                if x != stage
            ]
            ignore_files.extend(stages_to_skip)

            # Same stage but diffent credential: skip
            stages_credential_to_skip = [
                f"{stage}_{x}_*"
                for x in config.get("services", {})
                .get("skip", {})
                .get("credential", [])
                if x != jhub_credential
            ]
            ignore_files.extend(stages_credential_to_skip)

        credential_to_skip = [
            f"{x}_*"
            for x in config.get("services", {}).get("skip", {}).get("credential", [])
            if x != jhub_credential
        ]
        ignore_files.extend(credential_to_skip)

        shutil.copytree(
            src=services_skel,
            dst=services_service_path,
            ignore=shutil.ignore_patterns(*ignore_files),
        )

        # Rename specific files
        for subdir, dirs, files in os.walk(f"{services_service_path}/{input_dir}"):
            for file in files:
                if file.startswith(f"{stage}_{jhub_credential}_"):
                    newname = file[len(stage) + 1 + len(jhub_credential) + 1 :]
                    shutil.move(f"{subdir}/{file}", f"{subdir}/{newname}")
                elif file.startswith(f"{stage}_"):
                    newname = file[len(stage) + 1 :]
                    shutil.move(f"{subdir}/{file}", f"{subdir}/{newname}")
                elif file.startswith(f"{jhub_credential}_"):
                    newname = file[len(jhub_credential) + 1 :]
                    shutil.move(f"{subdir}/{file}", f"{subdir}/{newname}")
    else:
        log.critical(
            f"Service specific directory {services_service_path} already exists.",
            extra=logs_extra,
        )

    if not os.path.exists(service_yaml_file):
        log.critical(
            f"Configured service yaml file {service_yaml_file} does not exist.",
            extra=logs_extra,
        )
        raise Exception("Couldn't find service yaml file.")
    with lockfile.LockFile(service_yaml_file):
        with open(service_yaml_file, "r") as f:
            service_yaml_s = f.read()
    return service_yaml_s


def _create_input_string(service_yaml_file, input_dir):
    services_service_path = os.path.dirname(service_yaml_file)
    if os.path.exists(f"{services_service_path}/{input_dir}"):
        with tarfile.open(f"{services_service_path}/{input_dir}.tar.gz", "w:gz") as tar:
            tar.add(f"{services_service_path}/{input_dir}", arcname="input")
        with open(f"{services_service_path}/{input_dir}.tar.gz", "rb") as f:
            encoded_input = base64.b64encode(f.read())
        shutil.rmtree(f"{services_service_path}/{input_dir}")
        os.remove(f"{services_service_path}/{input_dir}.tar.gz")
        return encoded_input.decode()
    else:
        return ""


def _yaml_replace(
    drf_id,
    config,
    yaml_s,
    jhub_credential,
    jhub_user_id,
    input_string,
    logs_extra,
):
    unique_user = f"{jhub_credential}_{jhub_user_id}"
    replace_indicators = (
        config.get("services", {}).get("replace", {}).get("indicators", ["<", ">"])
    )
    drf_id_keyword = (
        config.get("services", {}).get("replace", {}).get("drfid_keyword", "id")
    )
    uniqueuserid_keyword = (
        config.get("services", {})
        .get("replace", {})
        .get("uniqueuserid_keyword", "unique_user_id")
    )
    userid_keyword = (
        config.get("services", {}).get("replace", {}).get("userid_keyword", "user_id")
    )
    secretname_keyword = (
        config.get("services", {})
        .get("replace", {})
        .get("secretname_keyword", "secret_name")
    )
    secretcertsname_keyword = (
        config.get("services", {})
        .get("replace", {})
        .get("secretcertsname_keyword", "secret_certs_name")
    )
    namespace_keyword = (
        config.get("services", {})
        .get("replace", {})
        .get("namespace_keyword", "namespace")
    )
    input_keyword = (
        config.get("services", {}).get("replace", {}).get("input_keyword", "input")
    )
    yaml_s = yaml_s.replace(
        f"{replace_indicators[0]}{input_keyword}{replace_indicators[1]}",
        input_string,
    )
    yaml_s = yaml_s.replace(
        f"{replace_indicators[0]}{drf_id_keyword}{replace_indicators[1]}",
        str(drf_id),
    )
    yaml_s = yaml_s.replace(
        f"{replace_indicators[0]}{uniqueuserid_keyword}{replace_indicators[1]}",
        unique_user,
    )
    yaml_s = yaml_s.replace(
        f"{replace_indicators[0]}{userid_keyword}{replace_indicators[1]}",
        str(jhub_user_id),
    )
    yaml_s = yaml_s.replace(
        f"{replace_indicators[0]}{secretname_keyword}{replace_indicators[1]}",
        _k8s_get_secret_name(drf_id),
    )
    yaml_s = yaml_s.replace(
        f"{replace_indicators[0]}{secretcertsname_keyword}{replace_indicators[1]}",
        _k8s_get_secret_certs_name(drf_id),
    )
    yaml_s = yaml_s.replace(
        f"{replace_indicators[0]}{namespace_keyword}{replace_indicators[1]}",
        _k8s_get_namespace(),
    )

    # Replace stage specific keywords, if stage is defined
    stage = os.environ.get("STAGE", "").lower()
    if stage:
        # First replace stage+credential specific
        for key, value in (
            config.get("services", {})
            .get("replace", {})
            .get("stage_credential", {})
            .get(stage, {})
            .get(jhub_credential, {})
            .items()
        ):
            yaml_s = yaml_s.replace(
                f"{replace_indicators[0]}{key}{replace_indicators[1]}",
                value,
            )
        for key, value in (
            config.get("services", {})
            .get("replace", {})
            .get("stage", {})
            .get(stage, {})
            .items()
        ):
            yaml_s = yaml_s.replace(
                f"{replace_indicators[0]}{key}{replace_indicators[1]}",
                value,
            )

    # Replace credential specific keywords
    for key, value in (
        config.get("services", {})
        .get("replace", {})
        .get("credential", {})
        .get(jhub_credential, {})
        .items()
    ):
        yaml_s = yaml_s.replace(
            f"{replace_indicators[0]}{key}{replace_indicators[1]}",
            value,
        )

    return yaml_s


def _k8s_get_client_core():
    config.load_incluster_config()
    return client.CoreV1Api()


def _k8s_get_api_client():
    config.load_incluster_config()
    return client.ApiClient()


def _k8s_get_secret_name(drf_id):
    deployment_name = os.environ.get("DEPLOYMENT_NAME", "k8smgr")
    return f"secret-{drf_id}-{deployment_name}"[0:63]


def _k8s_get_secret_certs_name(drf_id):
    deployment_name = os.environ.get("DEPLOYMENT_NAME", "k8smgr")
    return f"secret-certs-{drf_id}-{deployment_name}"[0:63]


def _k8s_get_namespace():
    return os.environ.get("DEPLOYMENT_NAMESPACE", "default")


def _get_k8s_secret_object(secret_name, data):
    body = client.V1Secret()
    body.api_version = "v1"
    body.string_data = data
    body.kind = "Secret"
    body.metadata = {"name": secret_name}
    body.type = "Opaque"
    return body


def _create_secret_certificate_resource(
    servername, drf_id, config, initial_data, custom_headers, logs_extra
):
    secret_certs_name = _k8s_get_secret_certs_name(drf_id)
    namespace = _k8s_get_namespace()

    log.debug(
        f"Create secret cert resource ({drf_id}) for {servername} ...", extra=logs_extra
    )

    cert_data = {
        "JUPYTERHUB_SSL_KEYFILE_DATA": initial_data["certs"]["keyfile"],
        "JUPYTERHUB_SSL_CERTFILE_DATA": initial_data["certs"]["certfile"],
        "JUPYTERHUB_SSL_CLIENT_CA_DATA": initial_data["certs"]["cafile"],
    }

    # Create resource with cert_data
    k8s_client = _k8s_get_client_core()
    body = _get_k8s_secret_object(secret_certs_name, cert_data)
    k8s_client.create_namespaced_secret(namespace=namespace, body=body)
    log.debug(
        f"Create secret cert resource ({secret_certs_name}) for {servername} ... done"
    )


def _create_secret_resource(
    servername, drf_id, config, initial_data, custom_headers, logs_extra
):
    secret_name = _k8s_get_secret_name(drf_id)
    log.debug(
        f"Create secret resource ({drf_id}) for {servername}...", extra=logs_extra
    )
    k8s_client = _k8s_get_client_core()
    namespace = _k8s_get_namespace()
    data = {key: str(value) for key, value in initial_data.get("env", {}).items()}
    data.update({key: str(value) for key, value in custom_headers.items()})
    for key, value in config.get("services", {}).get("env", {}).items():
        data[key] = str(value)
    for key in config.get("services", {}).get(
        "env_skip", ["LC_ALL", "LANG", "PATH", "PYTHONPATH", "uuidcode"]
    ):
        if key in data.keys():
            del data[key]
    data["SERVERNAME"] = servername
    data["DRF_ID"] = str(drf_id)

    body = _get_k8s_secret_object(secret_name, data)
    k8s_client.create_namespaced_secret(namespace=namespace, body=body)
    log.debug(
        f"Create secret resource ({secret_name}) for {servername}... done",
        extra=logs_extra,
    )


def _create_service_resource(service_yaml_file, logs_extra):
    log.debug("Create service resource ...", extra=logs_extra)
    namespace = _k8s_get_namespace()
    k8s_utils.create_from_yaml(
        k8s_client=_k8s_get_api_client(),
        yaml_file=service_yaml_file,
        namespace=namespace,
    )
    log.debug("Create service resource ... done", extra=logs_extra)


def _delete_service_yaml(drf_id, config, logs_extra):
    service_yaml_file = _get_yaml_file_name(drf_id, config)
    filename = config.get("services", {}).get("yaml_filename_update", "update.yaml")
    update_yaml_file = _get_yaml_file_name(drf_id, config, filename=filename)
    k8s_client = _k8s_get_client_core()
    k8s_api_client = _k8s_get_api_client()
    k8s_app_api = client.AppsV1Api(k8s_api_client)
    k8s_client_funcs = {
        "Service": k8s_client.delete_namespaced_service,
        "Deployment": k8s_app_api.delete_namespaced_deployment,
        "ConfigMap": k8s_client.delete_namespaced_config_map,
        "Pod": k8s_client.delete_namespaced_pod,
        "Secret": k8s_client.delete_namespaced_secret,
    }

    for file in [service_yaml_file, update_yaml_file]:
        if os.path.isfile(file):
            with lockfile.LockFile(file):
                with open(file) as f:
                    all_services = yaml.safe_load_all(f)
                    for service in all_services:
                        try:
                            kind = service["kind"]
                            name = service["metadata"]["name"]
                            namespace = service["metadata"]["namespace"]
                            log.debug(
                                f"Delete {kind} {name} in {namespace}", extra=logs_extra
                            )
                            k8s_client_funcs[kind](name=name, namespace=namespace)
                        except Exception as e:
                            log.critical(
                                "Could not delete resource",
                                exc_info=True,
                                extra=logs_extra,
                            )

    secret_name = _k8s_get_secret_name(drf_id)
    secret_namespace = _k8s_get_namespace()
    try:
        log.debug(f"Delete secret resource ({secret_name})...", extra=logs_extra)
        k8s_client.delete_namespaced_secret(
            name=secret_name, namespace=secret_namespace
        )
        log.debug(f"Delete secret resource ({secret_name})... done", extra=logs_extra)
    except:
        log.critical(
            "Could not delete secret resource", exc_info=True, extra=logs_extra
        )

    if config.get("services", {}).get("ssl", {}).get("enabled", False):
        secret_certs_name = _k8s_get_secret_certs_name(drf_id)
        try:
            log.debug(
                f"Delete secret certs resource ({secret_certs_name})...",
                extra=logs_extra,
            )
            k8s_client.delete_namespaced_secret(
                name=secret_certs_name, namespace=secret_namespace
            )
            log.debug(
                f"Delete secret certs resource ({secret_name})... done",
                extra=logs_extra,
            )
        except:
            log.warning(
                "Could not delete secret certs resource",
                exc_info=True,
                extra=logs_extra,
            )
