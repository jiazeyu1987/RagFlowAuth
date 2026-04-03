from __future__ import annotations

import csv
import hashlib
import io
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from zipfile import ZIP_DEFLATED, ZipFile

from backend.app.core.config import settings
from backend.app.core.paths import resolve_repo_path
from backend.database.tenant_paths import tenant_key_for_company


REGISTER_RELATIVE_PATH = "doc/compliance/controlled_document_register.md"
REQUIRED_REGISTER_COLUMNS = (
    "doc_code",
    "title",
    "file_path",
    "version",
    "status",
    "effective_date",
    "review_due_date",
    "approved_release_version",
    "package_group",
)
REQUIRED_REVIEW_PACKAGE_GROUPS = {"requirements", "validation", "sop", "package"}


@dataclass(slots=True, frozen=True)
class ControlledDocumentRecord:
    doc_code: str
    title: str
    path: str
    version: str
    status: str
    effective_date: str | None
    review_due_date: str | None
    approved_release_version: str
    package_group: str
    file_sha256: str
    file_exists: bool
    file_updated_at: str | None
    header_version: str | None
    header_updated_at: str | None
    release_matches: bool
    eligible_for_review_package: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "doc_code": self.doc_code,
            "title": self.title,
            "path": self.path,
            "version": self.version,
            "status": self.status,
            "effective_date": self.effective_date,
            "review_due_date": self.review_due_date,
            "approved_release_version": self.approved_release_version,
            "package_group": self.package_group,
            "file_sha256": self.file_sha256,
            "file_exists": self.file_exists,
            "file_updated_at": self.file_updated_at,
            "header_version": self.header_version,
            "header_updated_at": self.header_updated_at,
            "release_matches": self.release_matches,
            "eligible_for_review_package": self.eligible_for_review_package,
        }


@dataclass(slots=True)
class ReviewPackageExportResult:
    package_bytes: bytes
    package_filename: str
    package_sha256: str
    manifest: dict[str, Any]
    documents: list[dict[str, Any]]


