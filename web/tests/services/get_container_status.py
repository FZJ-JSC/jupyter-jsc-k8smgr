import sys

app_label = sys.argv[1]
namespace = sys.argv[2]
if len(sys.argv) > 3:
    output = sys.argv[3]
else:
    output = None

from kubernetes import client
from kubernetes import config
import os

kube_config = os.environ.get("KUBECONFIG", None)
assert kube_config
config.load_kube_config(kube_config)
k8s_client = client.CoreV1Api()

pods = k8s_client.list_namespaced_pod(
    namespace=namespace, label_selector=f"app.kubernetes.io/name={app_label}"
).to_dict()
ret = {}
import json

for pod in pods["items"]:
    container_statuses = pod["status"]["container_statuses"]
    if container_statuses:
        ret[pod["metadata"]["name"]] = {}
        for container_status in container_statuses:
            ret[pod["metadata"]["name"]][container_status["name"]] = container_status

if output:
    with open(output, "w") as f:
        json.dump(ret, f, sort_keys=True, indent=4, default=str)
else:
    output_s = json.dumps(ret, sort_keys=True, indent=4, default=str)
    print(output_s)
