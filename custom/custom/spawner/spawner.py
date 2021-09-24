import asyncio
from asyncio.tasks import sleep

from jupyterhub.spawner import Spawner
from jupyterhub.utils import maybe_future


class BackendSpawner(Spawner):
    events = []
    cancel_event_yielded = False
    yield_wait_seconds = 1
    _start_future = None

    async def _start(self):
        self.log.info("Start's taking sooo ...")
        await asyncio.sleep(0.5)
        self.log.info("...long")
        return "http://127.0.0.1:9999"

    def start(self):
        self.events = []
        self.cancel_event_yielded = False
        self._start_future = asyncio.ensure_future(self._start())
        return self._start_future

    async def poll(self):
        return None

    def stop(self):
        return asyncio.ensure_future(self._stop())

    async def _stop(self):
        self.log.info("Stop's taking sooo ...")
        await asyncio.sleep(0.5)
        self.log.info("...long")

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
