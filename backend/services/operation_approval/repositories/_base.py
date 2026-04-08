from __future__ import annotations

from collections.abc import Callable
from typing import Any


class OperationApprovalRepositoryBase:
    def __init__(self, *, connection_factory: Callable[[], Any]):
        self._connection_factory = connection_factory

    def _conn(self):
        return self._connection_factory()

    def _borrow_connection(self, conn: Any | None):
        if conn is not None:
            return conn, False
        return self._conn(), True
