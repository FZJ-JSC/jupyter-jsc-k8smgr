import asyncio
import json

from jupyterhub.apihandlers.base import APIHandler
from jupyterhub.apihandlers.users import admin_or_self
from jupyterhub.utils import maybe_future
from tornado import web

user_cancel_message = "Start cancelled by user."


class SpawnProgressUpdateAPIHandler(APIHandler):
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

    async def _stop(self, username, server_name, failed_event={}):
        user = self.find_user(username)
        spawner = user.spawners[server_name]
        if not failed_event:
            failed_event = {
                "progress": 100,
                "failed": True,
                "html_message": "Cancelled.",
            }
        spawner.events.append(failed_event)
        for i in range(0, 2):
            if spawner.cancel_event_yielded:
                break
            else:
                await asyncio.sleep(spawner.yield_wait_seconds)
        if spawner._start_future:
            await self.cancel_future(spawner._start_future)
        await self.cancel_future(spawner._spawn_future)

    @admin_or_self
    def post(self, username, server_name=""):
        self.set_header("Cache-Control", "no-cache")
        uuidcode = self.request.headers.get("uuidcode", "<no_uuidcode>")
        if server_name is None:
            server_name = ""
        user = self.find_user(username)
        if user is None:
            # no such user
            raise web.HTTPError(404)
        if server_name not in user.spawners:
            # user has no such server
            raise web.HTTPError(404)
        body = self.request.body.decode("utf8")
        event = json.loads(body) if body else {}

        if event and event.get("failed", False):
            if event.get("html_message", "") == user_cancel_message:
                self.log.debug(
                    "APICall: SpawnUpdate",
                    extra={
                        "uuidcode": uuidcode,
                        "log_name": f"{username}:{server_name}",
                        "user": username,
                        "action": "cancel",
                    },
                )
            else:
                self.log.info(
                    "APICall: SpawnUpdate",
                    extra={
                        "uuidcode": uuidcode,
                        "log_name": f"{username}:{server_name}",
                        "user": username,
                        "action": "failed",
                        "event": event,
                    },
                )
            cancel_future = asyncio.ensure_future(
                self._stop(username, server_name, event)
            )
            self.set_header("Content-Type", "text/plain")
            self.set_status(204)
            return cancel_future
        elif event:
            self.log.debug(
                "APICall: SpawnUpdate",
                extra={
                    "uuidcode": uuidcode,
                    "log_name": f"{username}:{server_name}",
                    "user": username,
                    "action": "spawnupdate",
                    "event": event,
                },
            )
            spawner = user.spawners[server_name]
            spawner.events.append(event)
            self.set_header("Content-Type", "text/plain")
            self.set_status(204)
            return
        else:
            self.set_header("Content-Type", "text/plain")
            self.write("Bad Request - No event in request body.")
            self.set_status(400)
            return
