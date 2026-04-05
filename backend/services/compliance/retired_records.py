from __future__ import annotations

import hashlib
import io
import json
import shutil
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from zipfile import ZIP_DEFLATED, ZipFile

from backend.app.core.managed_paths import to_managed_data_storage_path
from backend.app.core.paths import resolve_repo_path
from backend.services.kb import KbDocument, KbStore


def _file_sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            hasher.update(chunk)
    return hasher.hexdigest()


def _json_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8")


def _safe_segment(value: str) -> str:
    text = str(value or "").strip()
    safe = "".join(ch if ch.isalnum() or ch in ("-", "_", ".") else "_" for ch in text)
    return safe or "record"


@dataclass(slots=True)
class RetiredRecordPackageResult:
    package_bytes: bytes
    package_filename: str
    package_sha256: str
    manifest: dict[str, Any]
    retired_document: dict[str, Any]


class RetiredRecordsService:
    def __init__(self, *, kb_store: KbStore, repo_root: str | Path | None = None) -> None:
        self._kb_store = kb_store
        self._repo_root = resolve_repo_path(repo_root or ".").resolve()

    def list_retired_documents(
        self,
        *,
        kb_refs: list[str] | None = None,
        kb_id: str | None = None,
        limit: int = 100,
        include_expired: bool = False,
        now_ms: int | None = None,
    ) -> list[KbDocument]:
        return self._kb_store.list_retired_documents(
            kb_refs=kb_refs,
            kb_id=kb_id,
            limit=limit,
            include_expired=include_expired,
            now_ms=now_ms,
        )

    def get_retired_document(
        self,
        doc_id: str,
        *,
        allow_expired: bool = False,
        now_ms: int | None = None,
    ) -> KbDocument:
        doc = self._kb_store.get_document(doc_id)
        if not doc:
            raise KeyError("document_not_found")
        if str(getattr(doc, "effective_status", "") or "").strip().lower() != "archived":
            raise ValueError("document_not_retired")
        current_ms = int(time.time() * 1000) if now_ms is None else int(now_ms)
        retention_until_ms = getattr(doc, "retention_until_ms", None)
        if (
            not allow_expired
            and retention_until_ms is not None
            and int(retention_until_ms) < current_ms
        ):
            raise ValueError("document_retention_expired")
        return doc

    def retire_document(
        self,
        *,
        doc_id: str,
        retired_by: str,
        retirement_reason: str,
        retention_until_ms: int,
        retired_by_username: str | None = None,
        archived_at_ms: int | None = None,
    ) -> KbDocument:
        doc = self._kb_store.get_document(doc_id)
        if not doc:
            raise KeyError("document_not_found")
        if str(getattr(doc, "effective_status", "") or "").strip().lower() == "archived":
            raise ValueError("document_already_retired")
        if str(getattr(doc, "status", "") or "").strip().lower() != "approved":
            raise ValueError("only_approved_document_can_be_retired")

        source_path = Path(str(doc.file_path or "").strip())
        if not source_path.exists() or not source_path.is_file():
            raise FileNotFoundError("file_not_found")

        archived_ms = int(time.time() * 1000) if archived_at_ms is None else int(archived_at_ms)
        retention_until_ms = int(retention_until_ms)
        if retention_until_ms <= archived_ms:
            raise ValueError("retention_until_must_be_future")

        logical_doc_id = str(getattr(doc, "logical_doc_id", None) or doc.doc_id)
        archive_dir = (
            self._repo_root
            / "data"
            / "retired_documents"
            / _safe_segment(logical_doc_id)
            / f"{archived_ms}_{_safe_segment(doc.doc_id)}"
        )
        archive_dir.mkdir(parents=True, exist_ok=True)

        archived_file_path = archive_dir / source_path.name
        shutil.copy2(source_path, archived_file_path)
        archived_file_sha256 = _file_sha256(archived_file_path)
        package_filename = (
            f"retired_record_{_safe_segment(logical_doc_id)}_v{int(getattr(doc, 'version_no', 1) or 1)}.zip"
        )
        package_path = archive_dir / package_filename
        manifest_path = archive_dir / "retirement_manifest.json"

        manifest = self._build_manifest(
            doc=doc,
            archived_at_ms=archived_ms,
            retention_until_ms=retention_until_ms,
            retired_by=str(retired_by or "").strip(),
            retired_by_username=(str(retired_by_username or "").strip() or None),
            retirement_reason=str(retirement_reason or "").strip(),
            source_path=source_path,
            archived_file_path=archived_file_path,
            archived_file_sha256=archived_file_sha256,
            package_filename=package_filename,
        )
        manifest_bytes = _json_bytes(manifest)
        checksums = {
            "retirement_manifest.json": {"sha256": hashlib.sha256(manifest_bytes).hexdigest(), "size_bytes": len(manifest_bytes)},
            f"documents/{doc.filename}": {
                "sha256": archived_file_sha256,
                "size_bytes": archived_file_path.stat().st_size,
            },
        }
        checksums_bytes = _json_bytes(checksums)
        readme_bytes = self._build_readme(manifest=manifest).encode("utf-8")

        buffer = io.BytesIO()
        with ZipFile(buffer, mode="w", compression=ZIP_DEFLATED) as archive:
            archive.writestr("README.txt", readme_bytes)
            archive.writestr("retirement_manifest.json", manifest_bytes)
            archive.writestr("checksums.json", checksums_bytes)
            archive.writestr(f"documents/{doc.filename}", archived_file_path.read_bytes())
        package_bytes = buffer.getvalue()
        package_sha256 = hashlib.sha256(package_bytes).hexdigest()

        manifest["package"] = {
            "filename": package_filename,
            "sha256": package_sha256,
            "size_bytes": len(package_bytes),
        }
        manifest_bytes = _json_bytes(manifest)
        manifest_path.write_bytes(manifest_bytes)
        package_path.write_bytes(package_bytes)

        retired = self._kb_store.retire_document(
            doc_id=doc.doc_id,
            archived_file_path=str(archived_file_path),
            archive_manifest_path=str(manifest_path),
            archive_package_path=str(package_path),
            archive_package_sha256=package_sha256,
            retired_by=str(retired_by or "").strip(),
            retirement_reason=str(retirement_reason or "").strip(),
            retention_until_ms=retention_until_ms,
            archived_at_ms=archived_ms,
        )
        if retired is None:
            raise RuntimeError("document_retire_update_failed")
        return retired

    def export_retired_record_package(
        self,
        *,
        doc_id: str,
        allow_expired: bool = False,
        now_ms: int | None = None,
    ) -> RetiredRecordPackageResult:
        doc = self.get_retired_document(doc_id, allow_expired=allow_expired, now_ms=now_ms)
        package_path = Path(str(getattr(doc, "archive_package_path", "") or "").strip())
        manifest_path = Path(str(getattr(doc, "archive_manifest_path", "") or "").strip())
        if not package_path.exists() or not package_path.is_file():
            raise FileNotFoundError("archive_package_not_found")
        if not manifest_path.exists() or not manifest_path.is_file():
            raise FileNotFoundError("archive_manifest_not_found")

        package_bytes = package_path.read_bytes()
        package_sha256 = hashlib.sha256(package_bytes).hexdigest()
        expected_sha256 = str(getattr(doc, "archive_package_sha256", "") or "").strip()
        if expected_sha256 and expected_sha256 != package_sha256:
            raise RuntimeError("archive_package_sha256_mismatch")

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        return RetiredRecordPackageResult(
            package_bytes=package_bytes,
            package_filename=package_path.name,
            package_sha256=package_sha256,
            manifest=manifest,
            retired_document=self._document_payload(doc),
        )

    @staticmethod
    def _build_readme(*, manifest: dict[str, Any]) -> str:
        metadata = manifest.get("metadata") or {}
        record = manifest.get("record") or {}
        return "\n".join(
            [
                "RagflowAuth retired record package",
                f"Archived at: {metadata.get('archived_at_ms')}",
                f"Retention until: {metadata.get('retention_until_ms')}",
                f"Retired by: {metadata.get('retired_by')}",
                f"Reason: {metadata.get('retirement_reason')}",
                f"Document ID: {record.get('doc_id')}",
                f"Logical Document ID: {record.get('logical_doc_id')}",
                "",
            ]
        )

    @staticmethod
    def _document_payload(doc: KbDocument) -> dict[str, Any]:
        return {
            "doc_id": doc.doc_id,
            "filename": doc.filename,
            "file_size": doc.file_size,
            "mime_type": doc.mime_type,
            "uploaded_by": doc.uploaded_by,
            "status": doc.status,
            "uploaded_at_ms": doc.uploaded_at_ms,
            "reviewed_by": doc.reviewed_by,
            "reviewed_at_ms": doc.reviewed_at_ms,
            "review_notes": doc.review_notes,
            "kb_id": doc.kb_id,
            "kb_dataset_id": doc.kb_dataset_id,
            "kb_name": doc.kb_name,
            "logical_doc_id": doc.logical_doc_id,
            "version_no": doc.version_no,
            "previous_doc_id": doc.previous_doc_id,
            "superseded_by_doc_id": doc.superseded_by_doc_id,
            "is_current": doc.is_current,
            "effective_status": doc.effective_status,
            "archived_at_ms": doc.archived_at_ms,
            "retention_until_ms": doc.retention_until_ms,
            "file_sha256": doc.file_sha256,
            "retired_by": doc.retired_by,
            "retirement_reason": doc.retirement_reason,
            "archive_manifest_path": doc.archive_manifest_path,
            "archive_package_path": doc.archive_package_path,
            "archive_package_sha256": doc.archive_package_sha256,
        }

    def _build_manifest(
        self,
        *,
        doc: KbDocument,
        archived_at_ms: int,
        retention_until_ms: int,
        retired_by: str,
        retired_by_username: str | None,
        retirement_reason: str,
        source_path: Path,
        archived_file_path: Path,
        archived_file_sha256: str,
        package_filename: str,
    ) -> dict[str, Any]:
        return {
            "schema_version": "gbz03.v1",
            "metadata": {
                "archived_at_ms": archived_at_ms,
                "retention_until_ms": retention_until_ms,
                "retired_by": retired_by,
                "retired_by_username": retired_by_username,
                "retirement_reason": retirement_reason,
                "package_filename": package_filename,
            },
            "record": {
                "doc_id": doc.doc_id,
                "logical_doc_id": getattr(doc, "logical_doc_id", None) or doc.doc_id,
                "version_no": int(getattr(doc, "version_no", 1) or 1),
                "kb_id": doc.kb_id,
                "kb_dataset_id": doc.kb_dataset_id,
                "kb_name": doc.kb_name,
                "filename": doc.filename,
                "status": doc.status,
                "uploaded_by": doc.uploaded_by,
                "uploaded_at_ms": doc.uploaded_at_ms,
                "reviewed_by": doc.reviewed_by,
                "reviewed_at_ms": doc.reviewed_at_ms,
                "review_notes": doc.review_notes,
                "source_file_path": to_managed_data_storage_path(
                    source_path,
                    field_name="retired_record.source_file_path",
                ),
                "archived_file_path": to_managed_data_storage_path(
                    archived_file_path,
                    field_name="retired_record.archived_file_path",
                ),
                "file_sha256": archived_file_sha256,
            },
        }