class ComplianceReviewPackageService:
    def __init__(self, *, repo_root: str | Path | None = None, release_version: str | None = None):
        self._repo_root = resolve_repo_path(repo_root or ".").resolve()
        self._release_version = str(release_version or settings.APP_VERSION).strip()

    @property
    def release_version(self) -> str:
        return self._release_version

    def list_controlled_documents(self) -> list[ControlledDocumentRecord]:
        register_path = self._repo_root / REGISTER_RELATIVE_PATH
        text = register_path.read_text(encoding="utf-8")
        rows = self._parse_markdown_table(text)
        items: list[ControlledDocumentRecord] = []
        for row in rows:
            rel_path = str(row["file_path"]).strip()
            absolute_path = (self._repo_root / rel_path).resolve()
            file_exists = absolute_path.exists() and absolute_path.is_file()
            header_version = None
            header_updated_at = None
            file_sha256 = ""
            file_updated_at = None
            if file_exists:
                file_text = absolute_path.read_text(encoding="utf-8")
                header_version = self._match_header(file_text, "版本")
                header_updated_at = self._match_header(file_text, "更新时间")
                file_sha256 = hashlib.sha256(absolute_path.read_bytes()).hexdigest()
                file_updated_at = datetime.fromtimestamp(
                    absolute_path.stat().st_mtime,
                    tz=timezone.utc,
                ).astimezone().isoformat(timespec="seconds")

            version = str(row["version"]).strip()
            status = str(row["status"]).strip().lower()
            approved_release_version = str(row["approved_release_version"]).strip()
            release_matches = approved_release_version == self._release_version
            eligible = file_exists and status in {"effective", "current"} and release_matches
            items.append(
                ControlledDocumentRecord(
                    doc_code=str(row["doc_code"]).strip(),
                    title=str(row["title"]).strip(),
                    path=rel_path,
                    version=version,
                    status=status,
                    effective_date=self._nullable_cell(row.get("effective_date")),
                    review_due_date=self._nullable_cell(row.get("review_due_date")),
                    approved_release_version=approved_release_version,
                    package_group=str(row["package_group"]).strip(),
                    file_sha256=file_sha256,
                    file_exists=file_exists,
                    file_updated_at=file_updated_at,
                    header_version=header_version,
                    header_updated_at=header_updated_at,
                    release_matches=release_matches,
                    eligible_for_review_package=eligible,
                )
            )
        return items

    def export_review_package(
        self,
        *,
        exported_by: str,
        exported_by_username: str | None,
        company_id: int | None,
    ) -> ReviewPackageExportResult:
        documents = self.list_controlled_documents()
        included = [item for item in documents if item.eligible_for_review_package]
        if not included:
            raise ValueError("controlled_review_package_documents_missing")
        present_groups = {item.package_group for item in included}
        missing_groups = sorted(REQUIRED_REVIEW_PACKAGE_GROUPS - present_groups)
        if missing_groups:
            raise ValueError(f"controlled_review_package_group_missing:{','.join(missing_groups)}")

        exported_at = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
        metadata = {
            "exported_at": exported_at,
            "exported_by": str(exported_by or "").strip(),
            "exported_by_username": (str(exported_by_username or "").strip() or None),
            "release_version": self._release_version,
            "company_id": (int(company_id) if company_id is not None else None),
            "tenant_key": (tenant_key_for_company(company_id) if company_id is not None else None),
            "register_path": REGISTER_RELATIVE_PATH,
        }

        files: dict[str, bytes] = {}
        files["README.txt"] = self._build_readme(metadata=metadata, documents=included).encode("utf-8")
        files["controlled_documents.json"] = self._json_bytes([item.as_dict() for item in documents])
        files["controlled_documents.csv"] = self._csv_bytes(
            [item.as_dict() for item in documents],
            fieldnames=[
                "doc_code",
                "title",
                "path",
                "version",
                "status",
                "effective_date",
                "review_due_date",
                "approved_release_version",
                "package_group",
                "file_sha256",
                "file_exists",
                "file_updated_at",
                "header_version",
                "header_updated_at",
                "release_matches",
                "eligible_for_review_package",
            ],
        )
        for item in included:
            doc_path = (self._repo_root / item.path).resolve()
            files[f"documents/{Path(item.path).name}"] = doc_path.read_bytes()

        manifest = self._build_manifest(metadata=metadata, documents=included, files=files)
        files["review_package_manifest.json"] = self._json_bytes(manifest)
        files["review_package_checksums.json"] = self._json_bytes(manifest["files"])

        package_bytes = self._build_zip(files)
        package_sha256 = hashlib.sha256(package_bytes).hexdigest()
        package_filename = (
            f"review_package_{self._release_version}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.zip"
        )
        return ReviewPackageExportResult(
            package_bytes=package_bytes,
            package_filename=package_filename,
            package_sha256=package_sha256,
            manifest=manifest,
            documents=[item.as_dict() for item in documents],
        )

    @staticmethod
    def _nullable_cell(value: Any) -> str | None:
        text = str(value or "").strip()
        return text or None

    @staticmethod
    def _match_header(text: str, field_name: str) -> str | None:
        pattern = re.compile(rf"^{re.escape(field_name)}:\s*(.+?)\s*$", re.MULTILINE)
        match = pattern.search(text)
        if not match:
            return None
        return match.group(1).strip()

    @staticmethod
    def _parse_markdown_table(text: str) -> list[dict[str, str]]:
        rows = [line.strip() for line in text.splitlines() if line.strip().startswith("|")]
        if len(rows) < 3:
            raise ValueError("controlled_document_register_table_missing")
        headers = [cell.strip() for cell in rows[0].strip("|").split("|")]
        missing_columns = [name for name in REQUIRED_REGISTER_COLUMNS if name not in headers]
        if missing_columns:
            raise ValueError(f"controlled_document_register_columns_missing:{','.join(missing_columns)}")

        items: list[dict[str, str]] = []
        for raw in rows[2:]:
            cells = [cell.strip() for cell in raw.strip("|").split("|")]
            if len(cells) != len(headers):
                continue
            items.append(dict(zip(headers, cells, strict=True)))
        return items

    @staticmethod
    def _json_bytes(value: Any) -> bytes:
        return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8")

    @staticmethod
    def _csv_bytes(rows: list[dict[str, Any]], *, fieldnames: list[str]) -> bytes:
        buffer = io.StringIO()
        writer = csv.DictWriter(buffer, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
        return buffer.getvalue().encode("utf-8")

    @staticmethod
    def _build_zip(files: dict[str, bytes]) -> bytes:
        buffer = io.BytesIO()
        with ZipFile(buffer, mode="w", compression=ZIP_DEFLATED) as archive:
            for name, content in sorted(files.items()):
                archive.writestr(name, content)
        return buffer.getvalue()

    @staticmethod
    def _build_readme(*, metadata: dict[str, Any], documents: list[ControlledDocumentRecord]) -> str:
        return "\n".join(
            [
                "RagflowAuth controlled document review package",
                f"Release version: {metadata['release_version']}",
                f"Company ID: {metadata['company_id']}",
                f"Tenant key: {metadata['tenant_key']}",
                f"Exported by: {metadata['exported_by']}",
                f"Exported at: {metadata['exported_at']}",
                f"Included document count: {len(documents)}",
                "",
            ]
        )

    @staticmethod
    def _build_manifest(
        *,
        metadata: dict[str, Any],
        documents: list[ControlledDocumentRecord],
        files: dict[str, bytes],
    ) -> dict[str, Any]:
        return {
            "schema_version": "fda03.v1",
            "metadata": metadata,
            "documents": [item.as_dict() for item in documents],
            "files": {
                name: {
                    "sha256": hashlib.sha256(content).hexdigest(),
                    "size_bytes": len(content),
                }
                for name, content in sorted(files.items())
            },
        }
