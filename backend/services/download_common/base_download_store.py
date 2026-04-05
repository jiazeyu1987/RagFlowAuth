from __future__ import annotations

import json
import time
from dataclasses import asdict
from typing import Any, Generic, Iterable, TypeVar

from backend.app.core.managed_paths import (
    resolve_managed_data_storage_path,
    to_managed_data_storage_path,
)
from backend.database.paths import resolve_auth_db_path
from backend.database.sqlite import connect_sqlite


SessionT = TypeVar("SessionT")
ItemT = TypeVar("ItemT")


class BaseDownloadStore(Generic[SessionT, ItemT]):
    SESSION_TABLE = ""
    ITEM_TABLE = ""
    SESSION_MODEL: type[SessionT] | None = None
    ITEM_MODEL: type[ItemT] | None = None
    CREATE_ITEM_ERROR = "create_download_item_failed"

    def __init__(self, db_path: str | None = None):
        self.db_path = resolve_auth_db_path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def _get_connection(self):
        return connect_sqlite(self.db_path)

    @staticmethod
    def _json_text(value: Any) -> str:
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))

    @staticmethod
    def _session_fields_sql() -> str:
        return (
            "session_id, created_by, created_at_ms, "
            "keyword_text, keywords_json, use_and, sources_json, "
            "COALESCE(status, 'completed') AS status, "
            "error, "
            "COALESCE(source_errors_json, '{}') AS source_errors_json, "
            "COALESCE(source_stats_json, '{}') AS source_stats_json"
        )

    @staticmethod
    def _item_fields_sql(prefix: str | None = None) -> str:
        pfx = f"{prefix}." if prefix else ""
        return (
            f"{pfx}item_id, {pfx}session_id, {pfx}source, {pfx}source_label, "
            f"{pfx}patent_id, {pfx}title, {pfx}abstract_text, "
            f"{pfx}publication_number, {pfx}publication_date, {pfx}inventor, {pfx}assignee, "
            f"{pfx}detail_url, {pfx}pdf_url, "
            f"{pfx}file_path, {pfx}filename, {pfx}file_size, {pfx}mime_type, "
            f"{pfx}status, {pfx}error, "
            f"{pfx}analysis_text, {pfx}analysis_file_path, "
            f"{pfx}added_doc_id, {pfx}added_analysis_doc_id, {pfx}ragflow_doc_id, {pfx}added_at_ms, "
            f"{pfx}created_at_ms"
        )

    def _to_session(self, row: Any) -> SessionT:
        if self.SESSION_MODEL is None:
            raise RuntimeError("SESSION_MODEL not configured")
        return self.SESSION_MODEL(
            session_id=str(row[0]),
            created_by=str(row[1]),
            created_at_ms=int(row[2]),
            keyword_text=str(row[3] or ""),
            keywords_json=str(row[4] or "[]"),
            use_and=bool(int(row[5] or 0)),
            sources_json=str(row[6] or "{}"),
            status=str(row[7] or "completed"),
            error=(str(row[8]) if row[8] is not None else None),
            source_errors_json=str(row[9] or "{}"),
            source_stats_json=str(row[10] or "{}"),
        )

    def _to_item(self, row: Any) -> ItemT:
        if self.ITEM_MODEL is None:
            raise RuntimeError("ITEM_MODEL not configured")
        data = list(row)
        data[13] = self._resolve_item_path(data[13], field_name=f"{self.ITEM_TABLE}.file_path")
        data[20] = self._resolve_item_path(
            data[20],
            field_name=f"{self.ITEM_TABLE}.analysis_file_path",
        )
        return self.ITEM_MODEL(*data)

    @staticmethod
    def _normalize_item_path(value: str | None, *, field_name: str) -> str | None:
        text = str(value or "").strip()
        if not text:
            return None
        return to_managed_data_storage_path(text, field_name=field_name)

    @staticmethod
    def _resolve_item_path(value: str | None, *, field_name: str) -> str | None:
        text = str(value or "").strip()
        if not text:
            return None
        return str(resolve_managed_data_storage_path(text, field_name=field_name))

    def create_session(
        self,
        *,
        session_id: str,
        created_by: str,
        keyword_text: str,
        keywords: list[str],
        use_and: bool,
        sources: dict[str, Any],
        created_at_ms: int | None = None,
        status: str = "running",
        error: str | None = None,
        source_errors: dict[str, Any] | None = None,
        source_stats: dict[str, Any] | None = None,
    ) -> SessionT:
        now_ms = int(created_at_ms or int(time.time() * 1000))
        keywords_json = self._json_text(keywords)
        sources_json = self._json_text(sources or {})
        source_errors_json = self._json_text(source_errors or {})
        source_stats_json = self._json_text(source_stats or {})

        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                f"""
                INSERT INTO {self.SESSION_TABLE} (
                    session_id, created_by, created_at_ms,
                    keyword_text, keywords_json, use_and, sources_json,
                    status, error, source_errors_json, source_stats_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    created_by,
                    now_ms,
                    keyword_text or "",
                    keywords_json,
                    1 if use_and else 0,
                    sources_json,
                    str(status or "running"),
                    error,
                    source_errors_json,
                    source_stats_json,
                ),
            )
            conn.commit()
            return self._to_session(
                (
                    session_id,
                    created_by,
                    now_ms,
                    keyword_text or "",
                    keywords_json,
                    1 if use_and else 0,
                    sources_json,
                    str(status or "running"),
                    error,
                    source_errors_json,
                    source_stats_json,
                )
            )
        finally:
            conn.close()

    def update_session_runtime(
        self,
        *,
        session_id: str,
        status: str | None = None,
        error: str | None = None,
        source_errors: dict[str, Any] | None = None,
        source_stats: dict[str, Any] | None = None,
    ) -> SessionT | None:
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            sets: list[str] = []
            values: list[Any] = []
            if status is not None:
                sets.append("status = ?")
                values.append(str(status))
            if error is not None:
                sets.append("error = ?")
                values.append(str(error))
            if source_errors is not None:
                sets.append("source_errors_json = ?")
                values.append(self._json_text(source_errors))
            if source_stats is not None:
                sets.append("source_stats_json = ?")
                values.append(self._json_text(source_stats))
            if not sets:
                return self.get_session(session_id)
            values.append(session_id)
            cursor.execute(
                f"""
                UPDATE {self.SESSION_TABLE}
                SET {", ".join(sets)}
                WHERE session_id = ?
                """,
                tuple(values),
            )
            conn.commit()
        finally:
            conn.close()
        return self.get_session(session_id)

    def create_item(
        self,
        *,
        session_id: str,
        item: dict[str, Any],
    ) -> ItemT:
        conn = self._get_connection()
        cursor = conn.cursor()
        now_ms = int(time.time() * 1000)
        try:
            cursor.execute(
                f"""
                INSERT INTO {self.ITEM_TABLE} (
                    session_id, source, source_label,
                    patent_id, title, abstract_text,
                    publication_number, publication_date, inventor, assignee,
                    detail_url, pdf_url,
                    file_path, filename, file_size, mime_type,
                    status, error,
                    analysis_text, analysis_file_path,
                    added_doc_id, added_analysis_doc_id, ragflow_doc_id, added_at_ms,
                    created_at_ms
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    str(item.get("source") or ""),
                    str(item.get("source_label") or item.get("source") or ""),
                    item.get("patent_id"),
                    item.get("title"),
                    item.get("abstract_text"),
                    item.get("publication_number"),
                    item.get("publication_date"),
                    item.get("inventor"),
                    item.get("assignee"),
                    item.get("detail_url"),
                    item.get("pdf_url"),
                    self._normalize_item_path(
                        item.get("file_path"),
                        field_name=f"{self.ITEM_TABLE}.file_path",
                    ),
                    item.get("filename"),
                    int(item["file_size"]) if item.get("file_size") is not None else None,
                    item.get("mime_type"),
                    str(item.get("status") or "downloaded"),
                    item.get("error"),
                    item.get("analysis_text"),
                    self._normalize_item_path(
                        item.get("analysis_file_path"),
                        field_name=f"{self.ITEM_TABLE}.analysis_file_path",
                    ),
                    item.get("added_doc_id"),
                    item.get("added_analysis_doc_id"),
                    item.get("ragflow_doc_id"),
                    int(item["added_at_ms"]) if item.get("added_at_ms") is not None else None,
                    int(item.get("created_at_ms") or now_ms),
                ),
            )
            row_id = int(cursor.lastrowid)
            conn.commit()
        finally:
            conn.close()

        created = self.get_item(session_id=session_id, item_id=row_id)
        if not created:
            raise RuntimeError(self.CREATE_ITEM_ERROR)
        return created

    def bulk_create_items(
        self,
        *,
        session_id: str,
        items: Iterable[dict[str, Any]],
    ) -> list[ItemT]:
        created: list[ItemT] = []
        for item in items:
            created.append(self.create_item(session_id=session_id, item=item))
        return created

    def get_session(self, session_id: str) -> SessionT | None:
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                f"""
                SELECT {self._session_fields_sql()}
                FROM {self.SESSION_TABLE}
                WHERE session_id = ?
                """,
                (session_id,),
            )
            row = cursor.fetchone()
            return self._to_session(row) if row else None
        finally:
            conn.close()

    def list_sessions_by_creator(self, *, created_by: str, limit: int = 500) -> list[SessionT]:
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                f"""
                SELECT {self._session_fields_sql()}
                FROM {self.SESSION_TABLE}
                WHERE created_by = ?
                ORDER BY created_at_ms DESC
                LIMIT ?
                """,
                (str(created_by), max(1, int(limit))),
            )
            rows = cursor.fetchall()
            return [self._to_session(row) for row in rows]
        finally:
            conn.close()

    def list_items(self, *, session_id: str) -> list[ItemT]:
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                f"""
                SELECT {self._item_fields_sql()}
                FROM {self.ITEM_TABLE}
                WHERE session_id = ?
                ORDER BY item_id ASC
                """,
                (session_id,),
            )
            rows = cursor.fetchall()
            return [self._to_item(row) for row in rows]
        finally:
            conn.close()

    def get_item(self, *, session_id: str, item_id: int) -> ItemT | None:
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                f"""
                SELECT {self._item_fields_sql()}
                FROM {self.ITEM_TABLE}
                WHERE session_id = ? AND item_id = ?
                LIMIT 1
                """,
                (session_id, int(item_id)),
            )
            row = cursor.fetchone()
            return self._to_item(row) if row else None
        finally:
            conn.close()

    def find_reusable_download(
        self,
        *,
        created_by: str,
        patent_id: str | None,
        publication_number: str | None,
        title: str | None,
    ) -> ItemT | None:
        keys: list[tuple[str, str]] = []
        for col, value in (
            ("i.patent_id", patent_id),
            ("i.publication_number", publication_number),
            ("i.title", title),
        ):
            v = str(value or "").strip()
            if v:
                keys.append((col, v))
        if not keys:
            return None

        where_expr = " OR ".join([f"{col} = ?" for col, _ in keys])
        params: list[Any] = [str(created_by)] + [v for _, v in keys]

        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                f"""
                SELECT {self._item_fields_sql(prefix='i')}
                FROM {self.ITEM_TABLE} i
                INNER JOIN {self.SESSION_TABLE} s ON s.session_id = i.session_id
                WHERE s.created_by = ?
                  AND i.status IN ('downloaded', 'downloaded_cached')
                  AND i.file_path IS NOT NULL
                  AND ({where_expr})
                ORDER BY i.created_at_ms DESC, i.item_id DESC
                LIMIT 1
                """,
                tuple(params),
            )
            row = cursor.fetchone()
            return self._to_item(row) if row else None
        finally:
            conn.close()

    def mark_item_added(
        self,
        *,
        session_id: str,
        item_id: int,
        added_doc_id: str,
        added_analysis_doc_id: str | None,
        ragflow_doc_id: str | None,
    ) -> ItemT | None:
        now_ms = int(time.time() * 1000)
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                f"""
                UPDATE {self.ITEM_TABLE}
                SET added_doc_id = ?, added_analysis_doc_id = ?, ragflow_doc_id = ?, added_at_ms = ?
                WHERE session_id = ? AND item_id = ?
                """,
                (added_doc_id, added_analysis_doc_id, ragflow_doc_id, now_ms, session_id, int(item_id)),
            )
            conn.commit()
            return self.get_item(session_id=session_id, item_id=item_id)
        finally:
            conn.close()

    def update_item_analysis(
        self,
        *,
        session_id: str,
        item_id: int,
        analysis_text: str | None,
        analysis_file_path: str | None,
    ) -> ItemT | None:
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                f"""
                UPDATE {self.ITEM_TABLE}
                SET analysis_text = ?, analysis_file_path = ?
                WHERE session_id = ? AND item_id = ?
                """,
                (
                    analysis_text,
                    self._normalize_item_path(
                        analysis_file_path,
                        field_name=f"{self.ITEM_TABLE}.analysis_file_path",
                    ),
                    session_id,
                    int(item_id),
                ),
            )
            conn.commit()
            return self.get_item(session_id=session_id, item_id=item_id)
        finally:
            conn.close()

    def delete_item(self, *, session_id: str, item_id: int) -> bool:
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                f"DELETE FROM {self.ITEM_TABLE} WHERE session_id = ? AND item_id = ?",
                (session_id, int(item_id)),
            )
            conn.commit()
            return int(cursor.rowcount or 0) > 0
        finally:
            conn.close()

    def delete_session(self, *, session_id: str) -> dict[str, int]:
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {self.ITEM_TABLE} WHERE session_id = ?", (session_id,))
            item_count = int(cursor.fetchone()[0] or 0)
            cursor.execute(f"DELETE FROM {self.ITEM_TABLE} WHERE session_id = ?", (session_id,))
            cursor.execute(f"DELETE FROM {self.SESSION_TABLE} WHERE session_id = ?", (session_id,))
            conn.commit()
            return {"deleted_items": item_count}
        finally:
            conn.close()


def _safe_json_load(text: str, default: Any) -> Any:
    try:
        return json.loads(text)
    except Exception:
        return default


def session_to_dict_common(session: Any) -> dict[str, Any]:
    out = asdict(session)
    out["use_and"] = bool(getattr(session, "use_and", False))
    out["keywords"] = _safe_json_load(str(getattr(session, "keywords_json", "[]") or "[]"), [])
    out["sources"] = _safe_json_load(str(getattr(session, "sources_json", "{}") or "{}"), {})
    out["source_errors"] = _safe_json_load(str(getattr(session, "source_errors_json", "{}") or "{}"), {})
    out["source_stats"] = _safe_json_load(str(getattr(session, "source_stats_json", "{}") or "{}"), {})
    return out


def item_to_dict_common(item: Any) -> dict[str, Any]:
    return asdict(item)
