import asyncio
import html
import json
import os

from custom_utils.backend_services import BackendException
from custom_utils.backend_services import drf_request
from custom_utils.backend_services import drf_request_properties
from custom_utils.options_form import get_options_form
from custom_utils.options_form import get_options_from_form
from jupyterhub.spawner import Spawner
from jupyterhub.utils import maybe_future
from jupyterhub.utils import url_path_join
from tornado.httpclient import HTTPRequest
from traitlets import Unicode


class BackendSpawner(Spawner):
    events = []
    cancel_event_yielded = False
    yield_wait_seconds = 1
    _start_future = None

    def status_update_url(self, server_name=""):
        """API path for status update endpoint for a server with a given name"""
        url_parts = ["users", "progress", "update", self.user.escaped_name]
        if server_name:
            url_parts.append(server_name)
        return url_path_join(*url_parts)

    @property
    def _status_update_url(self):
        return self.status_update_url(self.name)

    def get_env(self):
        env = super().get_env()
        env["JUPYTERHUB_STATUS_URL"] = self._status_update_url
        env["JUPYTERHUB_USER_ID"] = self.user.orm_user.id
        return env

    def get_svc_name(self, id):
        k8s_tunnel_deployment_name = os.environ.get(
            "TUNNEL_DEPLOYMENT_NAME", "tunneling"
        )[0:30]
        k8s_tunnel_deployment_namespace = os.environ.get("TUNNEL_DEPLOYMENT_NAMESPACE")
        svc_name = f"{k8s_tunnel_deployment_name}-{id}"[0:63]
        return f"{svc_name}.{k8s_tunnel_deployment_namespace}.svc"

    def _get_req_prop(self, auth_state, uuidcode=""):
        custom_config = self.user.authenticator.custom_config
        drf_service = (
            custom_config.get("systems", {})
            .get(self.user_options["system"], {})
            .get("drf-service", None)
        )
        send_access_token = (
            custom_config.get("drf-services", {})
            .get(drf_service, {})
            .get("send_access_token", False)
        )
        access_token = auth_state["access_token"] if send_access_token else None
        req_prop = drf_request_properties(
            drf_service, custom_config, self.log, access_token, uuidcode
        )
        return req_prop

    async def _start(self):
        self.port = 8080

        auth_state = await self.user.get_auth_state()

        def map_user_options():
            config = self.user.authenticator.custom_config
            ret = {}
            for key, value in self.user_options.items():
                ret[config.get("map_user_options").get(key, key)] = value
            return ret

        env = self.get_env()
        popen_kwargs = {
            "auth_state": auth_state,
            "env": env,
            "user_options": map_user_options(),
        }

        req_prop = self._get_req_prop(auth_state, self.name)
        service_url = req_prop.get("urls", {}).get("services", "None")
        req = HTTPRequest(
            service_url,
            method="POST",
            headers=req_prop["headers"],
            body=json.dumps(popen_kwargs),
            request_timeout=req_prop["request_timeout"],
            validate_cert=req_prop["validate_cert"],
            ca_certs=req_prop["ca_certs"],
        )
        # Todo:
        # Test behaviour if start.sh is not present
        # Run job with /bin/bash start2.sh , will never be there. But it should try at least 3 times to start
        await drf_request(
            req,
            self.log,
            self.user.authenticator.fetch,
            "start",
            self.user.name,
            self._log_name,
            parse_json=True,
            raise_exception=True,
        )
        svc_name = self.get_svc_name(self.name)
        self.log.debug(
            f"Expect JupyterLab at {svc_name}:{self.port}",
            extra={"uuidcode": self.name},
        )
        return (svc_name, self.port)

    async def start(self):
        self.events = []
        self.cancel_event_yielded = False
        return await self._start()

    async def poll(self):
        auth_state = await self.user.get_auth_state()

        req_prop = self._get_req_prop(auth_state)
        service_url = req_prop.get("urls", {}).get("services", "None")

        req = HTTPRequest(
            f"{service_url}{self.name}/",
            method="GET",
            headers=req_prop["headers"],
            request_timeout=req_prop["request_timeout"],
            validate_cert=req_prop["validate_cert"],
            ca_certs=req_prop["ca_certs"],
        )

        try:
            resp_json = await drf_request(
                req,
                self.log,
                self.user.authenticator.fetch,
                "poll",
                self.user.name,
                self._log_name,
                parse_json=True,
                raise_exception=True,
            )
        except:
            return None
        if resp_json and not resp_json.get("running", True):
            return 0
        return None

    def stop(self):
        return asyncio.ensure_future(self._stop())

    async def _stop(self):
        auth_state = await self.user.get_auth_state()

        req_prop = self._get_req_prop(auth_state)
        service_url = req_prop.get("urls", {}).get("services", "None")

        req = HTTPRequest(
            f"{service_url}{self.name}/",
            method="DELETE",
            headers=req_prop["headers"],
            request_timeout=req_prop["request_timeout"],
            validate_cert=req_prop["validate_cert"],
            ca_certs=req_prop["ca_certs"],
        )
        await drf_request(
            req,
            self.log,
            self.user.authenticator.fetch,
            "stop",
            self.user.name,
            self._log_name,
            parse_json=True,
            raise_exception=False,
        )

        custom_config = self.user.authenticator.custom_config
        tunnel_req_prop = drf_request_properties(
            "tunnel", custom_config, self.log, {}, req.headers["uuidcode"]
        )

        tunnel_service_url = tunnel_req_prop.get("urls", {}).get("services", "None")
        tunnel_req = HTTPRequest(
            f"{tunnel_service_url}{self.name}/",
            method="DELETE",
            headers=tunnel_req_prop["headers"],
            request_timeout=tunnel_req_prop["request_timeout"],
            validate_cert=tunnel_req_prop["validate_cert"],
            ca_certs=tunnel_req_prop["ca_certs"],
        )
        await drf_request(
            tunnel_req,
            self.log,
            self.user.authenticator.fetch,
            "removetunnel",
            self.user.name,
            f"{self.user.name}::removetunnel",
            parse_json=True,
            raise_exception=False,
        )

    async def progress(self):
        spawn_future = self._spawn_future
        next_event = 0

        break_while_loop = False
        while True:
            # Ensure we always capture events following the start_future
            # signal has fired.
            if spawn_future.done():
                break_while_loop = True
            events = self.events

            len_events = len(events)
            if next_event < len_events:
                for i in range(next_event, len_events):
                    event = events[i]
                    yield event
                    if event["failed"] == True:
                        self.cancel_event_yielded = True
                        break_while_loop = True
                next_event = len_events

            if break_while_loop:
                break
            await asyncio.sleep(self.yield_wait_seconds)

    async def cancel_future(self, future):
        if type(future) is asyncio.Task:
            if future._state in ["PENDING"]:
                try:
                    future.cancel()
                    await maybe_future(future)
                except asyncio.CancelledError:
                    pass
                return True
        return False

    async def _cancel(self, failed_event):
        self.events.append(failed_event)
        for i in range(0, 2):
            if self.cancel_event_yielded:
                break
            else:
                await asyncio.sleep(self.yield_wait_seconds)
        if self._start_future:
            await self.cancel_future(self._start_future)
        cancelled = await self.cancel_future(self._spawn_future)
        if not cancelled:
            await self.user.stop(self.name)
        self.server = None

    async def options_form(self, spawner):
        query_options = {}
        for key, byte_list in spawner.handler.request.query_arguments.items():
            query_options[key] = [bs.decode("utf8") for bs in byte_list]
        service = query_options.get("service", "JupyterLab")
        if type(service) == list:
            service = service[0]
        service_type = service.split("/")[0]

        services = self.user.authenticator.custom_config.get("services")
        if service_type in services.keys():
            return await get_options_form(
                spawner, service, services[service_type].get("options", {})
            )
        raise NotImplementedError(f"Service type {service_type} from {service} unknown")

    async def options_from_form(self, formdata):
        custom_config = self.user.authenticator.custom_config
        service = formdata.get("service", [""])[0]
        service_type = service.split("/")[0]
        if service_type in custom_config.get("services").keys():
            return await get_options_from_form(formdata, custom_config)
        raise NotImplementedError(f"Service type {service_type} from {service} unknown")
