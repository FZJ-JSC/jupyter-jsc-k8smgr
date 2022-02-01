import asyncio
import html
import json
import uuid
from asyncio.tasks import sleep


from jupyterhub.spawner import Spawner
from jupyterhub.utils import maybe_future, random_port
from jupyterhub.utils import url_path_join
from tornado.httpclient import HTTPClientError
from tornado.httpclient import HTTPRequest
from tornado.httpclient import HTTPResponse
from traitlets import Unicode


class BackendException(Exception):
    error = "Unexpected error."
    error_detail = ""

    def __init__(self, error, error_detail=""):
        self.error = error
        self.error_detail = error_detail
        super().__init__(f"{error} --- {error_detail}")


class BackendSpawner(Spawner):
    events = []
    cancel_event_yielded = False
    yield_wait_seconds = 1
    _start_future = None

    id = Unicode(
        "",
        help="""
        The backend id of the server spawned for current user.
        """,
    )

    backend_services_url = Unicode(
        "",
        help="""
        URL to start/stop jobs via backend.
        """,
        config=True
    )

    backend_services_token = Unicode(
        "",
        help="""
        Used to authenticate against backend to start/stop jobs.
        """,
        config=True
    )

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

    def load_state(self, state):
        """Restore state about spawned server after a hub restart."""
        super(BackendSpawner, self).load_state(state)
        if "id" in state:
            self.id = state["id"]

    def get_state(self):
        """Save state that is needed to restore this spawner instance after a hub restore."""
        state = super(BackendSpawner, self).get_state()
        if self.id:
            state["id"] = self.id
        return state

    def clear_state(self):
        """Clear stored state about this spawner (id)"""
        super(BackendSpawner, self).clear_state()
        self.id = ""

    async def _start(self):
        try:
            await self._start_job()
        except Exception as e:
            self.log.exception("Start failed")
            failed_event = {
                "progress": 100,
                "failed": True,
            }
            if isinstance(e, BackendException):
                failed_event[
                    "html_message"
                ] = '<details><summary>Start failed. {}<span class="caret"></span></summary><p>{}</p></details>'.format(
                    e.error, html.escape(e.error_detail)
                )
            else:
                failed_event[
                    "html_message"
                ] = '<details><summary>Start failed. <span class="caret"></span></summary><p>{}</p></details>'.format(
                    html.escape(str(e))
                )
            await self._cancel(failed_event)
            return

    async def _start_job(self):
        uuidcode = uuid.uuid4().hex
        self.port = random_port()
        # Test setup
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": self.backend_services_token
        }
        auth_state = await self.user.get_auth_state()
        if auth_state is None:
            auth_state = {}
        
        # Test setup
        user_options = {
            "service": "JupyterLab/JupyterLab-no-tunnel",
            "system": "DEMO-SITE",
            "partition": "LoginNode",
            "project": "project1",
            "account": "demouser",
            "vo": "myvo",
        }

        popen_kwargs = {
            "auth_state": auth_state,
            "env": self.get_env(),
            "user_options": user_options
        }
        # Test setup
        popen_kwargs["auth_state"]["access_token"] = "ZGVtb3VzZXI6dGVzdDEyMw=="
        popen_kwargs["env"]["PORT"] = self.port
        req = HTTPRequest(
            f"{self.backend_services_url}?uuidcode={uuidcode}",
            method="POST",
            headers=headers,
            body=json.dumps(popen_kwargs),
        )
        max_start_attempts = 1
        for i in range(0, max_start_attempts):
            try:
                resp = await self.user.authenticator.fetch(req, parse_json=True)
                self.log.info(f"Server started. -- 'uuidcode': {uuidcode}, 'response': {resp}")
                break
            except Exception as e:
                if i < max_start_attempts - 1:
                    continue
                error = "Jupyter-JSC backend service could not start your service."
                error_detail = str(e)
                if isinstance(e, HTTPClientError):
                    if len(e.args) > 2:
                        orig_response = e.args[2]
                        if isinstance(orig_response, HTTPResponse):
                            error_json = json.loads(orig_response.body.decode("utf-8"))
                            error = error_json.get("error", error)
                            error_detail = error_json.get("error_detail", error_detail)
                self.log.exception(
                    "Exception while starting service",
                    extra={
                        "uuidcode": uuidcode,
                        "log_name": self._log_name,
                        "user": self.user.name,
                        "action": "start",
                        "user_options": user_options,
                    },
                )
                raise BackendException(error, error_detail)
        self.id = uuidcode
        return ("localhost", self.port)

    def start(self):
        self.events = []
        self.cancel_event_yielded = False
        self._start_future = asyncio.ensure_future(self._start())
        return self._start_future

    async def poll(self):
        auth_state = await self.user.get_auth_state()
        access_token = auth_state["access_token"]
        # Debug
        access_token = "ZGVtb3VzZXI6dGVzdDEyMw=="
        uuidcode = uuid.uuid4().hex
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": self.backend_services_token
        }
        req = HTTPRequest(
            f"{self.backend_services_url}{self.id}/?access_token={access_token}&uuidcode={uuidcode}",
            headers=headers,
        )
        max_poll_attempts = 1
        for i in range(0, max_poll_attempts):
            try:
                resp = await self.user.authenticator.fetch(req, parse_json=True)
                self.log.info(f"Server polled. -- 'uuidcode': {uuidcode}, 'response': {resp}")
                break
            except Exception as e:
                if i < max_poll_attempts - 1:
                    continue
                error = "Jupyter-JSC backend service could not poll your service."
                error_detail = str(e)
                if isinstance(e, HTTPClientError):
                    if len(e.args) > 2:
                        orig_response = e.args[2]
                        if isinstance(orig_response, HTTPResponse):
                            error_json = json.loads(orig_response.body.decode("utf-8"))
                            error = error_json.get("error", error)
                            error_detail = error_json.get("error_detail", error_detail)
                self.log.exception(
                    "Exception while starting service",
                    extra={
                        "uuidcode": uuidcode,
                        "log_name": self._log_name,
                        "user": self.user.name,
                        "action": "poll",
                    },
                )
                return None
        if not resp.get("running", True):
            return 0
        return None

    def stop(self):
        return asyncio.ensure_future(self._stop())

    async def _stop(self):
        if not self.id:
            return
        uuidcode = uuid.uuid4().hex
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": self.backend_services_token
        }
        auth_state = await self.user.get_auth_state()
        access_token = auth_state["access_token"]
        # Debug
        access_token = "ZGVtb3VzZXI6dGVzdDEyMw=="
        req = HTTPRequest(
            f"{self.backend_services_url}{self.id}/?access_token={access_token}&uuidcode={uuidcode}",
            method="DELETE",
            headers=headers,
        )
        try:
            await self.user.authenticator.fetch(req)
        except Exception as e:
            error = "Jupyter-JSC backend service could not stop the service."
            error_detail = str(e)
            if isinstance(e, HTTPClientError):
                if len(e.args) > 2:
                    orig_response = e.args[2]
                    if isinstance(orig_response, HTTPResponse):
                        error_json = json.loads(orig_response.body.decode("utf-8"))
                        error = error_json.get("error", error)
                        error_detail = error_json.get("error_detail", error_detail)
            self.log.exception(
                "Exception while stopping service",
                extra={
                    "uuidcode": uuidcode,
                    "log_name": self._log_name,
                    "user": self.user.name,
                    "action": "stop_failed",
                },
            )
            raise Exception(f"{error} ---- {error_detail}")

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
