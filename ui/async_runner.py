"""Run blocking work off the UI thread and deliver results back on the UI thread.

Worker threads never touch widgets. They put results in a thread-safe queue, and the Tk
main loop drains it every 40 ms with ``after()``. Callbacks are skipped when their
``owner`` widget has been destroyed in the meantime.
"""
from __future__ import annotations

import logging
import queue
import sys
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Any, Callable

log = logging.getLogger(__name__)

POLL_MS = 40


class TaskRunner:
    def __init__(self, root, max_workers: int = 4):
        self.root = root
        self._queue: "queue.Queue[Callable[[], None]]" = queue.Queue()
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="devdock-worker")
        self._closed = False
        self._after_id = root.after(POLL_MS, self._poll)

    # ------------------------------------------------------------------ public
    def submit(self, fn: Callable[..., Any], *args: Any, on_success: Callable[[Any], None] | None = None,
               on_error: Callable[[BaseException], None] | None = None, owner=None) -> Future | None:
        if self._closed:
            return None
        future = self._executor.submit(fn, *args)
        self.watch(future, on_success, on_error, owner)
        return future

    def watch(self, future: Future, on_success: Callable[[Any], None] | None = None,
              on_error: Callable[[BaseException], None] | None = None, owner=None) -> None:
        """Deliver an existing future's result on the UI thread."""
        def done(f: Future) -> None:
            if f.cancelled():
                return
            error = f.exception()
            if error is not None:
                self.post(lambda: self._deliver_error(error, on_error, owner))
            elif on_success is not None:
                result = f.result()
                self.post(lambda: self._deliver(on_success, result, owner))
        future.add_done_callback(done)

    def post(self, callback: Callable[[], None]) -> None:
        """Thread-safe: run ``callback`` on the UI thread soon."""
        if not self._closed:
            self._queue.put(callback)

    def shutdown(self) -> None:
        self._closed = True
        try:
            self.root.after_cancel(self._after_id)
        except Exception:
            pass
        self._executor.shutdown(wait=False, cancel_futures=True)

    # ------------------------------------------------------------------ internals
    @staticmethod
    def _alive(owner) -> bool:
        if owner is None:
            return True
        try:
            return bool(owner.winfo_exists())
        except Exception:
            return False

    def _deliver(self, callback: Callable[[Any], None], result: Any, owner) -> None:
        if self._alive(owner):
            callback(result)

    def _deliver_error(self, error: BaseException, on_error, owner) -> None:
        if not self._alive(owner):
            return
        if on_error is not None:
            on_error(error)
        else:
            self.root.report_callback_exception(type(error), error, error.__traceback__)

    def _poll(self) -> None:
        if self._closed:
            return
        for _ in range(200):
            try:
                callback = self._queue.get_nowait()
            except queue.Empty:
                break
            try:
                callback()
            except Exception:
                self.root.report_callback_exception(*sys.exc_info())
        self._after_id = self.root.after(POLL_MS, self._poll)
