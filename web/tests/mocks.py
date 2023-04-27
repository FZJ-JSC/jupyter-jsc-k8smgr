services_base = "web/tests/files/services"
services_descriptions = "web/tests/files/services_descriptions"
userhomes_base = "web/tests/files/userhomes"
userhomes_skel = "web/tests/files/userhomes_skel"

import datetime
from dateutil.tz import tzutc


def config_mock():
    return {
        "services": {
            "base": services_base,
            "headers_key_servername": "SERVERNAME",
            "headers_key_access_token": "access-token",
            "descriptions": services_descriptions,
            "descriptions_ignore_files": [".*.swp"],
            "yaml_filename": "service.yaml",
            "max_start_attempts": 3,
            "max_stop_attempts": 3,
            "restart_count_max": 3,
            "replace": {
                "stage": {
                    "stage1": {"stage_specific": "stage1"},
                    "stage2": {"stage_specific": "stage2"},
                },
                "credential": {"authorized": {"credential_stuff": "auth"}},
                "indicators": ["<", ">"],
                "drfid_keyword": "servername",
                "uniqueuserid_keyword": "unique_user_id",
                "secretname_keyword": "secret_name",
                "namespace_keyword": "namespace",
            },
            "skip": {
                "stage": ["stage1", "stage2"],
                "credential": ["authorized", "authorized2"],
            },
        },
        "userhomes": {
            "base": userhomes_base,
            "skel": userhomes_skel,
            "skel_ignore_files": [".*.swp"],
        },
        "tunnel": {},
        "error_messages": {"services.utils.common.start_service_2": "Custom error"},
    }


def config_mock_services_mapping():
    return {
        "services": {
            "base": services_base,
            "headers_key_servername": "SERVERNAME",
            "headers_key_access_token": "access-token",
            "descriptions": services_descriptions,
            "descriptions_ignore_files": [".*.swp"],
            "yaml_filename": "service.yaml",
            "max_start_attempts": 3,
            "max_stop_attempts": 3,
            "restart_count_max": 3,
            "replace": {
                "indicators": ["<", ">"],
                "drfid_keyword": "servername",
                "uniqueuserid_keyword": "unique_user_id",
                "secretname_keyword": "secret_name",
                "namespace_keyword": "namespace",
            },
            "skip": {"stage": ["stage1", "stage2"], "credential": []},
            "credential_mapping": {"authorized": "mapped"},
        },
        "userhomes": {
            "base": userhomes_base,
            "skel": userhomes_skel,
            "skel_ignore_files": [".*.swp"],
        },
        "tunnel": {},
        "error_messages": {"services.utils.common.start_service_2": "Custom error"},
    }


def config_mock_userhome_mapping():
    return {
        "services": {
            "base": services_base,
            "headers_key_servername": "SERVERNAME",
            "headers_key_access_token": "access-token",
            "descriptions": services_descriptions,
            "descriptions_ignore_files": [".*.swp"],
            "yaml_filename": "service.yaml",
            "max_start_attempts": 3,
            "max_stop_attempts": 3,
            "restart_count_max": 3,
            "replace": {
                "indicators": ["<", ">"],
                "drfid_keyword": "servername",
                "uniqueuserid_keyword": "unique_user_id",
                "secretname_keyword": "secret_name",
                "namespace_keyword": "namespace",
            },
        },
        "userhomes": {
            "credential_mapping": {"authorized": "mapped"},
            "service_suffix": {"JupyterLab/JupyterLab": "_suffix"},
            "base": userhomes_base,
            "skel": userhomes_skel,
            "skel_ignore_files": [".*.swp"],
        },
        "tunnel": {},
        "error_messages": {"services.utils.common.start_service_2": "Custom error"},
    }


def mocked_popen_init(*args, **kwargs):
    return PopenMocked(*args, **kwargs)


def mocked_popen_init_check_fail(*args, **kwargs):
    return PopenMockedCheckFail(*args, **kwargs)


def mocked_popen_init_cancel_fail(*args, **kwargs):
    return PopenMockedCancelFail(*args, **kwargs)


def mocked_popen_init_forward_fail(*args, **kwargs):
    return PopenMockedForwardFail(*args, **kwargs)


def mocked_popen_init_all_fail(*args, **kwargs):
    return PopenMockedAllFail(*args, **kwargs)


class PopenMocked:
    cmd = ""

    def __init__(self, cmd, *args, **kwargs):
        self.cmd = cmd

    def __enter__(self, *args, **kwargs):
        return self

    def __exit__(self, *args, **kwargs):
        pass

    def communicate(self):
        return ("stdout".encode("utf-8"), "stderr".encode("utf-8"))

    @property
    def returncode(self):
        return 0


