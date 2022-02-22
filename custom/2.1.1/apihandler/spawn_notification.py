import asyncio
from tornado import web

from jupyterhub.apihandlers.base import APIHandler
from jupyterhub.scopes import needs_scope
from tornado.iostream import StreamClosedError


class SpawnNotificationAPIHandler(APIHandler):
    """EventStream handler for active spawns"""

    keepalive_interval = 8

    def get_content_type(self):
        return 'text/event-stream'

    def initialize(self):
        super().initialize()
        self._finish_future = asyncio.Future()

    def on_finish(self):
        self._finish_future.set_result(None)
        
    async def keepalive(self):
        """Write empty lines periodically

        to avoid being closed by intermediate proxies
        when there's a large gap between events.
        """
        while not self._finish_future.done():
            try:
                self.write("\n\n")
                await self.flush()
            except (StreamClosedError, RuntimeError):
                return

            await asyncio.wait([self._finish_future], timeout=self.keepalive_interval)

    @needs_scope("read:servers")
    async def get(self, username):
        self.set_header("Cache-Control", "no-cache")
        user = self.find_user(username)
        if user is None:
            # no such user
            raise web.HTTPError(404)

        # start sending keepalive to avoid proxies closing the connection
        asyncio.ensure_future(self.keepalive())

        event = user.spawn_event  # asyncio.Event()
        await event.wait()
        spawners = user.spawners.values()
        # Set active spawners as event data
        event_data = {s.name: s.pending for s in spawners if s.pending}
        await self.send_event(event_data)
        # Clear event after sending in case stream has been closed
        event.clear()
        return
