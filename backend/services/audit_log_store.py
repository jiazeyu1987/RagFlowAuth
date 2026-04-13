from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from typing import Any, Optional

from backend.database.paths import resolve_auth_db_path
from backend.database.sqlite import connect_sqlite


@dataclass(frozen=True)
class AuditEvent:
    id: int
    action: str
    actor: str
    actor_username: Optional[str]
    company_id: Optional[int]
    company_name: Optional[str]
    department_id: Optional[int]
    department_name: Optional[str]
    created_at_ms: int
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    event_type: Optional[str] = None
    before_json: Optional[str] = None
    after_json: Optional[str] = None
    reason: Optional[str] = None
    signature_id: Optional[str] = None
    request_id: Optional[str] = None
    client_ip: Optional[str] = None
    prev_hash: Optional[str] = None
    event_hash: Optional[str] = None
    # Optional context
    source: Optional[str] = None  # ragflow|knowledge|auth|system
    doc_id: Optional[str] = None
    filename: Optional[str] = None
    kb_id: Optional[str] = None
    kb_dataset_id: Optional[str] = None
    kb_name: Optional[str] = None
    meta_json: Optional[str] = None
    evidence_json: Optional[str] = None


def _to_json_text(value: Any) -> str | None:
    if value is None:
        return None
    try:
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    except Exception:
        return None


