# K8s Manager
This software can be used to start webservices in combination with [JupyterHub](https://github.com/jupyterhub/jupyterhub) and [JupyterHub-BackendSpawner](https://github.com/kreuzert/jupyterhub-backendspawner).
You can find a configuration, which is used by [Jupyter-JSC](https://jupyter-jsc.fz-juelich.de), [here](will be added shortly).

## REST API
### Services
This endpoint will be used to start/poll/stop user services.  
  
#### POST  
Path: `/api/services/`  
Headers Required: 
 - Authentication (Credential of connected JupyterHub. Token or base64 encrypted username:password)
 - uuidcode: ID/Name of the service   
    
Body required:
 - start_id: 8 digit id, different for each start attempt
 - user_options: {}
 - user_options.service: Defines which service will be started
 - env: {}
 - env.JUPYTERHUB_STATUS_URL
 - env.JUPYTERHUB_API_TOKEN
 - env.JUPYTERHUB_USER_ID

#### GET / DELETE
Path: `/api/services/<servername>/`  
Headers Required: 
 - Authentication (Credential of connected JupyterHub. Token or base64 encrypted username:password)
 - uuidcode: unique ID for this request. Should be equal to servername

### Logs
#### Handlers
Path: `/api/logs/handler/[stream|file|smtp|syslog/]`  
Allows you to edit the logging handlers without restarting the service. Example configuration:  
```
{
    "stream": {
        "formatter": "simple",
        "level": 10,
        "stream": "ext://sys.stdout"
    },
    "file": {
        "formatter": "simple",
        "level": 20,
        "filename": "tests/receiver.log",
        "when": "midnight",
        "backupCount": 7
    },
    "smtp": {
        "formatter": "simple",
        "level": 20,
        "mailhost": "",
        "fromaddr": "",
        "toaddrs": [],
        "subject": ""
    },
    "syslog": {
        "formatter": "json",
        "level": 20,
        "address": ["127.0.0.1", 514],
        "socktype": "ext://socket.SOCK_DGRAM"
    }
}
```

#### LogTest
Path: `/api/logs/logtest/`  
Will trigger a log message on each LogLevel.

### UserJobs
Path: `/api/userjobs/`  
This endpoint allows users, who have started a service via K8sMgr, to create a slurm job on connected HPC systems. It also allows the user to connect to already running slurm jobs. If you're interested in this, feel free to contact the authors of this repository. There is currently no documentation available, because this is a very special interest topic.  

## Configuration
You can define which services will be started when accessing the K8s Manager REST API.

### Config.json

In `config.json` you can customize the general behavior and pathes.

| Tag | Type | Default | Description |
| ------ | ------ | ------ | ------ |
| services | Dict | {} | Base configuration for supported services |
| services.base | String | /tmp/services/services | K8sMgr will store the service descriptions for each started service here |
| services.descriptions | String | /tmp/services/descriptions | this is the folder where the service descriptions / definitions are stored. Subdirs: .../services_descriptions/<jhub_credential>/<service_type>/<service_option>/service.yaml | 
| services.yaml_filename | String | service.yaml | you can change the name for the service.yaml file |
| services.deployment_main_name_prefix | String | depl- | will be added to each deployment (each deployment must begin with a character) | 
| services.container_main_name | String | main | This container in the users pod will be used to check the status of the JupyterLab |
| services.input_dir | String | input | name of the directory in .../services_descriptions/<jhub_credential>/<service_type>/<service_option>/ to store files. Will be zipped to .tar.gz file, which you can unzip in start progress. |
| services.replace | Dict | {} | replacements in service.yaml template file |
| services.replace.input_keyword | String | input | input directory is zipped to tar.gz file and then base64 encoded. You can define the keyword in service.yaml |
| services.replace.indicators | List | ["<",">"] |indicators to look for replaces. e.g. default: <input> can be changed to ?!!?mYinPut!??! with indicators: ["?!!?", "!??!"] and input_keyword: "mYinPut" |
| services.replace.drfid_keyword | String | id | id is the unique name of the JupyterLab. Read from POST request header ( "uuidcode" ). Or created during JupyterLab creation in k8smgr. |
| services.replace.uniqueuserid_keyword | String | unique_user_id | jhub credential and user id combined with `_` :  f"{jhub_credential}_{jhub_user_id}"
| services.replace.userid_keyword | String | user_id | <user_id> will be replaced with the users jupyterhub user.id |
| services.replace.secretname_keyword | String | secret_name | K8sMgr will create a secret for each JupyterLab, containing all environments variables. You have to add it in service.yaml with this keyword. |
| services.replace.secretcertsname_keyword | String | secret_certs_name | If you want to use ssl, your certificates will be stored an extra secret (by k8smgr). You have to add it in volumes, to be able to read the certificates. |
| services.replace.namespace_keyword | String | namespace | Where to create the Kubernetes Resources |
| services.replace.stage | Dict | {} | You can give your K8sMgr an environment variable STAGE. e.g. STAGE="production" for your production cluster and STAGE="staging" for staging cluster. You can now use the same service.yaml template for both clusters. In this section you can replace keywords different values (e.g. each cluster (production/staging) uses a different nfs server). IMPORTANT: "nfs" is not a specific buzzword here, you can use any key. K8sMgr will look for every key you've defined within this dict. |
| services.replace.credential | Dict | {} | Same as services.replace.stage above. Different jupyterhub credential might use different variables. |
| services.replace.stage_credential | Dict | {} | Same as services.replace.stage/credential above. Different jupyterhub credential might use different variables for different stages. |
| services.ssl | Dict | {} | enable certificates and configure their options. |
| services.ssl.enabled | Boolean | False | Activate certificates for services |
| services. | Dict | {} | number of lines you want to return to JupyterHub if something fails (will be shown to the user) |
| services.status_information.pod_events_no | Integer | 3 | see services.services.status_information |
| services.status_information.container_logs_lines | Integer | 5 | see services.status_information |
| userhomes | Dict | {} | where to store persistent data for each user |
| userhomes.base | String | /mnt/userhomes | this is the base directory. K8sMgr will create /mnt/userhomes/<jhub_credential>/<user_id> this directory and you're able to mount it into the users pod. |
| userhomes.skel | String | /mnt/shared-data/git_config/userhome_skel | files in here will be copied to /mnt/userhomes/<jhub_credential>/<user_id> (only when creating the directory for the first time) |
| tunnel | List of Dicts | [] | When you restart K8sMgr, you have to inform all connected JupyterHubs. You'll receive a token for this from the JupyterHub admin. |
| tunnel.-.hostname | String | "" | Hostname of your K8sMgr, as it is defined in the connected JupyterHub |
| tunnel.-.restart_url | String | "" | API Endpoint of the connected JupyterHub to handle a K8sMgr restart | 
| tunnel.-.timeout | Integer | - | Timeout for request to services.tunnel.-.restart_url |
| tunnel.-.certificate_path | String or false | - | If needed, certificate_path of the ca |
| startup | Dict | {} | You can use this feature to create users in the database automatically during startup. Required env variables in this example: JUPYTERHUB_USER_PASS=<password> (<jhub_credential_in_capslock>_USER_PASS=...) |
| startup.create_user | Dict | {} | - |
| startup.create_user._credential\_name_ | List of Strings | - | available groups: "access_to_webservice" : allows you to start/stop Jupyterlabs. "access_to_logging": allows the JupyterHub to update the k8smgr logging configuraiton (You can do it manually at your Django Admin Endpoint) |

### Service Descriptions
In this directory, you can define the service definitions for each JupyterHub, service and service_options. You can find a full example [here](...)

### Userhomes Skeleton
When a user starts a service for the first time, you can define a skeleton directory, which will be used to create the users persistent storage. (comparable with `/etc/skel` in Linux distributions). You can find a full example [here](...)
