from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict, dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any

from backend.app.core.managed_paths import (
    managed_root_path,
    to_managed_child_storage_path,
    to_managed_data_storage_path,
)
from backend.app.core.paths import repo_root
from backend.database.paths import resolve_auth_db_path


@dataclass(frozen=True)
class DatabaseUpdateAction:
    table: str
    where: dict[str, Any]
    values: dict[str, Any]
    reason: str


@dataclass(frozen=True)
class DatabaseDeleteAction:
    table: str
    where: dict[str, Any]
    reason: str


@dataclass(frozen=True)
class FileDeleteAction:
    path: str
    reason: str


@dataclass(frozen=True)
class DirectoryDeleteAction:
    path: str
    reason: str


@dataclass(frozen=True)
class ReconcileIssue:
    category: str
    table: str | None
    row_ref: dict[str, Any] | None
    column: str | None
    raw_value: str | None
    normalized_value: str | None
    path: str | None
    reason: str


@dataclass
class ReconcileReport:
    db_updates: list[DatabaseUpdateAction] = field(default_factory=list)
    db_deletes: list[DatabaseDeleteAction] = field(default_factory=list)
    file_deletes: list[FileDeleteAction] = field(default_factory=list)
    dir_deletes: list[DirectoryDeleteAction] = field(default_factory=list)
    issues: list[ReconcileIssue] = field(default_factory=list)
    summary: dict[str, int] = field(default_factory=dict)

    def finalize(self) -> ReconcileReport:
        issue_breakdown: dict[str, int] = {}
        for item in self.issues:
            issue_breakdown[item.category] = int(issue_breakdown.get(item.category, 0) or 0) + 1
        self.summary = {
            "db_updates": len(self.db_updates),
            "db_deletes": len(self.db_deletes),
            "file_deletes": len(self.file_deletes),
            "dir_deletes": len(self.dir_deletes),
            "issues": len(self.issues),
            **{f"issue_{key}": value for key, value in sorted(issue_breakdown.items())},
        }
        return self

    def to_dict(self) -> dict[str, Any]:
        return {
            "summary": dict(self.summary),
            "db_updates": [asdict(item) for item in self.db_updates],
            "db_deletes": [asdict(item) for item in self.db_deletes],
            "file_deletes": [asdict(item) for item in self.file_deletes],
            "dir_deletes": [asdict(item) for item in self.dir_deletes],
            "issues": [asdict(item) for item in self.issues],
        }


@dataclass(frozen=True)
class _PathPlan:
    raw_value: str
    normalized_value: str | None
    absolute_path: Path | None
    exists: bool
    fixable: bool
    reason: str


