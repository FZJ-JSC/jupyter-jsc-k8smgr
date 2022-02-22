import json
import html
import time

from jupyterhub.apihandlers.base import APIHandler
from jupyterhub.scopes import needs_scope
from tornado import web

from jupyterhub.metrics import PROXY_DELETE_DURATION_SECONDS
from jupyterhub.metrics import ProxyDeleteStatus


class SpawnCancelAPIHandler(APIHandler):
    @needs_scope("access:servers")
    async def post(self, username, server_name=""):
        self.set_header("Cache-Control", "no-cache")
        uuidcode = self.request.headers.get("uuidcode", "<no_uuidcode>")
        self.log.info(
            "APICall: SpawnCancel",
            extra={
                "uuidcode": uuidcode,
                "log_name": f"{username}:{server_name}",
                "user": username,
                "action": "cancel",
            },
        )
        user = self.find_user(username)
        if user is None:
            # no such user
            raise web.HTTPError(404)
        if server_name not in user.spawners:
            # user has no such server
            raise web.HTTPError(404)
        spawner = user.spawners[server_name]

        body = self.request.body.decode("utf8")
        json_body = json.loads(body) if body else {}
        error = json_body.get("error", "Start cancelled.")
        detail_error = json_body.get("detail_error", "Start cancelled via API call.")
        failed_event = {
                "progress": 100,
                "failed": True,
                "html_message": '<details><summary>{}<span class="caret"></span></summary><p>{}</p></details>'.format(
                    html.escape(error), html.escape(detail_error)
                )
            }

        # Delete route from proxy
        proxy_deletion_start_time = time.perf_counter()
        try:
            await self.proxy.delete_user(user, server_name)
            PROXY_DELETE_DURATION_SECONDS.labels(
                status=ProxyDeleteStatus.success
            ).observe(time.perf_counter() - proxy_deletion_start_time)
        except Exception:
            PROXY_DELETE_DURATION_SECONDS.labels(
                status=ProxyDeleteStatus.failure
            ).observe(time.perf_counter() - proxy_deletion_start_time)
            raise

        await spawner._cancel(failed_event)
        self.set_header("Content-Type", "text/plain")
        self.set_status(204)

