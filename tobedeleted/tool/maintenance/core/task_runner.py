from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Callable, Generic, TypeVar

from tool.maintenance.core.logging_setup import log_to_file


T = TypeVar("T")


@dataclass(frozen=True)
class TaskResult(Generic[T]):
    ok: bool
    value: T | None
    error: Exception | None


class TaskRunner:
    """
    Small helper to run background tasks consistently:
    - catches exceptions and logs them
    - provides a UI-safe `ui()` callback (Tk root.after)
    """

    def __init__(self, *, ui_call: Callable[[Callable[[], None]], None]):
        self._ui_call = ui_call

    def ui(self, fn: Callable[[], None]) -> None:
        self._ui_call(fn)

    def run(
        self,
        *,
        name: str,
        fn: Callable[[], T],
        on_done: Callable[[TaskResult[T]], None] | None = None,
    ) -> None:
        def _worker():
            try:
                value = fn()
                res: TaskResult[T] = TaskResult(ok=True, value=value, error=None)
            except Exception as e:
                log_to_file(f"[TaskRunner] {name} failed: {e}", "ERROR")
                res = TaskResult(ok=False, value=None, error=e)

            if on_done is not None:
                try:
                    self.ui(lambda: on_done(res))
                except Exception:
                    pass

        threading.Thread(target=_worker, daemon=True).start()