class DataReconcileService:
    def __init__(self, *, db_path: str | Path | None = None) -> None:
        self._db_path = resolve_auth_db_path(db_path)
        self._repo_root = repo_root().resolve()
        self._data_root = managed_root_path("data")
        self._uploads_root = managed_root_path("data/uploads")
        self._paper_root = managed_root_path("data/paper_downloads")
        self._patent_root = managed_root_path("data/patent_downloads")
        self._package_drawing_root = managed_root_path("data/package_drawing_images")

    def report(self) -> ReconcileReport:
        report = ReconcileReport()
        referenced_uploads: set[Path] = set()
        referenced_papers: set[Path] = set()
        referenced_patents: set[Path] = set()
        referenced_package_drawings: set[Path] = set()

        conn = self._connect()
        try:
            if self._table_exists(conn, "kb_documents"):
                kb_refs = self._plan_kb_documents(conn, report)
                referenced_uploads.update(kb_refs)
            if self._table_exists(conn, "operation_approval_artifacts"):
                referenced_uploads.update(self._plan_operation_approval_artifacts(conn, report))
            if self._table_exists(conn, "paper_download_items"):
                refs = self._plan_download_items(
                    conn,
                    report,
                    table="paper_download_items",
                    root=self._paper_root,
                    missing_file_category="missing_paper_download_file",
                    missing_analysis_category="missing_paper_analysis_file",
                    invalid_file_category="invalid_paper_download_file_path",
                    invalid_analysis_category="invalid_paper_analysis_file_path",
                )
                referenced_papers.update(refs)
            if self._table_exists(conn, "patent_download_items"):
                refs = self._plan_download_items(
                    conn,
                    report,
                    table="patent_download_items",
                    root=self._patent_root,
                    missing_file_category="missing_patent_download_file",
                    missing_analysis_category="missing_patent_analysis_file",
                    invalid_file_category="invalid_patent_download_file_path",
                    invalid_analysis_category="invalid_patent_analysis_file_path",
                )
                referenced_patents.update(refs)
            if self._table_exists(conn, "package_drawing_images"):
                refs = self._plan_package_drawing_images(conn, report)
                referenced_package_drawings.update(refs)
        finally:
            conn.close()

        self._plan_orphan_files(
            report,
            root=self._uploads_root,
            referenced_paths=referenced_uploads,
            file_reason="orphan_upload_file",
            dir_reason="empty_upload_directory",
        )
        self._plan_orphan_files(
            report,
            root=self._paper_root,
            referenced_paths=referenced_papers,
            file_reason="orphan_paper_download_file",
            dir_reason="empty_paper_download_directory",
        )
        self._plan_orphan_files(
            report,
            root=self._patent_root,
            referenced_paths=referenced_patents,
            file_reason="orphan_patent_download_file",
            dir_reason="empty_patent_download_directory",
        )
        self._plan_orphan_files(
            report,
            root=self._package_drawing_root,
            referenced_paths=referenced_package_drawings,
            file_reason="orphan_package_drawing_file",
            dir_reason="empty_package_drawing_directory",
        )
        return report.finalize()

    def apply(self) -> dict[str, Any]:
        report = self.report()
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            for action in report.db_updates:
                values = dict(action.values)
                where = dict(action.where)
                set_clause = ", ".join(f"{column} = ?" for column in values.keys())
                where_clause = " AND ".join(f"{column} = ?" for column in where.keys())
                conn.execute(
                    f"UPDATE {action.table} SET {set_clause} WHERE {where_clause}",
                    [*values.values(), *where.values()],
                )
            for action in report.db_deletes:
                where = dict(action.where)
                where_clause = " AND ".join(f"{column} = ?" for column in where.keys())
                conn.execute(
                    f"DELETE FROM {action.table} WHERE {where_clause}",
                    list(where.values()),
                )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

        for action in report.file_deletes:
            path = Path(action.path)
            if path.exists():
                path.unlink()

        for action in sorted(report.dir_deletes, key=lambda item: len(Path(item.path).parts), reverse=True):
            path = Path(action.path)
            if path.exists() and path.is_dir():
                try:
                    path.rmdir()
                except OSError:
                    continue

        return report.to_dict()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._db_path), timeout=30.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA busy_timeout = 5000")
        conn.execute("PRAGMA journal_mode = DELETE")
        conn.execute("PRAGMA synchronous = NORMAL")
        return conn

    @staticmethod
    def _table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
        row = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
            (table_name,),
        ).fetchone()
        return row is not None

    @staticmethod
    def _canonical_text(value: str) -> str:
        return value.replace("\\", "/").strip()

    def _map_legacy_data_path(self, raw_value: str) -> str | None:
        text = self._canonical_text(raw_value)
        lowered = text.lower()
        marker = "/data/"
        index = lowered.find(marker)
        if index < 0:
            return None
        suffix = text[index + 1 :]
        try:
            return to_managed_data_storage_path(suffix, field_name="legacy_path")
        except ValueError:
            return None

    def _plan_managed_data_path(self, raw_value: Any, *, field_name: str) -> _PathPlan:
        text = str(raw_value or "").strip()
        if not text:
            return _PathPlan(
                raw_value=text,
                normalized_value=None,
                absolute_path=None,
                exists=False,
                fixable=False,
                reason="empty_path",
            )

        canonical_text = self._canonical_text(text)
        try:
            normalized = to_managed_data_storage_path(text, field_name=field_name)
            absolute = (self._repo_root / Path(*PurePosixPath(normalized).parts)).resolve()
            exists = absolute.exists()
            fixable = canonical_text != normalized
            reason = "path_exists" if exists else "managed_file_missing"
            return _PathPlan(
                raw_value=text,
                normalized_value=normalized,
                absolute_path=absolute,
                exists=exists,
                fixable=fixable,
                reason=reason,
            )
        except ValueError:
            normalized = self._map_legacy_data_path(text)
            if normalized:
                absolute = (self._repo_root / Path(*PurePosixPath(normalized).parts)).resolve()
                exists = absolute.exists()
                return _PathPlan(
                    raw_value=text,
                    normalized_value=normalized,
                    absolute_path=absolute,
                    exists=exists,
                    fixable=exists,
                    reason="legacy_managed_path_rewrite" if exists else "legacy_target_missing",
                )
            return _PathPlan(
                raw_value=text,
                normalized_value=None,
                absolute_path=None,
                exists=False,
                fixable=False,
                reason="invalid_managed_data_path",
            )

    def _plan_managed_child_path(
        self,
        raw_value: Any,
        *,
        managed_root: Path,
        field_name: str,
    ) -> _PathPlan:
        text = str(raw_value or "").strip()
        if not text:
            return _PathPlan(
                raw_value=text,
                normalized_value=None,
                absolute_path=None,
                exists=False,
                fixable=False,
                reason="empty_path",
            )

        canonical_text = self._canonical_text(text)
        try:
            normalized = to_managed_child_storage_path(
                text,
                managed_root=managed_root,
                field_name=field_name,
            )
            absolute = (managed_root / Path(*PurePosixPath(normalized).parts)).resolve()
            exists = absolute.exists()
            fixable = canonical_text != normalized
            reason = "path_exists" if exists else "managed_file_missing"
            return _PathPlan(
                raw_value=text,
                normalized_value=normalized,
                absolute_path=absolute,
                exists=exists,
                fixable=fixable,
                reason=reason,
            )
        except ValueError:
            normalized = self._map_legacy_data_path(text)
            if normalized:
                absolute = (self._repo_root / Path(*PurePosixPath(normalized).parts)).resolve()
                try:
                    child = absolute.relative_to(managed_root)
                except ValueError:
                    child = None
                if child is not None:
                    exists = absolute.exists()
                    normalized_child = child.as_posix()
                    return _PathPlan(
                        raw_value=text,
                        normalized_value=normalized_child,
                        absolute_path=absolute,
                        exists=exists,
                        fixable=exists,
                        reason="legacy_managed_path_rewrite" if exists else "legacy_target_missing",
                    )
            return _PathPlan(
                raw_value=text,
                normalized_value=None,
                absolute_path=None,
                exists=False,
                fixable=False,
                reason="invalid_managed_child_path",
            )

    def _add_issue(
        self,
        report: ReconcileReport,
        *,
        category: str,
        table: str | None,
        row_ref: dict[str, Any] | None,
        column: str | None,
        raw_value: str | None,
        normalized_value: str | None,
        path: Path | None,
        reason: str,
    ) -> None:
        report.issues.append(
            ReconcileIssue(
                category=category,
                table=table,
                row_ref=row_ref,
                column=column,
                raw_value=raw_value,
                normalized_value=normalized_value,
                path=(str(path) if path is not None else None),
                reason=reason,
            )
        )

    def _plan_kb_documents(self, conn: sqlite3.Connection, report: ReconcileReport) -> set[Path]:
        referenced_uploads: set[Path] = set()
        rows = conn.execute(
            """
            SELECT doc_id, file_path, archive_manifest_path, archive_package_path
            FROM kb_documents
            """
        ).fetchall()
        for row in rows:
            row_ref = {"doc_id": str(row["doc_id"])}
            file_plan = self._plan_managed_data_path(
                row["file_path"],
                field_name="kb_documents.file_path",
            )
            if file_plan.fixable and file_plan.normalized_value:
                report.db_updates.append(
                    DatabaseUpdateAction(
                        table="kb_documents",
                        where=row_ref,
                        values={"file_path": file_plan.normalized_value},
                        reason=file_plan.reason,
                    )
                )
            if file_plan.absolute_path is not None and file_plan.absolute_path.is_relative_to(self._uploads_root):
                if file_plan.exists:
                    referenced_uploads.add(file_plan.absolute_path)
            if not file_plan.exists:
                self._add_issue(
                    report,
                    category="missing_kb_document_file",
                    table="kb_documents",
                    row_ref=row_ref,
                    column="file_path",
                    raw_value=file_plan.raw_value,
                    normalized_value=file_plan.normalized_value,
                    path=file_plan.absolute_path,
                    reason=file_plan.reason,
                )

            for column_name in ("archive_manifest_path", "archive_package_path"):
                raw_value = row[column_name]
                if raw_value is None or str(raw_value).strip() == "":
                    continue
                plan = self._plan_managed_data_path(
                    raw_value,
                    field_name=f"kb_documents.{column_name}",
                )
                if plan.fixable and plan.normalized_value:
                    report.db_updates.append(
                        DatabaseUpdateAction(
                            table="kb_documents",
                            where=row_ref,
                            values={column_name: plan.normalized_value},
                            reason=plan.reason,
                        )
                    )
                if not plan.exists:
                    self._add_issue(
                        report,
                        category=f"missing_kb_{column_name}",
                        table="kb_documents",
                        row_ref=row_ref,
                        column=column_name,
                        raw_value=plan.raw_value,
                        normalized_value=plan.normalized_value,
                        path=plan.absolute_path,
                        reason=plan.reason,
                    )
        return referenced_uploads

    def _plan_operation_approval_artifacts(self, conn: sqlite3.Connection, report: ReconcileReport) -> set[Path]:
        referenced_uploads: set[Path] = set()
        rows = conn.execute(
            """
            SELECT artifact_id, file_path
            FROM operation_approval_artifacts
            """
        ).fetchall()
        for row in rows:
            row_ref = {"artifact_id": str(row["artifact_id"])}
            plan = self._plan_managed_data_path(
                row["file_path"],
                field_name="operation_approval_artifacts.file_path",
            )
            if plan.fixable and plan.normalized_value:
                report.db_updates.append(
                    DatabaseUpdateAction(
                        table="operation_approval_artifacts",
                        where=row_ref,
                        values={"file_path": plan.normalized_value},
                        reason=plan.reason,
                    )
                )
            if plan.absolute_path is not None and plan.exists and plan.absolute_path.is_relative_to(self._uploads_root):
                referenced_uploads.add(plan.absolute_path)
            if not plan.exists:
                self._add_issue(
                    report,
                    category="missing_operation_approval_artifact",
                    table="operation_approval_artifacts",
                    row_ref=row_ref,
                    column="file_path",
                    raw_value=plan.raw_value,
                    normalized_value=plan.normalized_value,
                    path=plan.absolute_path,
                    reason=plan.reason,
                )
        return referenced_uploads

    def _plan_download_items(
        self,
        conn: sqlite3.Connection,
        report: ReconcileReport,
        *,
        table: str,
        root: Path,
        missing_file_category: str,
        missing_analysis_category: str,
        invalid_file_category: str,
        invalid_analysis_category: str,
    ) -> set[Path]:
        referenced_files: set[Path] = set()
        rows = conn.execute(
            f"""
            SELECT item_id, session_id, file_path, analysis_file_path,
                   added_doc_id, added_analysis_doc_id, ragflow_doc_id
            FROM {table}
            """
        ).fetchall()
        for row in rows:
            row_ref = {"session_id": str(row["session_id"]), "item_id": int(row["item_id"])}
            file_plan = self._plan_managed_data_path(
                row["file_path"],
                field_name=f"{table}.file_path",
            )
            analysis_plan = self._plan_managed_data_path(
                row["analysis_file_path"],
                field_name=f"{table}.analysis_file_path",
            )

            if file_plan.fixable and file_plan.normalized_value:
                report.db_updates.append(
                    DatabaseUpdateAction(
                        table=table,
                        where=row_ref,
                        values={"file_path": file_plan.normalized_value},
                        reason=file_plan.reason,
                    )
                )
            if analysis_plan.fixable and analysis_plan.normalized_value:
                report.db_updates.append(
                    DatabaseUpdateAction(
                        table=table,
                        where=row_ref,
                        values={"analysis_file_path": analysis_plan.normalized_value},
                        reason=analysis_plan.reason,
                    )
                )

            if file_plan.exists and file_plan.absolute_path is not None and file_plan.absolute_path.is_relative_to(root):
                referenced_files.add(file_plan.absolute_path)
            elif file_plan.raw_value:
                self._add_issue(
                    report,
                    category=(
                        invalid_file_category
                        if file_plan.normalized_value is None
                        else missing_file_category
                    ),
                    table=table,
                    row_ref=row_ref,
                    column="file_path",
                    raw_value=file_plan.raw_value,
                    normalized_value=file_plan.normalized_value,
                    path=file_plan.absolute_path,
                    reason=file_plan.reason,
                )

            if analysis_plan.exists and analysis_plan.absolute_path is not None and analysis_plan.absolute_path.is_relative_to(root):
                referenced_files.add(analysis_plan.absolute_path)
            elif analysis_plan.raw_value:
                self._add_issue(
                    report,
                    category=(
                        invalid_analysis_category
                        if analysis_plan.normalized_value is None
                        else missing_analysis_category
                    ),
                    table=table,
                    row_ref=row_ref,
                    column="analysis_file_path",
                    raw_value=analysis_plan.raw_value,
                    normalized_value=analysis_plan.normalized_value,
                    path=analysis_plan.absolute_path,
                    reason=analysis_plan.reason,
                )

            has_kb_link = any(
                str(row[column] or "").strip()
                for column in ("added_doc_id", "added_analysis_doc_id", "ragflow_doc_id")
            )
            if has_kb_link:
                continue
            if file_plan.exists or analysis_plan.exists:
                continue
            report.db_deletes.append(
                DatabaseDeleteAction(
                    table=table,
                    where=row_ref,
                    reason="derived_download_row_without_files_or_kb_links",
                )
            )
        return referenced_files

    def _plan_package_drawing_images(self, conn: sqlite3.Connection, report: ReconcileReport) -> set[Path]:
        referenced: set[Path] = set()
        rows = conn.execute(
            """
            SELECT image_id, source_type, rel_path
            FROM package_drawing_images
            """
        ).fetchall()
        for row in rows:
            row_ref = {"image_id": str(row["image_id"])}
            source_type = str(row["source_type"] or "").strip().lower()
            rel_path = str(row["rel_path"] or "").strip()
            if source_type == "url" and not rel_path:
                continue
            plan = self._plan_managed_child_path(
                rel_path,
                managed_root=self._package_drawing_root,
                field_name="package_drawing_images.rel_path",
            )
            if plan.fixable and plan.normalized_value:
                report.db_updates.append(
                    DatabaseUpdateAction(
                        table="package_drawing_images",
                        where=row_ref,
                        values={"rel_path": plan.normalized_value},
                        reason=plan.reason,
                    )
                )
            if plan.exists and plan.absolute_path is not None:
                referenced.add(plan.absolute_path)
            else:
                self._add_issue(
                    report,
                    category=(
                        "invalid_package_drawing_rel_path"
                        if plan.normalized_value is None
                        else "missing_package_drawing_file"
                    ),
                    table="package_drawing_images",
                    row_ref=row_ref,
                    column="rel_path",
                    raw_value=plan.raw_value,
                    normalized_value=plan.normalized_value,
                    path=plan.absolute_path,
                    reason=plan.reason,
                )
        return referenced

    def _plan_orphan_files(
        self,
        report: ReconcileReport,
        *,
        root: Path,
        referenced_paths: set[Path],
        file_reason: str,
        dir_reason: str,
    ) -> None:
        if not root.exists():
            return

        normalized_refs = {path.resolve() for path in referenced_paths}
        for path in sorted(root.rglob("*")):
            resolved = path.resolve()
            if path.is_file() and resolved not in normalized_refs:
                report.file_deletes.append(FileDeleteAction(path=str(resolved), reason=file_reason))

        planned_file_deletes = {Path(item.path).resolve() for item in report.file_deletes}
        planned_dir_deletes: set[Path] = set()
        for path in sorted(root.rglob("*"), key=lambda item: len(item.parts), reverse=True):
            if not path.is_dir():
                continue
            if path.resolve() == root.resolve():
                continue
            remaining_children = []
            for child in path.iterdir():
                child_resolved = child.resolve()
                if child.is_file() and child_resolved in planned_file_deletes:
                    continue
                if child.is_dir() and child_resolved in planned_dir_deletes:
                    continue
                remaining_children.append(child)
            if not remaining_children:
                report.dir_deletes.append(DirectoryDeleteAction(path=str(path.resolve()), reason=dir_reason))
                planned_dir_deletes.add(path.resolve())
