# Kubernetes Setup
Minimal files to start K8s Service Manager on Kubernetes. Update `<NAMESPACE>` and `<ID>` in template files before deploying it.

```
$ export NAMESPACE=...
$ export ID=$(uuidgen)
$ sed -e "s/<NAMESPACE>/${NAMESPACE}/g" -e "s/<ID>/${ID}/g" yaml/service_account.yaml.template > yaml/service_account.yaml
$ sed -e "s/<ID>/${ID}/g" yaml/service.yaml.template > yaml/service.yaml
$ kubectl -n ${NAMESPACE} apply -f yaml
$ kubectl -n ${NAMESPACE} port-forward svc/svc-k8smgr-${ID} 8080:8080
$ curl -I http://localhost:8080/api/health/
```

You will find the admin password in the pods logs.
