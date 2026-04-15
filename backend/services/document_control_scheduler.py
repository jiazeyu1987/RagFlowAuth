from __future__ import annotations

import logging
import sqlite3
import threading
import time
from types import SimpleNamespace

from backend.database.sqlite import connect_sqlite
from backend.services.compliance.retired_records import RetiredRecordsService
from backend.services.document_control.service import DocumentControlService


logger = logging.getLogger(__name__)


class DocumentControlScheduler:
    def __init__(self, *, deps, interval_seconds: int = 60):
        self._deps = deps
        self._interval_seconds = max(5, int(interval_seconds or 60))
        self._running = False
        self._thread = None
        self._stop_event = None

    @staticmethod
    def _system_ctx():
        return SimpleNamespace(
            payload=SimpleNamespace(sub="system"),
            user=SimpleNamespace(
                user_id="system",
                username="system",
                role="admin",
                company_id=None,
                department_id=None,
            ),
            snapshot=SimpleNamespace(is_admin=True),
        )

    def _tenant_dependency_sets(self) -> list[object]:
        operation_approval_service = getattr(self._deps, "operation_approval_service", None)
        resolver = getattr(operation_approval_service, "_execution_deps_resolver", None)
        org_structure_manager = getattr(self._deps, "org_structure_manager", None)
        list_companies = getattr(org_structure_manager, "list_companies", None)
        if not callable(resolver) or not callable(list_companies):
            return [self._deps]

        tenant_deps_list: list[object] = []
        seen_company_ids: set[int] = set()
        for company in list_companies() or []:
            raw_company_id = getattr(company, "company_id", None)
            try:
                company_id = int(raw_company_id)
            except Exception:
                continue
            if company_id <= 0 or company_id in seen_company_ids:
                continue
            tenant_deps_list.append(resolver(company_id))
            seen_company_ids.add(company_id)
        return tenant_deps_list or [self._deps]

    def _approval_revision_ids(self, deps) -> list[str]:
        kb_store = getattr(deps, "kb_store", None)
        db_path = getattr(kb_store, "db_path", None)
        if not db_path:
            return []
        conn = connect_sqlite(db_path)
        try:
            try:
                rows = conn.execute(
                    """
                    SELECT controlled_revision_id
                    FROM controlled_revisions
                    WHERE status = 'approval_in_progress'
                      AND approval_request_id IS NOT NULL
                    ORDER BY approval_submitted_at_ms ASC, controlled_revision_id ASC
                    """
                ).fetchall()
            except sqlite3.OperationalError as exc:
                message = str(exc or "").lower()
                if "no such table" in message and "controlled_revisions" in message:
                    logger.warning("Document-control scheduler skipped db without controlled_revisions table: %s", db_path)
                    return []
                raise
            return [str(row["controlled_revision_id"]) for row in rows if row]
        finally:
            conn.close()

    def run_once(self) -> dict[str, int]:
        ctx = self._system_ctx()
        reminded = 0
        reminder_errors = 0

        purged = 0
        for tenant_deps in self._tenant_dependency_sets():
            document_control_service = DocumentControlService.from_deps(tenant_deps)
            for revision_id in self._approval_revision_ids(tenant_deps):
                try:
                    result = document_control_service.remind_overdue_revision_approval_step(
                        controlled_revision_id=revision_id,
                        ctx=ctx,
                        note="scheduled_approval_timeout_check",
                    )
                    reminded += int(result.get("count") or 0)
                except Exception:
                    reminder_errors += 1
                    logger.error("Document-control overdue reminder scan failed for revision %s", revision_id, exc_info=True)

            try:
                purged += len(RetiredRecordsService(kb_store=tenant_deps.kb_store).purge_expired_documents())
            except Exception:
                logger.error("Document-control expired-retention purge failed", exc_info=True)

        return {
            "reminded": reminded,
            "reminder_errors": reminder_errors,
            "purged": purged,
        }

    def _loop(self):
        logger.info("Document control scheduler started")
        while self._running and self._stop_event is not None and not self._stop_event.wait(self._interval_seconds):
            try:
                result = self.run_once()
                if any(int(result.get(key) or 0) > 0 for key in ("reminded", "reminder_errors", "purged")):
                    logger.info("Document control scheduler cycle: %s", result)
            except Exception:
                logger.error("Fatal document control scheduler loop error", exc_info=True)
        logger.info("Document control scheduler stopped")

    def start(self):
        if self._running:
            return
        self._running = True
        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._loop, daemon=True, name="document-control-scheduler")
        self._thread.start()

    def stop(self):
        if not self._running:
            return
        self._running = False
        if self._stop_event is not None:
            self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=5)
        self._thread = None
        self._stop_event = None


_document_control_scheduler: DocumentControlScheduler | None = None


def init_document_control_scheduler(*, deps, interval_seconds: int = 60) -> DocumentControlScheduler:
    global _document_control_scheduler
    _document_control_scheduler = DocumentControlScheduler(deps=deps, interval_seconds=interval_seconds)
    return _document_control_scheduler


def stop_document_control_scheduler():
    global _document_control_scheduler
    if _document_control_scheduler is not None:
        _document_control_scheduler.stop()
