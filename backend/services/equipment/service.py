from __future__ import annotations

import csv
import io
import time
from datetime import date, timedelta
from typing import Any
from uuid import uuid4

from backend.database.paths import resolve_auth_db_path
from backend.database.sqlite import connect_sqlite


EQUIPMENT_STATUSES = {
    "purchased",
    "accepted",
    "in_service",
    "under_maintenance",
    "under_metrology",
    "retired",
}

TRANSITIONS = {
    "accept": {"to_status": "accepted", "allowed_from": {"purchased"}, "date_field": "acceptance_date"},
    "commission": {"to_status": "in_service", "allowed_from": {"accepted"}, "date_field": "commissioning_date"},
    "retire": {
        "to_status": "retired",
        "allowed_from": {"purchased", "accepted", "in_service", "under_maintenance", "under_metrology"},
        "date_field": "retired_date",
    },
}


class EquipmentServiceError(Exception):
    def __init__(self, code: str, *, status_code: int = 400):
        super().__init__(code)
        self.code = code
        self.status_code = status_code


class EquipmentService:
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
            raise EquipmentServiceError(f"{field_name}_required", status_code=400)
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
            raise EquipmentServiceError(f"invalid_{field_name}", status_code=400) from exc
        return text

    def _require_asset_row(self, conn, equipment_id: str):
        row = conn.execute(
            """
            SELECT
                equipment_id,
                asset_code,
                equipment_name,
                manufacturer,
                model,
                serial_number,
                location,
                supplier_name,
                owner_user_id,
                status,
                purchase_date,
                acceptance_date,
                commissioning_date,
                retirement_due_date,
                retired_date,
                next_metrology_due_date,
                next_maintenance_due_date,
                notes,
                reminder_sent_at_ms,
                reminder_sent_for_due_date,
                created_by_user_id,
                updated_by_user_id,
                created_at_ms,
                updated_at_ms
            FROM equipment_assets
            WHERE equipment_id = ?
            """,
            (equipment_id,),
        ).fetchone()
        if row is None:
            raise EquipmentServiceError("equipment_asset_not_found", status_code=404)
        return row

    def _list_status_history(self, conn, equipment_id: str) -> list[dict[str, Any]]:
        rows = conn.execute(
            """
            SELECT transition_id, from_status, to_status, action, notes, actor_user_id, created_at_ms
            FROM equipment_asset_status_history
            WHERE equipment_id = ?
            ORDER BY created_at_ms ASC, transition_id ASC
            """,
            (equipment_id,),
        ).fetchall()
        return [
            {
                "transition_id": str(row["transition_id"]),
                "from_status": (str(row["from_status"]) if row["from_status"] else None),
                "to_status": str(row["to_status"]),
                "action": str(row["action"]),
                "notes": (str(row["notes"]) if row["notes"] else None),
                "actor_user_id": str(row["actor_user_id"]),
                "created_at_ms": int(row["created_at_ms"] or 0),
            }
            for row in rows
        ]

    def _serialize_asset(self, conn, row) -> dict[str, Any]:
        equipment_id = str(row["equipment_id"])
        return {
            "equipment_id": equipment_id,
            "asset_code": str(row["asset_code"]),
            "equipment_name": str(row["equipment_name"]),
            "manufacturer": (str(row["manufacturer"]) if row["manufacturer"] else None),
            "model": (str(row["model"]) if row["model"] else None),
            "serial_number": (str(row["serial_number"]) if row["serial_number"] else None),
            "location": (str(row["location"]) if row["location"] else None),
            "supplier_name": (str(row["supplier_name"]) if row["supplier_name"] else None),
            "owner_user_id": str(row["owner_user_id"]),
            "status": str(row["status"]),
            "purchase_date": (str(row["purchase_date"]) if row["purchase_date"] else None),
            "acceptance_date": (str(row["acceptance_date"]) if row["acceptance_date"] else None),
            "commissioning_date": (str(row["commissioning_date"]) if row["commissioning_date"] else None),
            "retirement_due_date": (str(row["retirement_due_date"]) if row["retirement_due_date"] else None),
            "retired_date": (str(row["retired_date"]) if row["retired_date"] else None),
            "next_metrology_due_date": (
                str(row["next_metrology_due_date"]) if row["next_metrology_due_date"] else None
            ),
            "next_maintenance_due_date": (
                str(row["next_maintenance_due_date"]) if row["next_maintenance_due_date"] else None
            ),
            "notes": (str(row["notes"]) if row["notes"] else None),
            "created_by_user_id": str(row["created_by_user_id"]),
            "updated_by_user_id": str(row["updated_by_user_id"]),
            "created_at_ms": int(row["created_at_ms"] or 0),
            "updated_at_ms": int(row["updated_at_ms"] or 0),
            "status_history": self._list_status_history(conn, equipment_id),
        }

    @staticmethod
    def _append_transition(
        conn,
        *,
        equipment_id: str,
        from_status: str | None,
        to_status: str,
        action: str,
        notes: str | None,
        actor_user_id: str,
        now_ms: int,
    ) -> None:
        conn.execute(
            """
            INSERT INTO equipment_asset_status_history (
                transition_id,
                equipment_id,
                from_status,
                to_status,
                action,
                notes,
                actor_user_id,
                created_at_ms
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid4()),
                equipment_id,
                from_status,
                to_status,
                action,
                notes,
                actor_user_id,
                now_ms,
            ),
        )

    def get_asset(self, equipment_id: str) -> dict[str, Any]:
        equipment_id = self._require_text(equipment_id, "equipment_id")
        conn = self._conn()
        try:
            return self._serialize_asset(conn, self._require_asset_row(conn, equipment_id))
        finally:
            conn.close()

    def list_assets(
        self,
        *,
        limit: int = 100,
        status: str | None = None,
        owner_user_id: str | None = None,
    ) -> list[dict[str, Any]]:
        limit = max(1, min(int(limit or 100), 200))
        where = []
        params: list[Any] = []
        if status:
            clean_status = str(status).strip().lower()
            if clean_status not in EQUIPMENT_STATUSES:
                raise EquipmentServiceError("invalid_status", status_code=400)
            where.append("status = ?")
            params.append(clean_status)
        if owner_user_id:
            where.append("owner_user_id = ?")
            params.append(str(owner_user_id).strip())
        where_sql = f"WHERE {' AND '.join(where)}" if where else ""
        conn = self._conn()
        try:
            rows = conn.execute(
                f"""
                SELECT equipment_id
                FROM equipment_assets
                {where_sql}
                ORDER BY updated_at_ms DESC, equipment_id DESC
                LIMIT ?
                """,
                [*params, limit],
            ).fetchall()
            return [self._serialize_asset(conn, self._require_asset_row(conn, str(row["equipment_id"]))) for row in rows]
        finally:
            conn.close()

    def create_asset(
        self,
        *,
        asset_code: str,
        equipment_name: str,
        owner_user_id: str,
        actor_user_id: str,
        manufacturer: str | None = None,
        model: str | None = None,
        serial_number: str | None = None,
        location: str | None = None,
        supplier_name: str | None = None,
        purchase_date: str | None = None,
        retirement_due_date: str | None = None,
        next_metrology_due_date: str | None = None,
        next_maintenance_due_date: str | None = None,
        notes: str | None = None,
    ) -> dict[str, Any]:
        asset_code = self._require_text(asset_code, "asset_code")
        equipment_name = self._require_text(equipment_name, "equipment_name")
        owner_user_id = self._require_text(owner_user_id, "owner_user_id")
        actor_user_id = self._require_text(actor_user_id, "actor_user_id")
        purchase_date = self._optional_iso_date(purchase_date, field_name="purchase_date")
        retirement_due_date = self._optional_iso_date(retirement_due_date, field_name="retirement_due_date")
        next_metrology_due_date = self._optional_iso_date(next_metrology_due_date, field_name="next_metrology_due_date")
        next_maintenance_due_date = self._optional_iso_date(
            next_maintenance_due_date,
            field_name="next_maintenance_due_date",
        )
        now_ms = int(time.time() * 1000)
        equipment_id = str(uuid4())
        conn = self._conn()
        try:
            conn.execute("BEGIN IMMEDIATE")
            duplicate = conn.execute(
                "SELECT equipment_id FROM equipment_assets WHERE asset_code = ?",
                (asset_code,),
            ).fetchone()
            if duplicate is not None:
                raise EquipmentServiceError("equipment_asset_code_conflict", status_code=409)
            conn.execute(
                """
                INSERT INTO equipment_assets (
                    equipment_id,
                    asset_code,
                    equipment_name,
                    manufacturer,
                    model,
                    serial_number,
                    location,
                    supplier_name,
                    owner_user_id,
                    status,
                    purchase_date,
                    retirement_due_date,
                    next_metrology_due_date,
                    next_maintenance_due_date,
                    notes,
                    created_by_user_id,
                    updated_by_user_id,
                    created_at_ms,
                    updated_at_ms
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'purchased', ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    equipment_id,
                    asset_code,
                    equipment_name,
                    self._optional_text(manufacturer),
                    self._optional_text(model),
                    self._optional_text(serial_number),
                    self._optional_text(location),
                    self._optional_text(supplier_name),
                    owner_user_id,
                    purchase_date,
                    retirement_due_date,
                    next_metrology_due_date,
                    next_maintenance_due_date,
                    self._optional_text(notes),
                    actor_user_id,
                    actor_user_id,
                    now_ms,
                    now_ms,
                ),
            )
            self._append_transition(
                conn,
                equipment_id=equipment_id,
                from_status=None,
                to_status="purchased",
                action="create",
                notes=self._optional_text(notes),
                actor_user_id=actor_user_id,
                now_ms=now_ms,
            )
            conn.commit()
            return self.get_asset(equipment_id)
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def transition_status(
        self,
        *,
        equipment_id: str,
        action: str,
        actor_user_id: str,
        status_date: str | None = None,
        notes: str | None = None,
    ) -> dict[str, Any]:
        equipment_id = self._require_text(equipment_id, "equipment_id")
        actor_user_id = self._require_text(actor_user_id, "actor_user_id")
        clean_action = self._require_text(action, "action").lower()
        transition = TRANSITIONS.get(clean_action)
        if transition is None:
            raise EquipmentServiceError("invalid_equipment_action", status_code=400)
        clean_status_date = self._optional_iso_date(status_date, field_name=transition["date_field"])
        now_ms = int(time.time() * 1000)
        conn = self._conn()
        try:
            conn.execute("BEGIN IMMEDIATE")
            row = self._require_asset_row(conn, equipment_id)
            current_status = str(row["status"])
            if current_status not in transition["allowed_from"]:
                raise EquipmentServiceError("equipment_asset_invalid_state", status_code=409)
            conn.execute(
                f"""
                UPDATE equipment_assets
                SET status = ?,
                    {transition["date_field"]} = COALESCE(?, {transition["date_field"]}),
                    updated_by_user_id = ?,
                    updated_at_ms = ?
                WHERE equipment_id = ?
                """,
                (transition["to_status"], clean_status_date, actor_user_id, now_ms, equipment_id),
            )
            self._append_transition(
                conn,
                equipment_id=equipment_id,
                from_status=current_status,
                to_status=transition["to_status"],
                action=clean_action,
                notes=self._optional_text(notes),
                actor_user_id=actor_user_id,
                now_ms=now_ms,
            )
            conn.commit()
            return self.get_asset(equipment_id)
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def mark_status_from_domain(
        self,
        *,
        equipment_id: str,
        status: str,
        actor_user_id: str,
        action: str,
        notes: str | None = None,
    ) -> dict[str, Any]:
        equipment_id = self._require_text(equipment_id, "equipment_id")
        actor_user_id = self._require_text(actor_user_id, "actor_user_id")
        next_status = self._require_text(status, "status").lower()
        if next_status not in EQUIPMENT_STATUSES:
            raise EquipmentServiceError("invalid_status", status_code=400)
        now_ms = int(time.time() * 1000)
        conn = self._conn()
        try:
            conn.execute("BEGIN IMMEDIATE")
            row = self._require_asset_row(conn, equipment_id)
            if str(row["status"]) == "retired":
                raise EquipmentServiceError("equipment_asset_retired", status_code=409)
            previous_status = str(row["status"])
            conn.execute(
                """
                UPDATE equipment_assets
                SET status = ?, updated_by_user_id = ?, updated_at_ms = ?
                WHERE equipment_id = ?
                """,
                (next_status, actor_user_id, now_ms, equipment_id),
            )
            self._append_transition(
                conn,
                equipment_id=equipment_id,
                from_status=previous_status,
                to_status=next_status,
                action=action,
                notes=self._optional_text(notes),
                actor_user_id=actor_user_id,
                now_ms=now_ms,
            )
            conn.commit()
            return self.get_asset(equipment_id)
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def update_due_dates(
        self,
        *,
        equipment_id: str,
        actor_user_id: str,
        next_metrology_due_date: str | None = None,
        next_maintenance_due_date: str | None = None,
    ) -> dict[str, Any]:
        equipment_id = self._require_text(equipment_id, "equipment_id")
        actor_user_id = self._require_text(actor_user_id, "actor_user_id")
        metrology_due = self._optional_iso_date(next_metrology_due_date, field_name="next_metrology_due_date")
        maintenance_due = self._optional_iso_date(next_maintenance_due_date, field_name="next_maintenance_due_date")
        now_ms = int(time.time() * 1000)
        conn = self._conn()
        try:
            conn.execute("BEGIN IMMEDIATE")
            self._require_asset_row(conn, equipment_id)
            conn.execute(
                """
                UPDATE equipment_assets
                SET next_metrology_due_date = COALESCE(?, next_metrology_due_date),
                    next_maintenance_due_date = COALESCE(?, next_maintenance_due_date),
                    updated_by_user_id = ?,
                    updated_at_ms = ?
                WHERE equipment_id = ?
                """,
                (metrology_due, maintenance_due, actor_user_id, now_ms, equipment_id),
            )
            conn.commit()
            return self.get_asset(equipment_id)
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def dispatch_due_reminders(self, *, actor_user_id: str, window_days: int = 7) -> dict[str, Any]:
        actor_user_id = self._require_text(actor_user_id, "actor_user_id")
        if self._notification_manager is None:
            raise EquipmentServiceError("equipment_notification_manager_unavailable", status_code=500)
        try:
            normalized_window_days = max(1, min(int(window_days or 7), 365))
        except Exception as exc:
            raise EquipmentServiceError("invalid_window_days", status_code=400) from exc
        today = date.today()
        upper_bound = today + timedelta(days=normalized_window_days)
        conn = self._conn()
        try:
            rows = conn.execute(
                """
                SELECT equipment_id, equipment_name, owner_user_id, retirement_due_date, reminder_sent_for_due_date
                FROM equipment_assets
                WHERE status != 'retired' AND retirement_due_date IS NOT NULL
                ORDER BY retirement_due_date ASC, equipment_id ASC
                """
            ).fetchall()
        finally:
            conn.close()
        items: list[dict[str, Any]] = []
        for row in rows:
            due_date = date.fromisoformat(str(row["retirement_due_date"]))
            if due_date < today or due_date > upper_bound:
                continue
            due_date_text = str(row["retirement_due_date"])
            if str(row["reminder_sent_for_due_date"] or "") == due_date_text:
                continue
            payload = {
                "event_type": "equipment_due_soon",
                "title": f"设备临期提醒：{row['equipment_name']}",
                "body": f"设备 {row['equipment_name']} 将于 {due_date_text} 到达报废节点，请责任人确认处理。",
                "recipient_user_ids": [str(row["owner_user_id"])],
                "link_path": "/quality-system/equipment",
                "resource_type": "equipment_asset",
                "resource_id": str(row["equipment_id"]),
                "due_at_ms": int(time.mktime(due_date.timetuple()) * 1000),
                "meta": {
                    "equipment_id": str(row["equipment_id"]),
                    "retirement_due_date": due_date_text,
                },
            }
            jobs = self._notification_manager.notify_event(
                event_type="equipment_due_soon",
                payload=payload,
                recipients=[{"user_id": str(row["owner_user_id"])}],
                dedupe_key=f"equipment_due_soon:{row['equipment_id']}:{due_date_text}",
                channel_types=["in_app"],
            )
            now_ms = int(time.time() * 1000)
            update_conn = self._conn()
            try:
                update_conn.execute(
                    """
                    UPDATE equipment_assets
                    SET reminder_sent_at_ms = ?, reminder_sent_for_due_date = ?, updated_by_user_id = ?, updated_at_ms = ?
                    WHERE equipment_id = ? AND COALESCE(reminder_sent_for_due_date, '') != ?
                    """,
                    (now_ms, due_date_text, actor_user_id, now_ms, str(row["equipment_id"]), due_date_text),
                )
                update_conn.commit()
            finally:
                update_conn.close()
            items.append(
                {
                    "equipment_id": str(row["equipment_id"]),
                    "event_type": "equipment_due_soon",
                    "due_date": due_date_text,
                    "job_count": len(jobs),
                }
            )
        return {"count": len(items), "items": items}

    def export_assets_csv(self, *, limit: int = 200, status: str | None = None) -> str:
        items = self.list_assets(limit=limit, status=status)
        output = io.StringIO()
        writer = csv.DictWriter(
            output,
            fieldnames=[
                "equipment_id",
                "asset_code",
                "equipment_name",
                "status",
                "owner_user_id",
                "location",
                "purchase_date",
                "acceptance_date",
                "commissioning_date",
                "retirement_due_date",
                "retired_date",
                "next_metrology_due_date",
                "next_maintenance_due_date",
            ],
        )
        writer.writeheader()
        for item in items:
            writer.writerow({key: item.get(key) for key in writer.fieldnames})
        return output.getvalue()
