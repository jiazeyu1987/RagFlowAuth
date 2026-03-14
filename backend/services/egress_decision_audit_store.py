from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any

from backend.database.paths import resolve_auth_db_path
from backend.database.sqlite import connect_sqlite


@dataclass(frozen=True)
class EgressDecisionAuditRecord:
    id: int
    request_id: str
    actor_user_id: str
    policy_mode: str
    decision: str
    hit_rules: list[dict[str, Any]]
    reason: str | None
    target_host: str | None
    target_model: str | None
    payload_level: str | None
    request_meta: dict[str, Any]
    created_at_ms: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "request_id": self.request_id,
            "actor_user_id": self.actor_user_id,
            "policy_mode": self.policy_mode,
            "decision": self.decision,
            "hit_rules": self.hit_rules,
            "reason": self.reason,
            "target_host": self.target_host,
            "target_model": self.target_model,
            "payload_level": self.payload_level,
            "request_meta": self.request_meta,
            "created_at_ms": self.created_at_ms,
        }


def _safe_json_dumps(payload: Any, *, default_json: str) -> str:
    try:
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    except Exception:
        return default_json


def _safe_json_loads(text: str, *, default_value: Any) -> Any:
    try:
        return json.loads(text or "")
    except Exception:
        return default_value


class EgressDecisionAuditStore:
    def __init__(self, db_path: str | None = None) -> None:
        self.db_path = resolve_auth_db_path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def _conn(self):
        return connect_sqlite(self.db_path)

    def log_decision(
        self,
        *,
        request_id: str | None,
        actor_user_id: str | None,
        policy_mode: str | None,
        decision: str,
        hit_rules: list[dict[str, Any]] | None = None,
        reason: str | None = None,
        target_host: str | None = None,
        target_model: str | None = None,
        payload_level: str | None = None,
        request_meta: dict[str, Any] | None = None,
        created_at_ms: int | None = None,
    ) -> EgressDecisionAuditRecord:
        normalized_decision = str(decision or "").strip().lower()
        if normalized_decision not in {"allow", "block"}:
            normalized_decision = "allow"

        now_ms = int(time.time() * 1000) if created_at_ms is None else int(created_at_ms)
        payload_json = _safe_json_dumps(hit_rules or [], default_json="[]")
        meta_json = _safe_json_dumps(request_meta or {}, default_json="{}")

        conn = self._conn()
        try:
            cur = conn.execute(
                """
                INSERT INTO egress_decision_audits (
                    request_id,
                    actor_user_id,
                    policy_mode,
                    decision,
                    hit_rules_json,
                    reason,
                    target_host,
                    target_model,
                    payload_level,
                    request_meta_json,
                    created_at_ms
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(request_id or "").strip() or None,
                    str(actor_user_id or "").strip(),
                    str(policy_mode or "").strip().lower() or "intranet",
                    normalized_decision,
                    payload_json,
                    str(reason or "").strip() or None,
                    str(target_host or "").strip().lower() or None,
                    str(target_model or "").strip().lower() or None,
                    str(payload_level or "").strip().lower() or None,
                    meta_json,
                    now_ms,
                ),
            )
            row_id = int(cur.lastrowid or 0)
            conn.commit()
        finally:
            conn.close()

        record = self.get_by_id(row_id)
        if record is None:
            raise RuntimeError("egress_audit_insert_failed")
        return record

    def get_by_id(self, record_id: int) -> EgressDecisionAuditRecord | None:
        conn = self._conn()
        try:
            row = conn.execute("SELECT * FROM egress_decision_audits WHERE id = ?", (int(record_id),)).fetchone()
        finally:
            conn.close()
        if not row:
            return None
        return self._to_record(row)

    @staticmethod
    def _to_record(row) -> EgressDecisionAuditRecord:
        hit_rules = _safe_json_loads(str(row["hit_rules_json"] or "[]"), default_value=[])
        if not isinstance(hit_rules, list):
            hit_rules = []
        request_meta = _safe_json_loads(str(row["request_meta_json"] or "{}"), default_value={})
        if not isinstance(request_meta, dict):
            request_meta = {}
        return EgressDecisionAuditRecord(
            id=int(row["id"] or 0),
            request_id=str(row["request_id"] or ""),
            actor_user_id=str(row["actor_user_id"] or ""),
            policy_mode=str(row["policy_mode"] or "intranet"),
            decision=str(row["decision"] or "allow"),
            hit_rules=hit_rules,
            reason=(str(row["reason"]) if row["reason"] is not None else None),
            target_host=(str(row["target_host"]) if row["target_host"] is not None else None),
            target_model=(str(row["target_model"]) if row["target_model"] is not None else None),
            payload_level=(str(row["payload_level"]) if row["payload_level"] is not None else None),
            request_meta=request_meta,
            created_at_ms=int(row["created_at_ms"] or 0),
        )

    def list_decisions(
        self,
        *,
        limit: int = 100,
        decision: str | None = None,
        actor_user_id: str | None = None,
        target_host: str | None = None,
        since_ms: int | None = None,
        until_ms: int | None = None,
    ) -> list[EgressDecisionAuditRecord]:
        safe_limit = max(1, min(int(limit or 100), 500))
        where_clauses = []
        values: list[Any] = []

        normalized_decision = str(decision or "").strip().lower()
        if normalized_decision in {"allow", "block"}:
            where_clauses.append("decision = ?")
            values.append(normalized_decision)

        actor = str(actor_user_id or "").strip()
        if actor:
            where_clauses.append("actor_user_id = ?")
            values.append(actor)

        host = str(target_host or "").strip().lower()
        if host:
            where_clauses.append("target_host = ?")
            values.append(host)

        if since_ms is not None:
            where_clauses.append("created_at_ms >= ?")
            values.append(int(since_ms))
        if until_ms is not None:
            where_clauses.append("created_at_ms <= ?")
            values.append(int(until_ms))

        where_sql = ""
        if where_clauses:
            where_sql = "WHERE " + " AND ".join(where_clauses)

        query = f"""
            SELECT *
            FROM egress_decision_audits
            {where_sql}
            ORDER BY created_at_ms DESC, id DESC
            LIMIT ?
        """
        values.append(safe_limit)

        conn = self._conn()
        try:
            rows = conn.execute(query, tuple(values)).fetchall()
        finally:
            conn.close()
        return [self._to_record(row) for row in rows or []]
