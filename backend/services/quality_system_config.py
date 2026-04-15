from __future__ import annotations

import json
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from backend.database.paths import resolve_auth_db_path
from backend.database.sqlite import connect_sqlite
from backend.services.audit_helpers import actor_fields_from_user


_KEY_FILE_CATEGORY = "\u6587\u4ef6\u5c0f\u7c7b"
_KEY_COMPILER = "\u7f16\u5236"
_KEY_SIGNOFF = "\u5ba1\u6838\u4f1a\u7b7e"
_KEY_APPROVER = "\u6279\u51c6"


class QualitySystemConfigError(Exception):
    def __init__(self, code: str, *, status_code: int = 400) -> None:
        super().__init__(code)
        self.code = code
        self.status_code = status_code


class QualitySystemConfigService:
    def __init__(
        self,
        *,
        db_path: str | Path | None,
        user_store: Any,
        org_structure_manager: Any,
        audit_log_manager: Any | None,
        json_path: str | Path | None = None,
    ) -> None:
        self._db_path = resolve_auth_db_path(db_path)
        self._user_store = user_store
        self._org_structure_manager = org_structure_manager
        self._audit_log_manager = audit_log_manager
        self._audit_actor_deps = SimpleNamespace(org_structure_manager=org_structure_manager)
        self._json_path = Path(json_path) if json_path is not None else Path(__file__).resolve().parents[2] / "docs" / "generated" / "document-approval-matrix.json"

    def get_config(self) -> dict[str, Any]:
        conn = connect_sqlite(self._db_path)
        try:
            self._ensure_seeded(conn)
            return {
                "positions": self._list_positions(conn),
                "file_categories": self._list_file_categories(conn, active_only=True),
            }
        finally:
            conn.close()

    def search_assignable_users(self, *, q: str | None = None, limit: int = 20) -> list[dict[str, Any]]:
        keyword = str(q or "").strip()
        lim = max(1, min(int(limit or 20), 100))
        conn = connect_sqlite(self._db_path)
        try:
            query = """
                SELECT user_id, username, full_name, employee_user_id, status, company_id, department_id
                FROM users
                WHERE status = 'active'
                  AND employee_user_id IS NOT NULL
                  AND TRIM(employee_user_id) <> ''
            """
            params: list[Any] = []
            if keyword:
                like = f"%{keyword}%"
                query += """
                  AND (
                    username LIKE ?
                    OR COALESCE(full_name, '') LIKE ?
                    OR employee_user_id LIKE ?
                    OR COALESCE(email, '') LIKE ?
                  )
                """
                params.extend([like, like, like, like])
            query += """
                ORDER BY
                  CASE WHEN TRIM(COALESCE(full_name, '')) <> '' THEN full_name ELSE username END COLLATE NOCASE ASC,
                  username COLLATE NOCASE ASC,
                  user_id ASC
                LIMIT ?
            """
            params.append(lim)
            rows = conn.execute(query, params).fetchall()
            return [self._row_to_user_summary(row) for row in rows]
        finally:
            conn.close()

    def update_position_assignments(
        self,
        *,
        position_id: int,
        user_ids: list[str],
        change_reason: str,
        actor_user: Any,
    ) -> dict[str, Any]:
        reason = str(change_reason or "").strip()
        if not reason:
            raise QualitySystemConfigError("quality_system_config_change_reason_required")

        normalized_user_ids = self._normalize_user_ids(user_ids)
        conn = connect_sqlite(self._db_path)
        try:
            self._ensure_seeded(conn)
            position = conn.execute(
                """
                SELECT id, name, in_signoff, in_compiler, in_approver, seeded_from_json
                FROM quality_system_positions
                WHERE id = ?
                """,
                (int(position_id),),
            ).fetchone()
            if not position:
                raise QualitySystemConfigError("quality_system_config_position_not_found", status_code=404)

            before_users = self._list_assigned_users_for_position(conn, int(position_id))
            validated_users = self._validate_assignable_user_ids(conn, normalized_user_ids)

            now_ms = self._now_ms()
            conn.execute(
                "DELETE FROM quality_system_position_assignments WHERE position_id = ?",
                (int(position_id),),
            )
            if validated_users:
                conn.executemany(
                    """
                    INSERT INTO quality_system_position_assignments (
                        position_id, user_id, created_at_ms, updated_at_ms
                    )
                    VALUES (?, ?, ?, ?)
                    """,
                    [
                        (int(position_id), item["user_id"], now_ms, now_ms)
                        for item in validated_users
                    ],
                )
            conn.commit()

            after_users = self._list_assigned_users_for_position(conn, int(position_id))
            self._log_record_change(
                actor_user=actor_user,
                action="quality_system_position_assignments_update",
                resource_type="quality_system_position_assignment",
                resource_id=str(position["name"]),
                reason=reason,
                before={
                    "position_id": int(position["id"]),
                    "position_name": str(position["name"]),
                    "assigned_users": before_users,
                },
                after={
                    "position_id": int(position["id"]),
                    "position_name": str(position["name"]),
                    "assigned_users": after_users,
                },
                meta={
                    "position_id": int(position["id"]),
                    "position_name": str(position["name"]),
                    "assigned_user_count": len(after_users),
                },
            )
            return self._build_position_response(position, after_users)
        finally:
            conn.close()

    def create_file_category(
        self,
        *,
        name: str,
        change_reason: str,
        actor_user: Any,
    ) -> dict[str, Any]:
        clean_name = str(name or "").strip()
        reason = str(change_reason or "").strip()
        if not clean_name:
            raise QualitySystemConfigError("quality_system_config_file_category_name_required")
        if not reason:
            raise QualitySystemConfigError("quality_system_config_change_reason_required")

        conn = connect_sqlite(self._db_path)
        try:
            self._ensure_seeded(conn)
            existing = conn.execute(
                """
                SELECT id, name, seeded_from_json, is_active
                FROM quality_system_file_categories
                WHERE name = ?
                """,
                (clean_name,),
            ).fetchone()

            now_ms = self._now_ms()
            before = None
            if existing and int(existing["is_active"] or 0) == 1:
                raise QualitySystemConfigError("quality_system_config_file_category_exists")
            if existing:
                before = self._build_file_category_response(existing)
                conn.execute(
                    """
                    UPDATE quality_system_file_categories
                    SET is_active = 1, updated_at_ms = ?
                    WHERE id = ?
                    """,
                    (now_ms, int(existing["id"])),
                )
                category_id = int(existing["id"])
            else:
                cursor = conn.execute(
                    """
                    INSERT INTO quality_system_file_categories (
                        name, seeded_from_json, is_active, created_at_ms, updated_at_ms
                    )
                    VALUES (?, 0, 1, ?, ?)
                    """,
                    (clean_name, now_ms, now_ms),
                )
                category_id = int(cursor.lastrowid)
            conn.commit()

            row = conn.execute(
                """
                SELECT id, name, seeded_from_json, is_active
                FROM quality_system_file_categories
                WHERE id = ?
                """,
                (category_id,),
            ).fetchone()
            after = self._build_file_category_response(row)
            self._log_record_change(
                actor_user=actor_user,
                action="quality_system_file_category_create",
                resource_type="quality_system_file_category",
                resource_id=clean_name,
                reason=reason,
                before=before,
                after=after,
                meta={"file_category_id": category_id, "file_category_name": clean_name},
            )
            return after
        finally:
            conn.close()

    def deactivate_file_category(
        self,
        *,
        category_id: int,
        change_reason: str,
        actor_user: Any,
    ) -> dict[str, Any]:
        reason = str(change_reason or "").strip()
        if not reason:
            raise QualitySystemConfigError("quality_system_config_change_reason_required")

        conn = connect_sqlite(self._db_path)
        try:
            self._ensure_seeded(conn)
            row = conn.execute(
                """
                SELECT id, name, seeded_from_json, is_active
                FROM quality_system_file_categories
                WHERE id = ?
                """,
                (int(category_id),),
            ).fetchone()
            if not row:
                raise QualitySystemConfigError("quality_system_config_file_category_not_found", status_code=404)

            before = self._build_file_category_response(row)
            if int(row["is_active"] or 0) == 1:
                conn.execute(
                    """
                    UPDATE quality_system_file_categories
                    SET is_active = 0, updated_at_ms = ?
                    WHERE id = ?
                    """,
                    (self._now_ms(), int(category_id)),
                )
                conn.commit()
            refreshed = conn.execute(
                """
                SELECT id, name, seeded_from_json, is_active
                FROM quality_system_file_categories
                WHERE id = ?
                """,
                (int(category_id),),
            ).fetchone()
            after = self._build_file_category_response(refreshed)
            self._log_record_change(
                actor_user=actor_user,
                action="quality_system_file_category_deactivate",
                resource_type="quality_system_file_category",
                resource_id=str(row["name"]),
                reason=reason,
                before=before,
                after=after,
                meta={"file_category_id": int(row["id"]), "file_category_name": str(row["name"])},
            )
            return after
        finally:
            conn.close()

    def _ensure_seeded(self, conn) -> None:
        position_count = int(
            conn.execute("SELECT COUNT(*) FROM quality_system_positions").fetchone()[0]
        )
        file_category_count = int(
            conn.execute("SELECT COUNT(*) FROM quality_system_file_categories").fetchone()[0]
        )
        if position_count > 0 and file_category_count > 0:
            return

        seed_data = self._load_seed_data()
        now_ms = self._now_ms()

        if position_count == 0:
            conn.executemany(
                """
                INSERT INTO quality_system_positions (
                    name, in_signoff, in_compiler, in_approver, seeded_from_json, created_at_ms, updated_at_ms
                )
                VALUES (?, ?, ?, ?, 1, ?, ?)
                """,
                [
                    (
                        item["name"],
                        1 if item["in_signoff"] else 0,
                        1 if item["in_compiler"] else 0,
                        1 if item["in_approver"] else 0,
                        now_ms,
                        now_ms,
                    )
                    for item in seed_data["positions"]
                ],
            )

        if file_category_count == 0:
            conn.executemany(
                """
                INSERT INTO quality_system_file_categories (
                    name, seeded_from_json, is_active, created_at_ms, updated_at_ms
                )
                VALUES (?, 1, 1, ?, ?)
                """,
                [
                    (name, now_ms, now_ms)
                    for name in seed_data["file_categories"]
                ],
            )

        conn.commit()

    def _load_seed_data(self) -> dict[str, Any]:
        if not self._json_path.exists():
            raise QualitySystemConfigError("quality_system_config_seed_missing", status_code=500)
        try:
            payload = json.loads(self._json_path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise QualitySystemConfigError("quality_system_config_seed_invalid", status_code=500) from exc
        if not isinstance(payload, list):
            raise QualitySystemConfigError("quality_system_config_seed_invalid", status_code=500)

        positions: list[dict[str, Any]] = []
        position_index: dict[str, dict[str, Any]] = {}
        file_categories: list[str] = []
        file_category_seen: set[str] = set()

        def register_position(name: Any, field_name: str) -> None:
            clean_name = str(name or "").strip()
            if not clean_name:
                return
            entry = position_index.get(clean_name)
            if entry is None:
                entry = {
                    "name": clean_name,
                    "in_signoff": False,
                    "in_compiler": False,
                    "in_approver": False,
                }
                position_index[clean_name] = entry
                positions.append(entry)
            entry[field_name] = True

        for item in payload:
            if not isinstance(item, dict):
                raise QualitySystemConfigError("quality_system_config_seed_invalid", status_code=500)
            clean_file_category = str(item.get(_KEY_FILE_CATEGORY) or "").strip()
            if clean_file_category and clean_file_category not in file_category_seen:
                file_categories.append(clean_file_category)
                file_category_seen.add(clean_file_category)

            signoff = item.get(_KEY_SIGNOFF)
            if not isinstance(signoff, dict):
                raise QualitySystemConfigError("quality_system_config_seed_invalid", status_code=500)
            for key in signoff.keys():
                register_position(key, "in_signoff")

            register_position(item.get(_KEY_COMPILER), "in_compiler")
            register_position(item.get(_KEY_APPROVER), "in_approver")

        return {
            "positions": positions,
            "file_categories": file_categories,
        }

    def _list_positions(self, conn) -> list[dict[str, Any]]:
        rows = conn.execute(
            """
            SELECT id, name, in_signoff, in_compiler, in_approver, seeded_from_json
            FROM quality_system_positions
            ORDER BY id ASC
            """
        ).fetchall()
        assigned_map: dict[int, list[dict[str, Any]]] = {}
        assignment_rows = conn.execute(
            """
            SELECT
                a.position_id,
                a.id AS assignment_id,
                u.user_id,
                u.username,
                u.full_name,
                u.employee_user_id,
                u.status,
                u.company_id,
                u.department_id
            FROM quality_system_position_assignments a
            JOIN users u ON u.user_id = a.user_id
            ORDER BY a.position_id ASC, a.id ASC
            """
        ).fetchall()
        for row in assignment_rows:
            assigned_map.setdefault(int(row["position_id"]), []).append(self._row_to_user_summary(row))
        return [
            self._build_position_response(row, assigned_map.get(int(row["id"]), []))
            for row in rows
        ]

    def _list_assigned_users_for_position(self, conn, position_id: int) -> list[dict[str, Any]]:
        rows = conn.execute(
            """
            SELECT
                a.id AS assignment_id,
                u.user_id,
                u.username,
                u.full_name,
                u.employee_user_id,
                u.status,
                u.company_id,
                u.department_id
            FROM quality_system_position_assignments a
            JOIN users u ON u.user_id = a.user_id
            WHERE a.position_id = ?
            ORDER BY a.id ASC
            """,
            (int(position_id),),
        ).fetchall()
        return [self._row_to_user_summary(row) for row in rows]

    def _validate_assignable_user_ids(self, conn, user_ids: list[str]) -> list[dict[str, Any]]:
        if not user_ids:
            return []
        placeholders = ",".join("?" for _ in user_ids)
        rows = conn.execute(
            f"""
            SELECT user_id, username, full_name, employee_user_id, status, company_id, department_id
            FROM users
            WHERE user_id IN ({placeholders})
              AND status = 'active'
              AND employee_user_id IS NOT NULL
              AND TRIM(employee_user_id) <> ''
            """,
            user_ids,
        ).fetchall()
        user_map = {str(row["user_id"]): self._row_to_user_summary(row) for row in rows}
        if len(user_map) != len(user_ids):
            missing = [user_id for user_id in user_ids if user_id not in user_map]
            raise QualitySystemConfigError(
                f"quality_system_config_assignable_user_not_found:{','.join(missing)}",
                status_code=404,
            )
        return [user_map[user_id] for user_id in user_ids]

    def _list_file_categories(self, conn, *, active_only: bool) -> list[dict[str, Any]]:
        query = """
            SELECT id, name, seeded_from_json, is_active
            FROM quality_system_file_categories
        """
        params: list[Any] = []
        if active_only:
            query += " WHERE is_active = 1"
        query += " ORDER BY id ASC"
        rows = conn.execute(query, params).fetchall()
        return [self._build_file_category_response(row) for row in rows]

    def _build_position_response(self, row, assigned_users: list[dict[str, Any]]) -> dict[str, Any]:
        return {
            "id": int(row["id"]),
            "name": str(row["name"]),
            "in_signoff": bool(row["in_signoff"]),
            "in_compiler": bool(row["in_compiler"]),
            "in_approver": bool(row["in_approver"]),
            "seeded_from_json": bool(row["seeded_from_json"]),
            "assigned_users": assigned_users,
        }

    @staticmethod
    def _build_file_category_response(row) -> dict[str, Any]:
        return {
            "id": int(row["id"]),
            "name": str(row["name"]),
            "seeded_from_json": bool(row["seeded_from_json"]),
            "is_active": bool(row["is_active"]),
        }

    def _row_to_user_summary(self, row) -> dict[str, Any]:
        company_id = row["company_id"]
        department_id = row["department_id"]
        return {
            "user_id": str(row["user_id"]),
            "username": str(row["username"]),
            "full_name": (str(row["full_name"]).strip() if row["full_name"] else None),
            "employee_user_id": (str(row["employee_user_id"]).strip() if row["employee_user_id"] else None),
            "status": str(row["status"]),
            "company_id": (int(company_id) if company_id is not None else None),
            "company_name": self._company_name(company_id),
            "department_id": (int(department_id) if department_id is not None else None),
            "department_name": self._department_name(department_id),
        }

    def _company_name(self, company_id: Any) -> str | None:
        if company_id is None or self._org_structure_manager is None:
            return None
        try:
            item = self._org_structure_manager.get_company(int(company_id))
        except Exception:
            return None
        return str(getattr(item, "name", "") or "").strip() or None

    def _department_name(self, department_id: Any) -> str | None:
        if department_id is None or self._org_structure_manager is None:
            return None
        try:
            item = self._org_structure_manager.get_department(int(department_id))
        except Exception:
            return None
        return str(getattr(item, "path_name", None) or getattr(item, "name", "") or "").strip() or None

    @staticmethod
    def _normalize_user_ids(user_ids: list[str]) -> list[str]:
        normalized: list[str] = []
        seen: set[str] = set()
        for raw in user_ids or []:
            clean = str(raw or "").strip()
            if not clean or clean in seen:
                continue
            seen.add(clean)
            normalized.append(clean)
        return normalized

    def _log_record_change(
        self,
        *,
        actor_user: Any,
        action: str,
        resource_type: str,
        resource_id: str,
        reason: str,
        before: Any,
        after: Any,
        meta: dict[str, Any] | None = None,
    ) -> None:
        if self._audit_log_manager is None or actor_user is None:
            return
        self._audit_log_manager.log_event(
            action=action,
            actor=str(getattr(actor_user, "user_id", "") or ""),
            source="quality_system_config",
            resource_type=resource_type,
            resource_id=resource_id,
            event_type="config_change",
            before=before,
            after=after,
            reason=reason,
            meta=meta or {},
            **actor_fields_from_user(self._audit_actor_deps, actor_user),
        )

    @staticmethod
    def _now_ms() -> int:
        return int(time.time() * 1000)
