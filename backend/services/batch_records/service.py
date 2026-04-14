from __future__ import annotations

import base64
import hashlib
import json
import time
from typing import Any
from uuid import uuid4

from backend.database.paths import resolve_auth_db_path
from backend.database.sqlite import connect_sqlite


TEMPLATE_STATUSES = {"draft", "active", "obsolete"}
EXECUTION_STATUSES = {"in_progress", "signed", "reviewed"}
MAX_STEP_PHOTO_EVIDENCE_COUNT = 5
MAX_STEP_PHOTO_EVIDENCE_BYTES = 2_500_000


class BatchRecordsServiceError(Exception):
    def __init__(self, code: str, *, status_code: int = 400):
        super().__init__(code)
        self.code = code
        self.status_code = status_code


def _now_ms() -> int:
    return int(time.time() * 1000)


def _to_json(value: Any, *, field_name: str) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    except Exception as exc:
        raise BatchRecordsServiceError(f"{field_name}_invalid_json", status_code=400) from exc


def _from_json(text: str, *, field_name: str) -> Any:
    try:
        return json.loads(text)
    except Exception as exc:
        raise BatchRecordsServiceError(f"{field_name}_invalid_json", status_code=500) from exc


def _require_text(value: Any, *, field_name: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise BatchRecordsServiceError(f"{field_name}_required", status_code=400)
    return text


def _optional_text(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def _require_step_definitions(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not value:
        raise BatchRecordsServiceError("template_steps_required", status_code=400)
    steps: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in value:
        if not isinstance(raw, dict):
            raise BatchRecordsServiceError("template_steps_invalid", status_code=400)
        key = _require_text(raw.get("key"), field_name="step_key")
        if key in seen:
            raise BatchRecordsServiceError("template_steps_duplicate_key", status_code=400)
        seen.add(key)
        steps.append(
            {
                "key": key,
                "title": _optional_text(raw.get("title")),
                "fields": raw.get("fields") if isinstance(raw.get("fields"), list) else [],
                "meta": raw.get("meta") if isinstance(raw.get("meta"), dict) else {},
            }
        )
    return steps


def _extract_step_keys(template_steps: list[dict[str, Any]]) -> set[str]:
    keys: set[str] = set()
    for step in template_steps:
        key = str(step.get("key") or "").strip()
        if key:
            keys.add(key)
    return keys


def _normalize_photo_evidence_item(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise BatchRecordsServiceError("step_photo_evidence_invalid", status_code=400)
    filename = _require_text(value.get("filename"), field_name="step_photo_filename")
    media_type = _require_text(value.get("media_type"), field_name="step_photo_media_type")
    data_url = _require_text(value.get("data_url"), field_name="step_photo_data_url")
    if not media_type.startswith("image/"):
        raise BatchRecordsServiceError("step_photo_media_type_invalid", status_code=400)
    prefix = f"data:{media_type};base64,"
    if not data_url.startswith(prefix):
        raise BatchRecordsServiceError("step_photo_data_url_invalid", status_code=400)
    encoded = data_url[len(prefix) :]
    try:
        raw = base64.b64decode(encoded, validate=True)
    except Exception as exc:
        raise BatchRecordsServiceError("step_photo_data_url_invalid", status_code=400) from exc
    if not raw:
        raise BatchRecordsServiceError("step_photo_empty", status_code=400)
    if len(raw) > MAX_STEP_PHOTO_EVIDENCE_BYTES:
        raise BatchRecordsServiceError("step_photo_too_large", status_code=400)
    captured_at_ms = value.get("captured_at_ms")
    normalized_captured_at_ms = None
    if captured_at_ms is not None:
        try:
            normalized_captured_at_ms = int(captured_at_ms)
        except Exception as exc:
            raise BatchRecordsServiceError("step_photo_captured_at_invalid", status_code=400) from exc
    return {
        "filename": filename,
        "media_type": media_type,
        "data_url": data_url,
        "captured_at_ms": normalized_captured_at_ms,
        "size_bytes": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
    }


def _normalize_step_payload(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise BatchRecordsServiceError("step_payload_invalid", status_code=400)
    normalized = dict(payload)
    photo_evidences = normalized.get("photo_evidences")
    if photo_evidences is None:
        return normalized
    if not isinstance(photo_evidences, list):
        raise BatchRecordsServiceError("step_photo_evidences_invalid", status_code=400)
    if len(photo_evidences) > MAX_STEP_PHOTO_EVIDENCE_COUNT:
        raise BatchRecordsServiceError("step_photo_evidences_too_many", status_code=400)
    normalized["photo_evidences"] = [
        _normalize_photo_evidence_item(item) for item in photo_evidences
    ]
    return normalized


class BatchRecordsService:
    def __init__(self, *, db_path: str | None = None):
        self.db_path = resolve_auth_db_path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def _conn(self):
        return connect_sqlite(self.db_path)

    @staticmethod
    def _template_row_to_dict(row) -> dict[str, Any]:
        return {
            "template_id": row["template_id"],
            "template_code": row["template_code"],
            "template_name": row["template_name"],
            "version_no": int(row["version_no"]),
            "status": row["status"],
            "steps": _from_json(str(row["steps_json"] or "[]"), field_name="template_steps"),
            "meta": _from_json(str(row["meta_json"] or "{}"), field_name="template_meta"),
            "created_by_user_id": row["created_by_user_id"],
            "created_at_ms": int(row["created_at_ms"]),
            "updated_at_ms": int(row["updated_at_ms"]),
        }

    @staticmethod
    def _execution_row_to_dict(row) -> dict[str, Any]:
        return {
            "execution_id": row["execution_id"],
            "template_id": row["template_id"],
            "template_code": row["template_code"],
            "template_version_no": int(row["template_version_no"]),
            "title": row["title"],
            "batch_no": row["batch_no"],
            "status": row["status"],
            "started_at_ms": int(row["started_at_ms"]),
            "completed_at_ms": int(row["completed_at_ms"]) if row["completed_at_ms"] is not None else None,
            "signed_signature_id": row["signed_signature_id"],
            "reviewed_signature_id": row["reviewed_signature_id"],
            "created_by_user_id": row["created_by_user_id"],
            "updated_by_user_id": row["updated_by_user_id"],
            "created_at_ms": int(row["created_at_ms"]),
            "updated_at_ms": int(row["updated_at_ms"]),
        }

    @staticmethod
    def _entry_row_to_dict(row) -> dict[str, Any]:
        return {
            "entry_id": row["entry_id"],
            "execution_id": row["execution_id"],
            "step_key": row["step_key"],
            "payload": _from_json(str(row["payload_json"] or "{}"), field_name="step_payload"),
            "created_by_user_id": row["created_by_user_id"],
            "created_by_username": row["created_by_username"],
            "created_at_ms": int(row["created_at_ms"]),
        }

    def get_template(self, *, template_id: str) -> dict[str, Any]:
        clean_id = _require_text(template_id, field_name="template_id")
        conn = self._conn()
        try:
            row = conn.execute(
                "SELECT * FROM batch_record_templates WHERE template_id = ?",
                (clean_id,),
            ).fetchone()
            if row is None:
                raise BatchRecordsServiceError("batch_record_template_not_found", status_code=404)
            return self._template_row_to_dict(row)
        finally:
            conn.close()

    def list_templates(
        self,
        *,
        include_versions: bool = False,
        include_obsolete: bool = False,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        lim = max(1, min(int(limit), 500))
        conn = self._conn()
        try:
            where = " WHERE 1=1"
            params: list[Any] = []
            if not include_obsolete:
                where += " AND status != 'obsolete'"

            if include_versions:
                rows = conn.execute(
                    f"""
                    SELECT *
                    FROM batch_record_templates
                    {where}
                    ORDER BY template_code ASC, version_no DESC
                    LIMIT ?
                    """,
                    [*params, lim],
                ).fetchall()
                return [self._template_row_to_dict(row) for row in rows]

            rows = conn.execute(
                f"""
                SELECT t.*
                FROM batch_record_templates t
                JOIN (
                    SELECT template_code, MAX(version_no) AS max_version_no
                    FROM batch_record_templates
                    {where}
                    GROUP BY template_code
                ) latest
                ON latest.template_code = t.template_code AND latest.max_version_no = t.version_no
                ORDER BY t.updated_at_ms DESC
                LIMIT ?
                """,
                [*params, lim],
            ).fetchall()
            return [self._template_row_to_dict(row) for row in rows]
        finally:
            conn.close()

    def create_template(
        self,
        *,
        template_code: str,
        template_name: str,
        steps: list[dict[str, Any]],
        meta: dict[str, Any] | None,
        actor_user_id: str,
    ) -> dict[str, Any]:
        code = _require_text(template_code, field_name="template_code")
        name = _require_text(template_name, field_name="template_name")
        actor = _require_text(actor_user_id, field_name="actor_user_id")
        normalized_steps = _require_step_definitions(steps)
        meta_value = meta if isinstance(meta, dict) else {}

        now_ms = _now_ms()
        template_id = str(uuid4())
        conn = self._conn()
        try:
            existing = conn.execute(
                "SELECT 1 FROM batch_record_templates WHERE template_code = ? LIMIT 1",
                (code,),
            ).fetchone()
            if existing is not None:
                raise BatchRecordsServiceError("batch_record_template_code_exists", status_code=409)

            conn.execute(
                """
                INSERT INTO batch_record_templates (
                    template_id,
                    template_code,
                    template_name,
                    version_no,
                    status,
                    steps_json,
                    meta_json,
                    created_by_user_id,
                    created_at_ms,
                    updated_at_ms
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    template_id,
                    code,
                    name,
                    1,
                    "draft",
                    _to_json(normalized_steps, field_name="template_steps"),
                    _to_json(meta_value, field_name="template_meta"),
                    actor,
                    now_ms,
                    now_ms,
                ),
            )
            conn.commit()
        finally:
            conn.close()
        return self.get_template(template_id=template_id)

    def create_template_version(
        self,
        *,
        template_code: str,
        template_name: str,
        steps: list[dict[str, Any]],
        meta: dict[str, Any] | None,
        actor_user_id: str,
    ) -> dict[str, Any]:
        code = _require_text(template_code, field_name="template_code")
        name = _require_text(template_name, field_name="template_name")
        actor = _require_text(actor_user_id, field_name="actor_user_id")
        normalized_steps = _require_step_definitions(steps)
        meta_value = meta if isinstance(meta, dict) else {}

        now_ms = _now_ms()
        template_id = str(uuid4())
        conn = self._conn()
        try:
            row = conn.execute(
                "SELECT MAX(version_no) AS max_version_no FROM batch_record_templates WHERE template_code = ?",
                (code,),
            ).fetchone()
            max_version = int(row["max_version_no"]) if row and row["max_version_no"] is not None else None
            if max_version is None:
                raise BatchRecordsServiceError("batch_record_template_not_found", status_code=404)
            next_version = max_version + 1
            conn.execute(
                """
                INSERT INTO batch_record_templates (
                    template_id,
                    template_code,
                    template_name,
                    version_no,
                    status,
                    steps_json,
                    meta_json,
                    created_by_user_id,
                    created_at_ms,
                    updated_at_ms
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    template_id,
                    code,
                    name,
                    next_version,
                    "draft",
                    _to_json(normalized_steps, field_name="template_steps"),
                    _to_json(meta_value, field_name="template_meta"),
                    actor,
                    now_ms,
                    now_ms,
                ),
            )
            conn.commit()
        finally:
            conn.close()
        return self.get_template(template_id=template_id)

    def publish_template(self, *, template_id: str, actor_user_id: str) -> dict[str, Any]:
        clean_id = _require_text(template_id, field_name="template_id")
        actor = _require_text(actor_user_id, field_name="actor_user_id")
        now_ms = _now_ms()
        conn = self._conn()
        try:
            row = conn.execute(
                "SELECT * FROM batch_record_templates WHERE template_id = ?",
                (clean_id,),
            ).fetchone()
            if row is None:
                raise BatchRecordsServiceError("batch_record_template_not_found", status_code=404)
            existing_status = str(row["status"] or "").strip()
            if existing_status == "obsolete":
                raise BatchRecordsServiceError("batch_record_template_obsolete", status_code=409)
            if existing_status == "active":
                return self._template_row_to_dict(row)
            code = str(row["template_code"] or "")
            conn.execute(
                """
                UPDATE batch_record_templates
                SET status = 'obsolete', updated_at_ms = ?
                WHERE template_code = ? AND status = 'active' AND template_id != ?
                """,
                (now_ms, code, clean_id),
            )
            conn.execute(
                """
                UPDATE batch_record_templates
                SET status = 'active', updated_at_ms = ?
                WHERE template_id = ?
                """,
                (now_ms, clean_id),
            )
            conn.commit()
        finally:
            conn.close()
        return self.get_template(template_id=clean_id)

    def get_execution(self, *, execution_id: str) -> dict[str, Any]:
        clean_id = _require_text(execution_id, field_name="execution_id")
        conn = self._conn()
        try:
            execution_row = conn.execute(
                "SELECT * FROM batch_record_executions WHERE execution_id = ?",
                (clean_id,),
            ).fetchone()
            if execution_row is None:
                raise BatchRecordsServiceError("batch_record_execution_not_found", status_code=404)
            execution = self._execution_row_to_dict(execution_row)
            template_row = conn.execute(
                "SELECT * FROM batch_record_templates WHERE template_id = ?",
                (execution["template_id"],),
            ).fetchone()
            template = self._template_row_to_dict(template_row) if template_row is not None else None
            entry_rows = conn.execute(
                """
                SELECT *
                FROM batch_record_step_entries
                WHERE execution_id = ?
                ORDER BY created_at_ms ASC, entry_id ASC
                """,
                (clean_id,),
            ).fetchall()
            entries = [self._entry_row_to_dict(row) for row in entry_rows]
        finally:
            conn.close()

        latest_steps: dict[str, dict[str, Any]] = {}
        for entry in entries:
            latest_steps[entry["step_key"]] = entry

        return {
            "execution": execution,
            "template": template,
            "step_entries": entries,
            "latest_steps": latest_steps,
        }

    def list_executions(
        self,
        *,
        status: str | None = None,
        template_code: str | None = None,
        batch_no: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        lim = max(1, min(int(limit), 500))
        where = " WHERE 1=1"
        params: list[Any] = []

        if status is not None:
            clean_status = str(status or "").strip()
            if clean_status and clean_status not in EXECUTION_STATUSES:
                raise BatchRecordsServiceError("batch_record_execution_status_invalid", status_code=400)
            if clean_status:
                where += " AND status = ?"
                params.append(clean_status)

        clean_code = _optional_text(template_code)
        if clean_code:
            where += " AND template_code = ?"
            params.append(clean_code)

        clean_batch = _optional_text(batch_no)
        if clean_batch:
            where += " AND batch_no = ?"
            params.append(clean_batch)

        conn = self._conn()
        try:
            rows = conn.execute(
                f"""
                SELECT *
                FROM batch_record_executions
                {where}
                ORDER BY updated_at_ms DESC
                LIMIT ?
                """,
                [*params, lim],
            ).fetchall()
            return [self._execution_row_to_dict(row) for row in rows]
        finally:
            conn.close()

    def create_execution(
        self,
        *,
        template_id: str,
        batch_no: str,
        title: str | None,
        actor_user_id: str,
    ) -> dict[str, Any]:
        clean_template_id = _require_text(template_id, field_name="template_id")
        clean_batch_no = _require_text(batch_no, field_name="batch_no")
        actor = _require_text(actor_user_id, field_name="actor_user_id")
        conn = self._conn()
        try:
            template_row = conn.execute(
                "SELECT * FROM batch_record_templates WHERE template_id = ?",
                (clean_template_id,),
            ).fetchone()
            if template_row is None:
                raise BatchRecordsServiceError("batch_record_template_not_found", status_code=404)
            template = self._template_row_to_dict(template_row)
            if template["status"] != "active":
                raise BatchRecordsServiceError("batch_record_template_not_active", status_code=409)

            execution_id = str(uuid4())
            now_ms = _now_ms()
            title_value = _optional_text(title) or f"{template['template_name']} - {clean_batch_no}"

            conn.execute(
                """
                INSERT INTO batch_record_executions (
                    execution_id,
                    template_id,
                    template_code,
                    template_version_no,
                    title,
                    batch_no,
                    status,
                    started_at_ms,
                    completed_at_ms,
                    signed_signature_id,
                    reviewed_signature_id,
                    created_by_user_id,
                    updated_by_user_id,
                    created_at_ms,
                    updated_at_ms
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    execution_id,
                    clean_template_id,
                    template["template_code"],
                    int(template["version_no"]),
                    title_value,
                    clean_batch_no,
                    "in_progress",
                    now_ms,
                    None,
                    None,
                    None,
                    actor,
                    actor,
                    now_ms,
                    now_ms,
                ),
            )
            conn.commit()
        finally:
            conn.close()
        return self.get_execution(execution_id=execution_id)

    def write_step_entry(
        self,
        *,
        execution_id: str,
        step_key: str,
        payload: dict[str, Any],
        actor_user_id: str,
        actor_username: str,
    ) -> dict[str, Any]:
        clean_execution_id = _require_text(execution_id, field_name="execution_id")
        clean_step_key = _require_text(step_key, field_name="step_key")
        actor = _require_text(actor_user_id, field_name="actor_user_id")
        username = _require_text(actor_username, field_name="actor_username")
        normalized_payload = _normalize_step_payload(payload)

        now_ms = _now_ms()
        entry_id = str(uuid4())
        conn = self._conn()
        try:
            execution_row = conn.execute(
                "SELECT * FROM batch_record_executions WHERE execution_id = ?",
                (clean_execution_id,),
            ).fetchone()
            if execution_row is None:
                raise BatchRecordsServiceError("batch_record_execution_not_found", status_code=404)
            execution = self._execution_row_to_dict(execution_row)
            if execution["status"] != "in_progress":
                raise BatchRecordsServiceError("batch_record_execution_not_editable", status_code=409)

            template_row = conn.execute(
                "SELECT steps_json FROM batch_record_templates WHERE template_id = ?",
                (execution["template_id"],),
            ).fetchone()
            if template_row is None:
                raise BatchRecordsServiceError("batch_record_template_not_found", status_code=404)
            template_steps = _from_json(str(template_row["steps_json"] or "[]"), field_name="template_steps")
            if not isinstance(template_steps, list):
                raise BatchRecordsServiceError("template_steps_invalid", status_code=500)
            valid_step_keys = _extract_step_keys([s for s in template_steps if isinstance(s, dict)])
            if clean_step_key not in valid_step_keys:
                raise BatchRecordsServiceError("batch_record_step_key_unknown", status_code=400)

            conn.execute(
                """
                INSERT INTO batch_record_step_entries (
                    entry_id,
                    execution_id,
                    step_key,
                    payload_json,
                    created_by_user_id,
                    created_by_username,
                    created_at_ms
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    entry_id,
                    clean_execution_id,
                    clean_step_key,
                    _to_json(normalized_payload, field_name="step_payload"),
                    actor,
                    username,
                    now_ms,
                ),
            )
            conn.execute(
                """
                UPDATE batch_record_executions
                SET updated_by_user_id = ?, updated_at_ms = ?
                WHERE execution_id = ?
                """,
                (actor, now_ms, clean_execution_id),
            )
            conn.commit()
        finally:
            conn.close()
        return {
            "entry_id": entry_id,
            "execution_id": clean_execution_id,
            "step_key": clean_step_key,
            "created_at_ms": now_ms,
        }

    def set_execution_signed(
        self,
        *,
        execution_id: str,
        signature_id: str,
        actor_user_id: str,
    ) -> dict[str, Any]:
        clean_execution_id = _require_text(execution_id, field_name="execution_id")
        clean_signature_id = _require_text(signature_id, field_name="signature_id")
        actor = _require_text(actor_user_id, field_name="actor_user_id")

        now_ms = _now_ms()
        conn = self._conn()
        try:
            row = conn.execute(
                "SELECT * FROM batch_record_executions WHERE execution_id = ?",
                (clean_execution_id,),
            ).fetchone()
            if row is None:
                raise BatchRecordsServiceError("batch_record_execution_not_found", status_code=404)
            execution = self._execution_row_to_dict(row)
            if execution["status"] != "in_progress":
                raise BatchRecordsServiceError("batch_record_execution_sign_invalid_status", status_code=409)
            if execution["signed_signature_id"]:
                raise BatchRecordsServiceError("batch_record_execution_already_signed", status_code=409)

            conn.execute(
                """
                UPDATE batch_record_executions
                SET status = 'signed',
                    signed_signature_id = ?,
                    updated_by_user_id = ?,
                    updated_at_ms = ?
                WHERE execution_id = ?
                """,
                (clean_signature_id, actor, now_ms, clean_execution_id),
            )
            conn.commit()
        finally:
            conn.close()
        return self.get_execution(execution_id=clean_execution_id)

    def set_execution_reviewed(
        self,
        *,
        execution_id: str,
        signature_id: str,
        actor_user_id: str,
    ) -> dict[str, Any]:
        clean_execution_id = _require_text(execution_id, field_name="execution_id")
        clean_signature_id = _require_text(signature_id, field_name="signature_id")
        actor = _require_text(actor_user_id, field_name="actor_user_id")

        now_ms = _now_ms()
        conn = self._conn()
        try:
            row = conn.execute(
                "SELECT * FROM batch_record_executions WHERE execution_id = ?",
                (clean_execution_id,),
            ).fetchone()
            if row is None:
                raise BatchRecordsServiceError("batch_record_execution_not_found", status_code=404)
            execution = self._execution_row_to_dict(row)
            if execution["status"] != "signed":
                raise BatchRecordsServiceError("batch_record_execution_review_invalid_status", status_code=409)
            if execution["reviewed_signature_id"]:
                raise BatchRecordsServiceError("batch_record_execution_already_reviewed", status_code=409)

            conn.execute(
                """
                UPDATE batch_record_executions
                SET status = 'reviewed',
                    reviewed_signature_id = ?,
                    completed_at_ms = COALESCE(completed_at_ms, ?),
                    updated_by_user_id = ?,
                    updated_at_ms = ?
                WHERE execution_id = ?
                """,
                (clean_signature_id, now_ms, actor, now_ms, clean_execution_id),
            )
            conn.commit()
        finally:
            conn.close()
        return self.get_execution(execution_id=clean_execution_id)

    def build_execution_record_payload(self, *, execution_id: str) -> dict[str, Any]:
        bundle = self.get_execution(execution_id=execution_id)
        template = bundle.get("template")
        execution = bundle.get("execution") or {}
        steps = bundle.get("latest_steps") or {}
        step_entries = bundle.get("step_entries") or []

        return {
            "execution": execution,
            "template": template,
            "latest_steps": {k: v.get("payload") for k, v in steps.items()},
            "step_entries": [
                {
                    "entry_id": e.get("entry_id"),
                    "step_key": e.get("step_key"),
                    "payload": e.get("payload"),
                    "created_by_user_id": e.get("created_by_user_id"),
                    "created_by_username": e.get("created_by_username"),
                    "created_at_ms": e.get("created_at_ms"),
                }
                for e in step_entries
            ],
        }
