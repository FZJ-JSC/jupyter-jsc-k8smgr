import asyncio
import json
import os
import re

from async_generator import aclosing
from custom_utils.backend_services import BackendException
from custom_utils.backend_services import drf_request
from custom_utils.backend_services import drf_request_properties
from custom_utils.options_form import get_options_form
from custom_utils.options_form import get_options_from_form
from datetime import datetime
from jupyterhub.spawner import Spawner
from jupyterhub.utils import maybe_future
from jupyterhub.utils import url_path_join
from tornado.httpclient import HTTPClientError
from tornado.httpclient import HTTPRequest


class BackendSpawner(Spawner):
    _cancel_pending = False
    _cancel_event_yielded = False
    _yielded_events = []
    svc_name = ""

    current_events = []
    events = {}
    yield_wait_seconds = 1

    def get_state(self):
        """get the current state"""
        state = super().get_state()
        if self.svc_name:
            state["svc_name"] = self.svc_name
        if self.events:
            self.events["current"] = self.current_events
            # Clear logs older than 24h
            for key, value in self.events.items():
                stime = self._get_event_time(value[0])
                dtime = datetime.strptime(stime, "%Y_%m_%d %H:%M:%S")
                now = datetime.now()
                delta = now - dtime
                if delta.days:
                    del self.events[key]
            state["events"] = self.events
        return state

    def load_state(self, state):
        """load state from the database"""
        super().load_state(state)
        if "events" in state:
            self.events = state["events"]
        if "svc_name" in state:
            self.svc_name = state["svc_name"]

    def clear_state(self):
        """clear any state (called after shutdown)"""
        self.svc_name = ""
        super().clear_state()

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

    def get_svc_name(self, resp_json):
        custom_config = self.user.authenticator.custom_config
        drf_service = (
            custom_config.get("systems", {})
            .get(self.user_options["system"], {})
            .get("drf-service", None)
        )
        svc_name = f"{drf_service}-{resp_json['id']}"[0:63]
        return f"{svc_name}"

    def get_svc_name_suffix(self):
        k8s_tunnel_deployment_namespace = os.environ.get("TUNNEL_DEPLOYMENT_NAMESPACE")
        return f".{k8s_tunnel_deployment_namespace}.svc"

    def _get_req_prop(self, auth_state):
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
            drf_service, custom_config, self.log, self.name, access_token
        )
        return req_prop

    def _get_event_time(self, event):
        # Regex for date time
        pattern = re.compile(r"([0-9]+(_[0-9]+)+).*[0-9]{2}:[0-9]{2}:[0-9]{2}(\\.[0-9]{1,3})?")
        message = event["html_message"]
        match = re.search(pattern, message)
        return match.group()

    async def start(self):
        # Save current events with start event time
        if self.current_events != []:
            start_event = self.current_events[0]
            start_event_time = self._get_event_time(start_event)
            self.events[start_event_time] = self.current_events
        # Reset current events only
        self.current_events = []
        self.events["current"] = self.current_events

        self._cancel_pending = False
        self._cancel_event_yielded = False
        return await self._start()

    async def _start(self):
        def map_user_options():
            config = self.user.authenticator.custom_config
            ret = {}
            for key, value in self.user_options.items():
                ret[config.get("map_user_options").get(key, key)] = value
            return ret

        now = datetime.now().strftime("%Y_%m_%d %H:%M:%S.%f")[:-3]
        user_options = map_user_options()
        start_event = {
            "failed": False,
            "progress": 10,
            "html_message": f"<details><summary>{now}: Start service</summary>{user_options}</details>",
        }
        self.ready_event[
            "html_message"
        ] = f"<details><summary><now>: Service {user_options['name']} started on {user_options['system']}.</summary>You will be redirected to <a href=\"<url>\"><url></a></details>"
        self.current_events = [start_event]

        self.port = 8080

        auth_state = await self.user.get_auth_state()

        env = self.get_env()
        popen_kwargs = {
            "auth_state": auth_state,
            "env": env,
            "user_options": user_options,
        }

        req_prop = self._get_req_prop(auth_state)
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
        try:
            resp_json = await drf_request(
                req,
                self.log,
                self.user.authenticator.fetch,
                "start",
                self.user.name,
                self._log_name,
                parse_json=True,
                raise_exception=True,
            )
        except BackendException as e:
            failed_event = {
                "progress": 100,
                "failed": True,
                "html_message": e.jupyterhub_html_message,
            }
            self.current_events.append(failed_event)
            try:
                self.stop()
            except:
                pass
            raise e

        self.svc_name = self.get_svc_name(resp_json)
        svc_name_suffix = self.get_svc_name_suffix()
        self.log.debug(
            f"Expect JupyterLab at {self.svc_name}{svc_name_suffix}:{self.port}",
            extra={"uuidcode": self.name},
        )
        now = datetime.now().strftime("%Y_%m_%d %H:%M:%S.%f")[:-3]
        submitted_event = {
            "failed": False,
            "progress": 30,
            "html_message": f"<details><summary>{now}: Request submitted to Jupyter-JSC backend</summary></details>",
        }
        self.current_events.append(submitted_event)
        return (f"{self.svc_name}{svc_name_suffix}", self.port)

    async def poll(self):
        if self._cancel_pending:
            # avoid loop with cancel
            return 0

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
        except HTTPClientError as e:
            if e.code == 404:
                resp_json = {"running": False}
            else:
                self.log.warning("Unexpected error", exc_info=True)
                return None
        except Exception:
            return None
        if not resp_json.get("running", True):
            if self._spawn_pending:
                # During the spawn progress we've received that it's already stopped.
                # We want to show the error message to the user
                now = datetime.now().strftime("%Y_%m_%d %H:%M:%S.%f")[:-3]
                summary = resp_json.get("details", {}).get("error", "Start failed.")
                details = resp_json.get("details", {}).get(
                    "detailed_error", "No details available."
                )
                event = {
                    "failed": True,
                    "progress": 100,
                    "html_message": f"<details><summary>{now}: {summary}</summary>{details}</details>",
                }
                await self.cancel(event)
                return 0
            else:
                # It's not running anymore. Call stop to delete all resources
                await self.stop()
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
            "tunnel", custom_config, self.log, self.name
        )

        tunnel_service_url = tunnel_req_prop.get("urls", {}).get("tunnel", "None")
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

    async def _generate_progress(self):
        """Private wrapper of progress generator

        This method is always an async generator and will always yield at least one event.
        """
        if not self._spawn_pending:
            self.log.warning(
                "Spawn not pending, can't generate progress for %s", self._log_name
            )
            return

        async with aclosing(self.progress()) as progress:
            async for event in progress:
                yield event

    async def progress(self):
        spawn_future = self._spawn_future
        next_event = 0

        break_while_loop = False
        while True:
            # Ensure we always capture events following the start_future
            # signal has fired.
            if spawn_future.done():
                break_while_loop = True

            len_events = len(self.current_events)
            if next_event < len_events:
                for i in range(next_event, len_events):
                    yield self.current_events[i]
                    if self.current_events[i].get("failed", False) == True:
                        self._cancel_event_yielded = True
                        break_while_loop = True
                next_event = len_events

            if break_while_loop:
                break
            await asyncio.sleep(self.yield_wait_seconds)

    async def _cancel_future(self, future):
        if type(future) is asyncio.Task:
            if future._state in ["PENDING"]:
                try:
                    future.cancel()
                    await maybe_future(future)
                except asyncio.CancelledError:
                    pass
                return True
        return False

    async def cancel(self, event):
        self.log.info("Cancel Start")
        self._cancel_pending = True
        self.current_events.append(event)

        # Let generate_progress catch this event.
        # This will show the new event at the control panel site
        for _ in range(0, 2):
            if self._cancel_event_yielded:
                break
            else:
                await asyncio.sleep(self.yield_wait_seconds)
        if not self._cancel_event_yielded:
            self.log.warning("Cancel event will not be displayed at control panel.")

        await self.stop()

        try:
            await self.user.stop(self.name)
        except asyncio.CancelledError:
            pass
        await self._cancel_future(self._spawn_future)

        self._cancel_pending = False
        self.log.info("Cancel Done")

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