class PopenMockedCheckFail(PopenMocked):
    @property
    def returncode(self):
        if self.cmd[5:7] == ["-O", "check"]:
            return 255
        elif self.cmd[5] == "-v" and self.cmd[6:8] == ["-O", "check"]:
            return 255
        else:
            return 0


class PopenMockedCancelFail(PopenMocked):
    @property
    def returncode(self):
        if self.cmd[5:7] == ["-O", "cancel"]:
            return 255
        elif self.cmd[5] == "-v" and self.cmd[6:8] == ["-O", "cancel"]:
            return 255
        else:
            return 0


class PopenMockedForwardFail(PopenMocked):
    @property
    def returncode(self):
        if self.cmd[5:7] == ["-O", "forward"]:
            return 255
        elif self.cmd[5] == "-v" and self.cmd[6:8] == ["-O", "forward"]:
            return 255
        else:
            return 0


class PopenMockedAllFail(PopenMocked):
    @property
    def returncode(self):
        return 255


class MockResponse:
    _json = {}

    def __init__(self, status_code, json):
        self.status_code = status_code
        self._json = json

    def json(self):
        return self._json

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f"Unexpected Status Code: {self.status_code}")


def mocked_exception(*args, **kwargs):
    raise Exception("Exception")


def mocked_requests_post_running(*args, **kwargs):
    return MockResponse(200, {"running": True})


## Kubernetes mocks

# from kubernetes import client


class k8s_V1Secret:
    api_version = ""
    data = {}
    kind = ""
    metadata = {}
    type = ""


class k8s_pods:
    d = {}

    def __init__(self, d):
        self.d = d

    def to_dict(self):
        return self.d


class k8s_apiclient:
    def __init__(self, *args, **kwargs):
        pass


class k8s_client:
    def __init__(self, *args, **kwargs):
        pass

    # Examples for different states of Pods
    #
    # Complete:
    # {
    #     "container_id": "docker://...",
    #     "image": "...",
    #     "image_id": "docker-pullable://rancher/....@....",
    #     "last_state": {
    #         "running": null,
    #         "terminated": null,
    #         "waiting": null
    #     },
    #     "name": "container_name",
    #     "ready": false,
    #     "restart_count": 0,
    #     "started": false,
    #     "state": {
    #         "running": null,
    #         "terminated": {
    #             "container_id": "docker://...",
    #             "exit_code": 0,
    #             "finished_at": "datetime.datetime(2021, 12, 15, 10, 11, 12, tzinfo=tzutc())",
    #             "message": null,
    #             "reason": "Completed",
    #             "signal": null,
    #             "started_at": "datetime.datetime(2021, 12, 15, 10, 11, 11, tzinfo=tzutc())"
    #         },
    #         "waiting": null
    #     }
    # }

    def list_namespaced_pod(self, namespace, **kwargs):
        d = {
            "items": [
                {
                    "status": {
                        "container_statuses": [
                            {
                                "state": {
                                    "running": {
                                        "started_at": datetime.datetime(
                                            2022, 2, 10, 16, 19, 33, tzinfo=tzutc()
                                        )
                                    }
                                },
                                "restart_count": 0,
                            }
                        ]
                    }
                }
            ]
        }
        return k8s_pods(d)

    def create_namespaced_secret(self, namespace, body):
        assert body.__class__.__name__ == "k8s_V1Secret"
        assert body.api_version
        assert body.string_data
        assert body.kind
        assert body.metadata
        assert body.type

    def delete_namespaced_service(self, name, namespace):
        # assert name.startswith("svc-")
        pass

    def create_namespaced_service(self, body, namespace):
        assert body.get("apiVersion") == "v1"
        assert body.get("kind") == "Service"

    def delete_namespaced_config_map(self, name, namespace):
        assert name.startswith("cm-")

    def delete_namespaced_pod(self, name, namespace):
        assert name.startswith("pod-")

    def delete_namespaced_secret(self, name, namespace):
        assert name.startswith("secret-")

    def delete_namespaced_service_account(self, name, namespace):
        assert name.startswith("svcacc-")


class k8s_client_appsv1_api:
    def __init__(self, *args, **kwargs):
        pass

    def delete_namespaced_deployment(self, name, namespace):
        assert name.startswith("deployment-")


def k8s_client_CoreV1Api(*args, **kwargs):
    return k8s_client()


def k8s_ApiClient(*args, **kwargs):
    return k8s_apiclient()


def k8s_client_AppsV1Api(k8s_client):
    assert k8s_client.__class__.__name__ == "k8s_client"
    return k8s_client_appsv1_api()


# from kubernetes import config
def k8s_config_load_incluster_config():
    pass


# from kubernetes import utils as k8s_utils
def k8s_utils_create_from_yaml(k8s_client, yaml_file, namespace):
    assert k8s_client.__class__.__name__ == "k8s_apiclient"
    assert yaml_file
    assert namespace
