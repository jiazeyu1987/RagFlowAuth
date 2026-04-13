from __future__ import annotations

import csv
import io
import json
import time
from datetime import date, timedelta
from typing import Any
from uuid import uuid4

from backend.database.paths import resolve_auth_db_path
from backend.database.sqlite import connect_sqlite


METROLOGY_STATUSES = {"planned", "recorded", "confirmed", "approved"}
METROLOGY_RESULTS = {"passed", "failed", "conditional"}


class MetrologyServiceError(Exception):
    def __init__(self, code: str, *, status_code: int = 400):
        super().__init__(code)
        self.code = code
        self.status_code = status_code


class MetrologyService:
    def __init__(self, db_path: str | None = None, *, notification_manager: Any | None = None):
        self.db_path = resolve_auth_db_path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._notification_manager = notification_manager

    def _conn(self):
        return connect_sqlite(self.db_path)

    @staticmethod
    def _require_text(value: Any, field_name: str) -> str:
        text = str(value or "").strip()
        if not text:
            raise MetrologyServiceError(f"{field_name}_required", status_code=400)
        return text

    @staticmethod
    def _optional_text(value: Any) -> str | None:
        text = str(value or "").strip()
        return text or None

    @staticmethod
    def _optional_iso_date(value: Any, *, field_name: str) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        if not text:
            return None
        try:
            date.fromisoformat(text)
        except ValueError as exc:
            raise MetrologyServiceError(f"invalid_{field_name}", status_code=400) from exc
        return text

    @staticmethod
    def _optional_timestamp_ms(value: Any, *, field_name: str) -> int | None:
        if value is None or str(value).strip() == "":
            return None
        try:
            parsed = int(value)
        except Exception as exc:
            raise MetrologyServiceError(f"invalid_{field_name}", status_code=400) from exc
        if parsed <= 0:
            raise MetrologyServiceError(f"invalid_{field_name}", status_code=400)
        return parsed

    def _require_known_value(self, value: Any, *, field_name: str, allowed: set[str]) -> str:
        text = self._require_text(value, field_name).lower()
        if text not in allowed:
            raise MetrologyServiceError(f"invalid_{field_name}", status_code=400)
        return text

    def _require_equipment_row(self, conn, equipment_id: str):
        row = conn.execute(
            """
            SELECT equipment_id, equipment_name, owner_user_id, status
            FROM equipment_assets
            WHERE equipment_id = ?
            """,
            (equipment_id,),
        ).fetchone()
        if row is None:
            raise MetrologyServiceError("equipment_asset_not_found", status_code=404)
        return row

    def _require_record_row(self, conn, record_id: str):
        row = conn.execute(
            """
            SELECT
                record_id,
                equipment_id,
                responsible_user_id,
                status,
                planned_due_date,
                performed_at_ms,
                result_status,
                summary,
                next_due_date,
                attachments_json,
                record_notes,
                confirmation_notes,
                approval_notes,
                confirmed_by_user_id,
                confirmed_at_ms,
                approved_by_user_id,
                approved_at_ms,
                reminder_sent_at_ms,
                reminder_sent_for_due_date,
                created_by_user_id,
                updated_by_user_id,
                created_at_ms,
                updated_at_ms
            FROM metrology_records
            WHERE record_id = ?
            """,
            (record_id,),
        ).fetchone()
        if row is None:
            raise MetrologyServiceError("metrology_record_not_found", status_code=404)
        return row

    @staticmethod
    def _normalize_attachments(
        attachments: list[dict[str, Any]] | None,
        *,
        resource_id: str,
        actor_user_id: str,
        now_ms: int,
    ) -> list[dict[str, Any]]:
        normalized: list[dict[str, Any]] = []
        for item in attachments or []:
            if not isinstance(item, dict):
                raise MetrologyServiceError("invalid_attachments", status_code=400)
            attachment_id = str(item.get("attachment_id") or "").strip()
            filename = str(item.get("filename") or "").strip()
            mime_type = str(item.get("mime_type") or "").strip()
            storage_ref = str(item.get("storage_ref") or "").strip()
            evidence_role = str(item.get("evidence_role") or "").strip()
            if not all([attachment_id, filename, mime_type, storage_ref, evidence_role]):
                raise MetrologyServiceError("invalid_attachments", status_code=400)
            uploaded_at_raw = item.get("uploaded_at_ms")
            if uploaded_at_raw is None or str(uploaded_at_raw).strip() == "":
                uploaded_at_ms = now_ms
            else:
                try:
                    uploaded_at_ms = int(uploaded_at_raw)
                except Exception as exc:
                    raise MetrologyServiceError("invalid_attachments", status_code=400) from exc
            normalized.append(
                {
                    "attachment_id": attachment_id,
                    "resource_type": "metrology_record",
                    "resource_id": resource_id,
                    "filename": filename,
                    "mime_type": mime_type,
                    "storage_ref": storage_ref,
                    "uploaded_by": str(item.get("uploaded_by") or actor_user_id).strip(),
                    "uploaded_at_ms": uploaded_at_ms,
                    "evidence_role": evidence_role,
                }
            )
        return normalized

    @staticmethod
    def _serialize_record(row) -> dict[str, Any]:
        return {
            "record_id": str(row["record_id"]),
            "equipment_id": str(row["equipment_id"]),
            "responsible_user_id": str(row["responsible_user_id"]),
            "status": str(row["status"]),
            "planned_due_date": str(row["planned_due_date"]),
            "performed_at_ms": (int(row["performed_at_ms"]) if row["performed_at_ms"] is not None else None),
            "result_status": (str(row["result_status"]) if row["result_status"] else None),
            "summary": str(row["summary"]),
            "next_due_date": (str(row["next_due_date"]) if row["next_due_date"] else None),
            "attachments": json.loads(str(row["attachments_json"]) or "[]"),
            "record_notes": (str(row["record_notes"]) if row["record_notes"] else None),
            "confirmation_notes": (str(row["confirmation_notes"]) if row["confirmation_notes"] else None),
            "approval_notes": (str(row["approval_notes"]) if row["approval_notes"] else None),
            "confirmed_by_user_id": (str(row["confirmed_by_user_id"]) if row["confirmed_by_user_id"] else None),
            "confirmed_at_ms": (int(row["confirmed_at_ms"]) if row["confirmed_at_ms"] is not None else None),
            "approved_by_user_id": (str(row["approved_by_user_id"]) if row["approved_by_user_id"] else None),
            "approved_at_ms": (int(row["approved_at_ms"]) if row["approved_at_ms"] is not None else None),
            "created_by_user_id": str(row["created_by_user_id"]),
            "updated_by_user_id": str(row["updated_by_user_id"]),
            "created_at_ms": int(row["created_at_ms"] or 0),
            "updated_at_ms": int(row["updated_at_ms"] or 0),
        }

    def get_record(self, record_id: str) -> dict[str, Any]:
        record_id = self._require_text(record_id, "record_id")
        conn = self._conn()
        try:
            return self._serialize_record(self._require_record_row(conn, record_id))
        finally:
            conn.close()

    def list_records(
        self,
        *,
        limit: int = 100,
        equipment_id: str | None = None,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        limit = max(1, min(int(limit or 100), 200))
        where = []
        params: list[Any] = []
        if equipment_id:
            where.append("equipment_id = ?")
            params.append(str(equipment_id).strip())
        if status:
            clean_status = self._require_known_value(status, field_name="status", allowed=METROLOGY_STATUSES)
            where.append("status = ?")
            params.append(clean_status)
        where_sql = f"WHERE {' AND '.join(where)}" if where else ""
        conn = self._conn()
        try:
            rows = conn.execute(
                f"""
                SELECT record_id
                FROM metrology_records
                {where_sql}
                ORDER BY updated_at_ms DESC, record_id DESC
                LIMIT ?
                """,
                [*params, limit],
            ).fetchall()
            return [self._serialize_record(self._require_record_row(conn, str(row["record_id"]))) for row in rows]
        finally:
            conn.close()

    def create_record(
        self,
        *,
        equipment_id: str,
        responsible_user_id: str,
        actor_user_id: str,
        planned_due_date: str,
        summary: str,
        result_status: str | None = None,
        performed_at_ms: int | None = None,
        next_due_date: str | None = None,
        attachments: list[dict[str, Any]] | None = None,
        record_notes: str | None = None,
    ) -> dict[str, Any]:
        equipment_id = self._require_text(equipment_id, "equipment_id")
        responsible_user_id = self._require_text(responsible_user_id, "responsible_user_id")
        actor_user_id = self._require_text(actor_user_id, "actor_user_id")
        planned_due_date = self._optional_iso_date(planned_due_date, field_name="planned_due_date")
        if planned_due_date is None:
            raise MetrologyServiceError("planned_due_date_required", status_code=400)
        summary = self._require_text(summary, "summary")
        performed_at_ms = self._optional_timestamp_ms(performed_at_ms, field_name="performed_at_ms")
        clean_result_status = None
        if result_status is not None and str(result_status).strip():
            clean_result_status = self._require_known_value(
                result_status,
                field_name="result_status",
                allowed=METROLOGY_RESULTS,
            )
        if performed_at_ms is None and clean_result_status is not None:
            raise MetrologyServiceError("performed_at_ms_required", status_code=400)
        if performed_at_ms is not None and clean_result_status is None:
            raise MetrologyServiceError("result_status_required", status_code=400)
        next_due_date = self._optional_iso_date(next_due_date, field_name="next_due_date")
        now_ms = int(time.time() * 1000)
        record_id = str(uuid4())
        clean_attachments = self._normalize_attachments(
            attachments,
            resource_id=record_id,
            actor_user_id=actor_user_id,
            now_ms=now_ms,
        )
        status = "recorded" if performed_at_ms is not None else "planned"
        conn = self._conn()
        try:
            conn.execute("BEGIN IMMEDIATE")
            equipment_row = self._require_equipment_row(conn, equipment_id)
            if str(equipment_row["status"]) == "retired":
                raise MetrologyServiceError("equipment_asset_retired", status_code=409)
            conn.execute(
                """
                INSERT INTO metrology_records (
                    record_id,
                    equipment_id,
                    responsible_user_id,
                    status,
                    planned_due_date,
                    performed_at_ms,
                    result_status,
                    summary,
                    next_due_date,
                    attachments_json,
                    record_notes,
                    created_by_user_id,
                    updated_by_user_id,
                    created_at_ms,
                    updated_at_ms
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record_id,
                    equipment_id,
                    responsible_user_id,
                    status,
                    planned_due_date,
                    performed_at_ms,
                    clean_result_status,
                    summary,
                    next_due_date,
                    json.dumps(clean_attachments, ensure_ascii=False, sort_keys=True),
                    self._optional_text(record_notes),
                    actor_user_id,
                    actor_user_id,
                    now_ms,
                    now_ms,
                ),
            )
            if status == "recorded":
                conn.execute(
                    """
                    UPDATE equipment_assets
                    SET status = 'under_metrology', updated_by_user_id = ?, updated_at_ms = ?
                    WHERE equipment_id = ?
                    """,
                    (actor_user_id, now_ms, equipment_id),
                )
            conn.commit()
            return self.get_record(record_id)
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def record_result(
        self,
        *,
        record_id: str,
        actor_user_id: str,
        performed_at_ms: int,
        result_status: str,
        summary: str,
        next_due_date: str | None = None,
        attachments: list[dict[str, Any]] | None = None,
        record_notes: str | None = None,
    ) -> dict[str, Any]:
        record_id = self._require_text(record_id, "record_id")
        actor_user_id = self._require_text(actor_user_id, "actor_user_id")
        performed_at_ms = self._optional_timestamp_ms(performed_at_ms, field_name="performed_at_ms")
        if performed_at_ms is None:
            raise MetrologyServiceError("performed_at_ms_required", status_code=400)
        result_status = self._require_known_value(result_status, field_name="result_status", allowed=METROLOGY_RESULTS)
        summary = self._require_text(summary, "summary")
        next_due_date = self._optional_iso_date(next_due_date, field_name="next_due_date")
        now_ms = int(time.time() * 1000)
        clean_attachments = self._normalize_attachments(
            attachments,
            resource_id=record_id,
            actor_user_id=actor_user_id,
            now_ms=now_ms,
        )
        conn = self._conn()
        try:
            conn.execute("BEGIN IMMEDIATE")
            row = self._require_record_row(conn, record_id)
            if str(row["status"]) not in {"planned", "recorded"}:
                raise MetrologyServiceError("metrology_record_invalid_state", status_code=409)
            conn.execute(
                """
                UPDATE metrology_records
                SET status = 'recorded',
                    performed_at_ms = ?,
                    result_status = ?,
                    summary = ?,
                    next_due_date = ?,
                    attachments_json = ?,
                    record_notes = ?,
                    updated_by_user_id = ?,
                    updated_at_ms = ?
                WHERE record_id = ?
                """,
                (
                    performed_at_ms,
                    result_status,
                    summary,
                    next_due_date,
                    json.dumps(clean_attachments, ensure_ascii=False, sort_keys=True),
                    self._optional_text(record_notes),
                    actor_user_id,
                    now_ms,
                    record_id,
                ),
            )
            conn.execute(
                """
                UPDATE equipment_assets
                SET status = 'under_metrology', updated_by_user_id = ?, updated_at_ms = ?
                WHERE equipment_id = ?
                """,
                (actor_user_id, now_ms, str(row["equipment_id"])),
            )
            conn.commit()
            return self.get_record(record_id)
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def confirm_record(
        self,
        *,
        record_id: str,
        actor_user_id: str,
        confirmation_notes: str | None = None,
    ) -> dict[str, Any]:
        record_id = self._require_text(record_id, "record_id")
        actor_user_id = self._require_text(actor_user_id, "actor_user_id")
        now_ms = int(time.time() * 1000)
        conn = self._conn()
        try:
            conn.execute("BEGIN IMMEDIATE")
            row = self._require_record_row(conn, record_id)
            if str(row["status"]) != "recorded":
                raise MetrologyServiceError("metrology_record_must_be_recorded", status_code=409)
            conn.execute(
                """
                UPDATE metrology_records
                SET status = 'confirmed',
                    confirmation_notes = ?,
                    confirmed_by_user_id = ?,
                    confirmed_at_ms = ?,
                    updated_by_user_id = ?,
                    updated_at_ms = ?
                WHERE record_id = ?
                """,
                (
                    self._optional_text(confirmation_notes),
                    actor_user_id,
                    now_ms,
                    actor_user_id,
                    now_ms,
                    record_id,
                ),
            )
            conn.commit()
            return self.get_record(record_id)
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def approve_record(
        self,
        *,
        record_id: str,
        actor_user_id: str,
        approval_notes: str | None = None,
    ) -> dict[str, Any]:
        record_id = self._require_text(record_id, "record_id")
        actor_user_id = self._require_text(actor_user_id, "actor_user_id")
        now_ms = int(time.time() * 1000)
        conn = self._conn()
        try:
            conn.execute("BEGIN IMMEDIATE")
            row = self._require_record_row(conn, record_id)
            if str(row["status"]) != "confirmed":
                raise MetrologyServiceError("metrology_record_must_be_confirmed", status_code=409)
            conn.execute(
                """
                UPDATE metrology_records
                SET status = 'approved',
                    approval_notes = ?,
                    approved_by_user_id = ?,
                    approved_at_ms = ?,
                    updated_by_user_id = ?,
                    updated_at_ms = ?
                WHERE record_id = ?
                """,
                (
                    self._optional_text(approval_notes),
                    actor_user_id,
                    now_ms,
                    actor_user_id,
                    now_ms,
                    record_id,
                ),
            )
            if str(row["result_status"]) == "passed":
                conn.execute(
                    """
                    UPDATE equipment_assets
                    SET status = 'in_service',
                        next_metrology_due_date = COALESCE(?, next_metrology_due_date),
                        updated_by_user_id = ?,
                        updated_at_ms = ?
                    WHERE equipment_id = ?
                    """,
                    (
                        str(row["next_due_date"]) if row["next_due_date"] else None,
                        actor_user_id,
                        now_ms,
                        str(row["equipment_id"]),
                    ),
                )
            conn.commit()
            return self.get_record(record_id)
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def dispatch_due_reminders(self, *, actor_user_id: str, window_days: int = 7) -> dict[str, Any]:
        actor_user_id = self._require_text(actor_user_id, "actor_user_id")
        if self._notification_manager is None:
            raise MetrologyServiceError("metrology_notification_manager_unavailable", status_code=500)
        try:
            normalized_window_days = max(1, min(int(window_days or 7), 365))
        except Exception as exc:
            raise MetrologyServiceError("invalid_window_days", status_code=400) from exc
        today = date.today()
        upper_bound = today + timedelta(days=normalized_window_days)
        conn = self._conn()
        try:
            rows = conn.execute(
                """
                SELECT record_id, equipment_id, responsible_user_id, planned_due_date, next_due_date, reminder_sent_for_due_date
                FROM metrology_records
                ORDER BY updated_at_ms DESC, record_id DESC
                """
            ).fetchall()
        finally:
            conn.close()
        items: list[dict[str, Any]] = []
        for row in rows:
            due_date_text = str(row["next_due_date"] or row["planned_due_date"] or "")
            if not due_date_text:
                continue
            due_date = date.fromisoformat(due_date_text)
            if due_date < today or due_date > upper_bound:
                continue
            if str(row["reminder_sent_for_due_date"] or "") == due_date_text:
                continue
            payload = {
                "event_type": "metrology_due_soon",
                "title": f"计量临期提醒：{row['equipment_id']}",
                "body": f"设备 {row['equipment_id']} 的计量节点将于 {due_date_text} 到期，请责任人处理。",
                "recipient_user_ids": [str(row["responsible_user_id"])],
                "link_path": "/quality-system/equipment",
                "resource_type": "metrology_record",
                "resource_id": str(row["record_id"]),
                "due_at_ms": int(time.mktime(due_date.timetuple()) * 1000),
                "meta": {
                    "equipment_id": str(row["equipment_id"]),
                    "due_date": due_date_text,
                },
            }
            jobs = self._notification_manager.notify_event(
                event_type="metrology_due_soon",
                payload=payload,
                recipients=[{"user_id": str(row["responsible_user_id"])}],
                dedupe_key=f"metrology_due_soon:{row['record_id']}:{due_date_text}",
                channel_types=["in_app"],
            )
            now_ms = int(time.time() * 1000)
            update_conn = self._conn()
            try:
                update_conn.execute(
                    """
                    UPDATE metrology_records
                    SET reminder_sent_at_ms = ?, reminder_sent_for_due_date = ?, updated_by_user_id = ?, updated_at_ms = ?
                    WHERE record_id = ? AND COALESCE(reminder_sent_for_due_date, '') != ?
                    """,
                    (now_ms, due_date_text, actor_user_id, now_ms, str(row["record_id"]), due_date_text),
                )
                update_conn.commit()
            finally:
                update_conn.close()
            items.append(
                {
                    "record_id": str(row["record_id"]),
                    "event_type": "metrology_due_soon",
                    "due_date": due_date_text,
                    "job_count": len(jobs),
                }
            )
        return {"count": len(items), "items": items}

    def export_records_csv(self, *, limit: int = 200, equipment_id: str | None = None, status: str | None = None) -> str:
        items = self.list_records(limit=limit, equipment_id=equipment_id, status=status)
        output = io.StringIO()
        writer = csv.DictWriter(
            output,
            fieldnames=[
                "record_id",
                "equipment_id",
                "responsible_user_id",
                "status",
                "planned_due_date",
                "performed_at_ms",
                "result_status",
                "next_due_date",
                "approved_by_user_id",
            ],
        )
        writer.writeheader()
        for item in items:
            writer.writerow({key: item.get(key) for key in writer.fieldnames})
        return output.getvalue()
