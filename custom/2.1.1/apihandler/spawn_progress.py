import asyncio
import json

from jupyterhub.apihandlers.base import APIHandler
from jupyterhub.scopes import needs_scope
from tornado import web

user_cancel_message = "Start cancelled by user."


class SpawnProgressUpdateAPIHandler(APIHandler):
    @needs_scope("access:servers")
    def post(self, user_name, server_name=""):
        self.set_header("Cache-Control", "no-cache")
        uuidcode = self.request.headers.get("uuidcode", "<no_uuidcode>")
        if server_name is None:
            server_name = ""
        user = self.find_user(user_name)
        if user is None:
            # no such user
            raise web.HTTPError(404)
        if server_name not in user.spawners:
            # user has no such server
            raise web.HTTPError(404)
        body = self.request.body.decode("utf8")
        self.log.info(body)
        event = json.loads(body) if body else {}

        user = self.find_user(user_name)
        spawner = user.spawners[server_name]

        if event and event.get("failed", False):
            if event.get("html_message", "") == user_cancel_message:
                self.log.debug(
                    "APICall: SpawnUpdate",
                    extra={
                        "uuidcode": uuidcode,
                        "log_name": f"{user_name}:{server_name}",
                        "user": user_name,
                        "action": "cancel",
                    },
                )
            else:
                self.log.info(
                    "APICall: SpawnUpdate",
                    extra={
                        "uuidcode": uuidcode,
                        "log_name": f"{user_name}:{server_name}",
                        "user": user_name,
                        "action": "failed",
                        "event": event,
                    },
                )
            cancel_future = asyncio.ensure_future(spawner._cancel(event))
            self.set_header("Content-Type", "text/plain")
            self.set_status(204)
            return cancel_future
        elif event:
            self.log.debug(
                "APICall: SpawnUpdate",
                extra={
                    "uuidcode": uuidcode,
                    "log_name": f"{user_name}:{server_name}",
                    "user": user_name,
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


class SpawnProgressStatusAPIHandler(APIHandler):
    @needs_scope("read:servers")
    async def get(self, username, server_name=""):
        user = self.find_user(username)
        if user is None:
            # no such user
            raise web.HTTPError(404)
        if server_name not in user.spawners:
            # user has no such server
            raise web.HTTPError(404)
        spawner = user.spawners[server_name]
        data = {
            "events": spawner.events,
            "active": spawner.active,
            "ready": spawner.ready
        }
        self.write(json.dumps(data))
