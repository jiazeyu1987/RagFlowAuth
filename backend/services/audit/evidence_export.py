from __future__ import annotations

import csv
import hashlib
import io
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from zipfile import ZIP_DEFLATED, ZipFile

from backend.database.paths import resolve_auth_db_path
from backend.database.sqlite import connect_sqlite


@dataclass(slots=True)
class EvidenceExportResult:
    package_bytes: bytes
    package_filename: str
    package_sha256: str
    manifest: dict[str, Any]
    counts: dict[str, int]


class AuditEvidenceExportService:
    def __init__(self, *, db_path: str | Path):
        self._db_path = resolve_auth_db_path(db_path)

    def export_package(
        self,
        *,
        exported_by: str,
        exported_by_username: str | None = None,
        filters: dict[str, Any] | None = None,
    ) -> EvidenceExportResult:
        normalized_filters = self._normalize_filters(filters or {})
        audit_events = self._list_audit_events(normalized_filters)
        signatures = self._list_electronic_signatures(normalized_filters)
        approval_actions = self._list_approval_actions(normalized_filters)
        notification_jobs = self._list_notification_jobs(normalized_filters)
        backup_jobs = self._list_backup_jobs(normalized_filters)
        restore_drills = self._list_restore_drills(normalized_filters)

        exported_at = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
        metadata = {
            "exported_at": exported_at,
            "exported_by": str(exported_by or "").strip(),
            "exported_by_username": (str(exported_by_username or "").strip() or None),
            "filters": normalized_filters,
            "record_copy_definition": {
                "human_readable_copy": "csv",
                "portable_structured_copy": "json",
                "integrity_summary": "manifest.json + checksums.json",
            },
        }
        counts = {
            "audit_events": len(audit_events),
            "electronic_signatures": len(signatures),
            "approval_actions": len(approval_actions),
            "notification_jobs": len(notification_jobs),
            "backup_jobs": len(backup_jobs),
            "restore_drills": len(restore_drills),
        }

        files: dict[str, bytes] = {}
        files["README.txt"] = self._build_readme(metadata=metadata, counts=counts).encode("utf-8")
        files["audit_events.json"] = self._json_bytes(audit_events)
        files["audit_events.csv"] = self._csv_bytes(
            audit_events,
            fieldnames=[
                "id",
                "action",
                "actor",
                "actor_username",
                "company_id",
                "company_name",
                "department_id",
                "department_name",
                "created_at_ms",
                "resource_type",
                "resource_id",
                "event_type",
                "reason",
                "signature_id",
                "request_id",
                "client_ip",
                "prev_hash",
                "event_hash",
                "source",
                "doc_id",
                "filename",
                "kb_id",
                "kb_dataset_id",
                "kb_name",
                "before_json",
                "after_json",
                "meta_json",
                "evidence_json",
            ],
        )
        files["electronic_signatures.json"] = self._json_bytes(signatures)
        files["electronic_signatures.csv"] = self._csv_bytes(
            signatures,
            fieldnames=[
                "signature_id",
                "record_type",
                "record_id",
                "action",
                "meaning",
                "reason",
                "signed_by",
                "signed_by_username",
                "signed_at_ms",
                "sign_token_id",
                "record_hash",
                "signature_hash",
                "status",
                "record_payload_json",
            ],
        )
        files["approval_actions.json"] = self._json_bytes(approval_actions)
        files["approval_actions.csv"] = self._csv_bytes(
            approval_actions,
            fieldnames=[
                "action_id",
                "instance_id",
                "doc_id",
                "workflow_id",
                "step_no",
                "action",
                "actor",
                "notes",
                "created_at_ms",
            ],
        )
        files["notification_jobs.json"] = self._json_bytes(notification_jobs)
        files["notification_jobs.csv"] = self._csv_bytes(
            notification_jobs,
            fieldnames=[
                "job_id",
                "channel_id",
                "event_type",
                "recipient_user_id",
                "recipient_username",
                "recipient_address",
                "dedupe_key",
                "source_job_id",
                "status",
                "attempts",
                "max_attempts",
                "last_error",
                "created_at_ms",
                "sent_at_ms",
                "next_retry_at_ms",
                "payload_json",
                "delivery_log_count",
            ],
        )
        files["backup_jobs.json"] = self._json_bytes(backup_jobs)
        files["backup_jobs.csv"] = self._csv_bytes(
            backup_jobs,
            fieldnames=[
                "id",
                "kind",
                "status",
                "progress",
                "message",
                "detail",
                "output_dir",
                "package_hash",
                "verified_by",
                "verified_at_ms",
                "created_at_ms",
                "started_at_ms",
                "finished_at_ms",
                "replication_status",
                "replication_error",
                "replica_path",
                "verification_status",
                "verification_detail",
                "last_restore_drill_id",
            ],
        )
        files["restore_drills.json"] = self._json_bytes(restore_drills)
        files["restore_drills.csv"] = self._csv_bytes(
            restore_drills,
            fieldnames=[
                "drill_id",
                "job_id",
                "backup_path",
                "backup_hash",
                "actual_backup_hash",
                "hash_match",
                "restore_target",
                "restored_auth_db_path",
                "restored_auth_db_hash",
                "compare_match",
                "package_validation_status",
                "acceptance_status",
                "executed_by",
                "executed_at_ms",
                "result",
                "verification_notes",
                "verification_report_json",
            ],
        )

        manifest = self._build_manifest(metadata=metadata, counts=counts, files=files)
        files["manifest.json"] = self._json_bytes(manifest)
        files["checksums.json"] = self._json_bytes(manifest["files"])

        package_bytes = self._build_zip(files)
        package_sha256 = hashlib.sha256(package_bytes).hexdigest()
        package_filename = self._package_filename(normalized_filters)
        return EvidenceExportResult(
            package_bytes=package_bytes,
            package_filename=package_filename,
            package_sha256=package_sha256,
            manifest=manifest,
            counts=counts,
        )

    @staticmethod
    def _normalize_filters(filters: dict[str, Any]) -> dict[str, Any]:
        normalized: dict[str, Any] = {}
        for key in ("from_ms", "to_ms"):
            value = filters.get(key)
            if value is None or value == "":
                continue
            normalized[key] = int(value)
        for key in (
            "action",
            "doc_id",
            "actor",
            "signature_id",
            "request_id",
            "event_type",
            "filename",
            "resource_type",
            "resource_id",
            "source",
        ):
            value = str(filters.get(key) or "").strip()
            if value:
                normalized[key] = value
        return normalized

    def _conn(self):
        return connect_sqlite(self._db_path)

    def _list_audit_events(self, filters: dict[str, Any]) -> list[dict[str, Any]]:
        where = ["1=1"]
        params: list[Any] = []
        if filters.get("from_ms") is not None:
            where.append("created_at_ms >= ?")
            params.append(int(filters["from_ms"]))
        if filters.get("to_ms") is not None:
            where.append("created_at_ms <= ?")
            params.append(int(filters["to_ms"]))
        for key in (
            "action",
            "doc_id",
            "actor",
            "signature_id",
            "request_id",
            "event_type",
            "filename",
            "resource_type",
            "resource_id",
            "source",
        ):
            value = filters.get(key)
            if value:
                where.append(f"{key} = ?")
                params.append(value)
        query = f"""
            SELECT
                id, action, actor, actor_username, company_id, company_name, department_id, department_name,
                created_at_ms, resource_type, resource_id, event_type, before_json, after_json, reason,
                signature_id, request_id, client_ip, prev_hash, event_hash, source, doc_id, filename,
                kb_id, kb_dataset_id, kb_name, meta_json, evidence_json
            FROM audit_events
            WHERE {' AND '.join(where)}
            ORDER BY created_at_ms ASC, id ASC
        """
        with self._conn() as conn:
            rows = conn.execute(query, params).fetchall()
        items: list[dict[str, Any]] = []
        for row in rows:
            item = dict(row)
            item["evidence_refs"] = self._decode_json(item.get("evidence_json")) or []
            items.append(item)
        return items

    def _list_electronic_signatures(self, filters: dict[str, Any]) -> list[dict[str, Any]]:
        where = ["1=1"]
        params: list[Any] = []
        if filters.get("from_ms") is not None:
            where.append("signed_at_ms >= ?")
            params.append(int(filters["from_ms"]))
        if filters.get("to_ms") is not None:
            where.append("signed_at_ms <= ?")
            params.append(int(filters["to_ms"]))
        if filters.get("doc_id"):
            where.append("record_id = ?")
            params.append(filters["doc_id"])
        if filters.get("actor"):
            where.append("signed_by = ?")
            params.append(filters["actor"])
        if filters.get("signature_id"):
            where.append("signature_id = ?")
            params.append(filters["signature_id"])
        query = f"""
            SELECT
                signature_id, record_type, record_id, action, meaning, reason, signed_by, signed_by_username,
                signed_at_ms, sign_token_id, record_hash, signature_hash, status, record_payload_json
            FROM electronic_signatures
            WHERE {' AND '.join(where)}
            ORDER BY signed_at_ms ASC, signature_id ASC
        """
        with self._conn() as conn:
            rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]

    def _list_approval_actions(self, filters: dict[str, Any]) -> list[dict[str, Any]]:
        where = ["1=1"]
        params: list[Any] = []
        if filters.get("from_ms") is not None:
            where.append("created_at_ms >= ?")
            params.append(int(filters["from_ms"]))
        if filters.get("to_ms") is not None:
            where.append("created_at_ms <= ?")
            params.append(int(filters["to_ms"]))
        if filters.get("doc_id"):
            where.append("doc_id = ?")
            params.append(filters["doc_id"])
        if filters.get("actor"):
            where.append("actor = ?")
            params.append(filters["actor"])
        query = f"""
            SELECT
                action_id, instance_id, doc_id, workflow_id, step_no, action, actor, notes, created_at_ms
            FROM document_approval_actions
            WHERE {' AND '.join(where)}
            ORDER BY created_at_ms ASC, action_id ASC
        """
        with self._conn() as conn:
            rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]

    def _list_notification_jobs(self, filters: dict[str, Any]) -> list[dict[str, Any]]:
        where = ["1=1"]
        params: list[Any] = []
        if filters.get("from_ms") is not None:
            where.append("created_at_ms >= ?")
            params.append(int(filters["from_ms"]))
        if filters.get("to_ms") is not None:
            where.append("created_at_ms <= ?")
            params.append(int(filters["to_ms"]))
        if filters.get("actor"):
            where.append("COALESCE(recipient_user_id, '') = ?")
            params.append(filters["actor"])
        if filters.get("request_id"):
            where.append("payload_json LIKE ?")
            params.append(f'%{filters["request_id"]}%')
        query = f"""
            SELECT
                job_id, channel_id, event_type, payload_json, recipient_user_id, recipient_username,
                recipient_address, dedupe_key, source_job_id, status, attempts, max_attempts,
                last_error, created_at_ms, sent_at_ms, next_retry_at_ms
            FROM notification_jobs
            WHERE {' AND '.join(where)}
            ORDER BY created_at_ms ASC, job_id ASC
        """
        with self._conn() as conn:
            rows = conn.execute(query, params).fetchall()
            items: list[dict[str, Any]] = []
            for row in rows:
                item = dict(row)
                payload = self._decode_json(item.get("payload_json"))
                if not self._notification_matches_filters(payload=payload, filters=filters):
                    continue
                delivery_logs = conn.execute(
                    """
                    SELECT id, job_id, channel_id, status, error, attempted_at_ms
                    FROM notification_delivery_logs
                    WHERE job_id = ?
                    ORDER BY attempted_at_ms ASC, id ASC
                    """,
                    (int(item["job_id"]),),
                ).fetchall()
                item["payload"] = payload
                item["delivery_logs"] = [dict(log) for log in delivery_logs]
                item["delivery_log_count"] = len(item["delivery_logs"])
                items.append(item)
        return items

    @staticmethod
    def _notification_matches_filters(*, payload: Any, filters: dict[str, Any]) -> bool:
        if not isinstance(payload, dict):
            return not filters.get("doc_id")
        doc_id = str(filters.get("doc_id") or "").strip()
        if doc_id:
            payload_doc_id = str(payload.get("doc_id") or payload.get("approval_target", {}).get("doc_id") or "").strip()
            if payload_doc_id != doc_id:
                return False
        filename = str(filters.get("filename") or "").strip()
        if filename and str(payload.get("filename") or "").strip() != filename:
            return False
        return True

    def _list_backup_jobs(self, filters: dict[str, Any]) -> list[dict[str, Any]]:
        where = ["1=1"]
        params: list[Any] = []
        if filters.get("from_ms") is not None:
            where.append("created_at_ms >= ?")
            params.append(int(filters["from_ms"]))
        if filters.get("to_ms") is not None:
            where.append("created_at_ms <= ?")
            params.append(int(filters["to_ms"]))
        query = f"""
            SELECT
                id, kind, status, progress, message, detail, output_dir, package_hash, verified_by,
                verified_at_ms, created_at_ms, started_at_ms, finished_at_ms, replication_status,
                replication_error, replica_path, verification_status, verification_detail, last_restore_drill_id
            FROM backup_jobs
            WHERE {' AND '.join(where)}
            ORDER BY created_at_ms ASC, id ASC
        """
        with self._conn() as conn:
            rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]

    def _list_restore_drills(self, filters: dict[str, Any]) -> list[dict[str, Any]]:
        where = ["1=1"]
        params: list[Any] = []
        if filters.get("from_ms") is not None:
            where.append("executed_at_ms >= ?")
            params.append(int(filters["from_ms"]))
        if filters.get("to_ms") is not None:
            where.append("executed_at_ms <= ?")
            params.append(int(filters["to_ms"]))
        query = f"""
            SELECT
                drill_id, job_id, backup_path, backup_hash, actual_backup_hash, hash_match,
                restore_target, restored_auth_db_path, restored_auth_db_hash, compare_match,
                package_validation_status, acceptance_status, executed_by, executed_at_ms,
                result, verification_notes, verification_report_json
            FROM restore_drills
            WHERE {' AND '.join(where)}
            ORDER BY executed_at_ms ASC, drill_id ASC
        """
        with self._conn() as conn:
            rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]

    @staticmethod
    def _build_readme(*, metadata: dict[str, Any], counts: dict[str, int]) -> str:
        return "\n".join(
            [
                "RagflowAuth inspection evidence export",
                f"Exported at: {metadata['exported_at']}",
                f"Exported by: {metadata['exported_by']}",
                f"Filters: {json.dumps(metadata['filters'], ensure_ascii=False, sort_keys=True)}",
                "Human readable copy: CSV",
                "Portable structured copy: JSON",
                "Integrity summary: manifest.json and checksums.json",
                f"Counts: {json.dumps(counts, ensure_ascii=False, sort_keys=True)}",
                "",
            ]
        )

    @staticmethod
    def _json_bytes(items: Any) -> bytes:
        return json.dumps(items, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8")

    @staticmethod
    def _csv_bytes(items: list[dict[str, Any]], *, fieldnames: list[str]) -> bytes:
        buffer = io.StringIO()
        writer = csv.DictWriter(buffer, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for item in items:
            row: dict[str, Any] = {}
            for field in fieldnames:
                value = item.get(field)
                if isinstance(value, (dict, list)):
                    row[field] = json.dumps(value, ensure_ascii=False, sort_keys=True)
                else:
                    row[field] = value
            writer.writerow(row)
        return buffer.getvalue().encode("utf-8")

    @staticmethod
    def _build_manifest(
        *,
        metadata: dict[str, Any],
        counts: dict[str, int],
        files: dict[str, bytes],
    ) -> dict[str, Any]:
        return {
            "schema_version": "fda02.v1",
            "metadata": metadata,
            "counts": counts,
            "files": {
                name: {
                    "sha256": hashlib.sha256(content).hexdigest(),
                    "size_bytes": len(content),
                }
                for name, content in sorted(files.items())
            },
        }

    @staticmethod
    def _build_zip(files: dict[str, bytes]) -> bytes:
        buffer = io.BytesIO()
        with ZipFile(buffer, mode="w", compression=ZIP_DEFLATED) as archive:
            for name, content in sorted(files.items()):
                archive.writestr(name, content)
        return buffer.getvalue()

    @staticmethod
    def _package_filename(filters: dict[str, Any]) -> str:
        suffix = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        doc_id = str(filters.get("doc_id") or "").strip()
        if doc_id:
            safe_doc_id = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in doc_id)
            return f"inspection_evidence_{safe_doc_id}_{suffix}.zip"
        return f"inspection_evidence_{suffix}.zip"

    @staticmethod
    def _decode_json(value: Any) -> Any:
        if not value:
            return None
        try:
            return json.loads(value)
        except Exception:
            return None