def _event_hash_hex(payload: dict[str, Any]) -> str:
    text = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class AuditLogStore:
    """
    Unified audit/event log store.

    Used to record user-visible operations across the system:
    - auth: login/logout
    - documents: preview/upload/download/delete

    Notes:
    - This is additive; existing specialized logs (download_logs/deletion_logs) are kept for compatibility.
    - Avoid putting secrets into meta_json.
    """

    def __init__(self, db_path: str | None = None):
        self.db_path = resolve_auth_db_path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def _get_connection(self):
        return connect_sqlite(self.db_path)

    def log_event(
        self,
        *,
        action: str,
        actor: str,
        actor_username: str | None = None,
        company_id: int | None = None,
        company_name: str | None = None,
        department_id: int | None = None,
        department_name: str | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
        event_type: str | None = None,
        before: Any | None = None,
        after: Any | None = None,
        reason: str | None = None,
        signature_id: str | None = None,
        request_id: str | None = None,
        client_ip: str | None = None,
        source: str | None = None,
        doc_id: str | None = None,
        filename: str | None = None,
        kb_id: str | None = None,
        kb_dataset_id: str | None = None,
        kb_name: str | None = None,
        meta: dict[str, Any] | None = None,
        evidence_refs: list[dict[str, Any]] | None = None,
    ) -> AuditEvent:
        now_ms = int(time.time() * 1000)
        meta_json = _to_json_text(meta)
        before_json = _to_json_text(before)
        after_json = _to_json_text(after)
        evidence_json = _to_json_text(evidence_refs)

        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT event_hash FROM audit_events WHERE event_hash IS NOT NULL ORDER BY id DESC LIMIT 1")
            row = cursor.fetchone()
            prev_hash = str(row[0]) if row and row[0] else None

            event_hash = _event_hash_hex(
                {
                    "action": (action or "").strip(),
                    "actor": (actor or "").strip(),
                    "created_at_ms": now_ms,
                    "resource_type": (resource_type or None),
                    "resource_id": (resource_id or None),
                    "event_type": (event_type or None),
                    "before_json": before_json,
                    "after_json": after_json,
                    "reason": (reason or None),
                    "signature_id": (signature_id or None),
                    "request_id": (request_id or None),
                    "client_ip": (client_ip or None),
                    "source": (source or None),
                    "doc_id": (doc_id or None),
                    "filename": (filename or None),
                    "kb_id": (kb_id or None),
                    "kb_dataset_id": (kb_dataset_id or None),
                    "kb_name": (kb_name or kb_id or None),
                    "meta_json": meta_json,
                    "evidence_json": evidence_json,
                    "prev_hash": prev_hash,
                }
            )

            placeholders = ", ".join(["?"] * 27)
            cursor.execute(
                f"""
                INSERT INTO audit_events (
                    action, actor, created_at_ms,
                    actor_username, company_id, company_name, department_id, department_name,
                    resource_type, resource_id, event_type,
                    before_json, after_json, reason, signature_id, request_id, client_ip,
                    prev_hash, event_hash,
                    source, doc_id, filename,
                    kb_id, kb_dataset_id, kb_name,
                    meta_json, evidence_json
                ) VALUES ({placeholders})
                """,
                (
                    (action or "").strip(),
                    (actor or "").strip(),
                    now_ms,
                    (actor_username or None),
                    (int(company_id) if company_id is not None else None),
                    (company_name or None),
                    (int(department_id) if department_id is not None else None),
                    (department_name or None),
                    (resource_type or None),
                    (resource_id or None),
                    (event_type or None),
                    before_json,
                    after_json,
                    (reason or None),
                    (signature_id or None),
                    (request_id or None),
                    (client_ip or None),
                    prev_hash,
                    event_hash,
                    (source or None),
                    (doc_id or None),
                    (filename or None),
                    (kb_id or None),
                    (kb_dataset_id or None),
                    (kb_name or kb_id or None),
                    meta_json,
                    evidence_json,
                ),
            )
            conn.commit()
            cursor.execute("SELECT last_insert_rowid()")
            event_id = int(cursor.fetchone()[0])
            return AuditEvent(
                id=event_id,
                action=(action or "").strip(),
                actor=(actor or "").strip(),
                actor_username=(actor_username or None),
                company_id=(int(company_id) if company_id is not None else None),
                company_name=(company_name or None),
                department_id=(int(department_id) if department_id is not None else None),
                department_name=(department_name or None),
                created_at_ms=now_ms,
                resource_type=(resource_type or None),
                resource_id=(resource_id or None),
                event_type=(event_type or None),
                before_json=before_json,
                after_json=after_json,
                reason=(reason or None),
                signature_id=(signature_id or None),
                request_id=(request_id or None),
                client_ip=(client_ip or None),
                prev_hash=prev_hash,
                event_hash=event_hash,
                source=(source or None),
                doc_id=(doc_id or None),
                filename=(filename or None),
                kb_id=(kb_id or None),
                kb_dataset_id=(kb_dataset_id or None),
                kb_name=(kb_name or kb_id or None),
                meta_json=meta_json,
                evidence_json=evidence_json,
            )
        finally:
            conn.close()

    def list_events(
        self,
        *,
        action: str | None = None,
        actor: str | None = None,
        actor_username: str | None = None,
        company_id: int | None = None,
        department_id: int | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
        event_type: str | None = None,
        signature_id: str | None = None,
        request_id: str | None = None,
        source: str | None = None,
        doc_id: str | None = None,
        filename: str | None = None,
        kb_id: str | None = None,
        kb_dataset_id: str | None = None,
        kb_name: str | None = None,
        kb_ref: str | None = None,
        from_ms: int | None = None,
        to_ms: int | None = None,
        offset: int = 0,
        limit: int = 200,
    ) -> tuple[int, list[AuditEvent]]:
        lim = int(limit) if int(limit) > 0 else 200
        lim = min(lim, 2000)
        off = int(offset) if int(offset) > 0 else 0

        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            where = " WHERE 1=1"
            params: list[Any] = []

            if action:
                where += " AND action = ?"
                params.append(action)
            if actor:
                where += " AND actor = ?"
                params.append(actor)
            if actor_username:
                where += " AND actor_username = ?"
                params.append(actor_username)
            if company_id is not None:
                where += " AND company_id = ?"
                params.append(int(company_id))
            if department_id is not None:
                where += " AND department_id = ?"
                params.append(int(department_id))
            if resource_type:
                where += " AND resource_type = ?"
                params.append(resource_type)
            if resource_id:
                where += " AND resource_id = ?"
                params.append(resource_id)
            if event_type:
                where += " AND event_type = ?"
                params.append(event_type)
            if signature_id:
                where += " AND signature_id = ?"
                params.append(signature_id)
            if request_id:
                where += " AND request_id = ?"
                params.append(request_id)
            if source:
                where += " AND source = ?"
                params.append(source)
            if doc_id:
                where += " AND doc_id = ?"
                params.append(doc_id)
            if filename:
                where += " AND filename = ?"
                params.append(filename)
            if kb_id:
                where += " AND kb_id = ?"
                params.append(kb_id)
            if kb_dataset_id:
                where += " AND kb_dataset_id = ?"
                params.append(kb_dataset_id)
            if kb_name:
                where += " AND kb_name = ?"
                params.append(kb_name)
            if kb_ref:
                where += " AND (kb_id = ? OR kb_dataset_id = ? OR kb_name = ?)"
                params.extend([kb_ref, kb_ref, kb_ref])
            if from_ms is not None:
                where += " AND created_at_ms >= ?"
                params.append(int(from_ms))
            if to_ms is not None:
                where += " AND created_at_ms <= ?"
                params.append(int(to_ms))

            cursor.execute(f"SELECT COUNT(*) FROM audit_events{where}", params)
            total = int(cursor.fetchone()[0])

            cursor.execute(
                f"""
                SELECT
                    id, action, actor,
                    actor_username, company_id, company_name, department_id, department_name,
                    created_at_ms,
                    resource_type, resource_id, event_type,
                    before_json, after_json, reason, signature_id, request_id, client_ip,
                    prev_hash, event_hash,
                    source, doc_id, filename,
                    kb_id, kb_dataset_id, kb_name,
                    meta_json, evidence_json
                FROM audit_events
                {where}
                ORDER BY created_at_ms DESC
                LIMIT ? OFFSET ?
                """,
                [*params, lim, off],
            )

            rows = cursor.fetchall()
            return total, [AuditEvent(*row) for row in rows]
        finally:
            conn.close()
