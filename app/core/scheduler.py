import asyncio
from typing import Optional, Callable

class AutoRunner:
    def __init__(self, interval_seconds: int = 300):
        self.interval = interval_seconds
        self._task: Optional[asyncio.Task] = None
        self.enabled: bool = False

    async def _loop(self, job: Callable[[], "asyncio.Future | None"]):
        try:
            while self.enabled:
                try:
                    res = job()
                    if asyncio.iscoroutine(res):
                        await res
                except Exception as e:
                    print(f"[AutoRunner] Job error: {e}")
                await asyncio.sleep(self.interval)
        finally:
            self._task = None

    def start(self, job: Callable[[], "asyncio.Future | None"]):
        if not self.enabled:
            self.enabled = True
            self._task = asyncio.create_task(self._loop(job))

    def stop(self):
        self.enabled = False
