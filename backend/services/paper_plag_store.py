from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from backend.database.paths import resolve_auth_db_path
from backend.database.sqlite import connect_sqlite


@dataclass
class PaperVersion:
    id: int
    paper_id: str
    version_no: int
    title: str
    content_hash: str | None
    content_text: str | None
    author_user_id: str
    note: str | None
    created_at_ms: int
    updated_at_ms: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "paper_id": self.paper_id,
            "version_no": self.version_no,
            "title": self.title,
            "content_hash": self.content_hash,
            "content_text": self.content_text,
            "author_user_id": self.author_user_id,
            "note": self.note,
            "created_at_ms": self.created_at_ms,
            "updated_at_ms": self.updated_at_ms,
        }


@dataclass
class PaperPlagReport:
    report_id: str
    paper_id: str
    version_id: int | None
    task_id: str | None
    status: str
    score: float
    duplicate_rate: float
    summary: str | None
    source_count: int
    report_file_path: str | None
    created_by_user_id: str
    created_at_ms: int
    updated_at_ms: int
    finished_at_ms: int | None

    def as_dict(self) -> dict[str, Any]:
        return {
            "report_id": self.report_id,
            "paper_id": self.paper_id,
            "version_id": self.version_id,
            "task_id": self.task_id,
            "status": self.status,
            "score": float(self.score),
            "duplicate_rate": float(self.duplicate_rate),
            "summary": self.summary,
            "source_count": int(self.source_count),
            "report_file_path": self.report_file_path,
            "created_by_user_id": self.created_by_user_id,
            "created_at_ms": int(self.created_at_ms),
            "updated_at_ms": int(self.updated_at_ms),
            "finished_at_ms": self.finished_at_ms,
        }


@dataclass
class PaperPlagHit:
    id: int
    report_id: str
    source_doc_id: str | None
    source_title: str | None
    source_uri: str | None
    similarity_score: float
    start_offset: int
    end_offset: int
    snippet_text: str | None
    created_at_ms: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "report_id": self.report_id,
            "source_doc_id": self.source_doc_id,
            "source_title": self.source_title,
            "source_uri": self.source_uri,
            "similarity_score": float(self.similarity_score),
            "start_offset": int(self.start_offset),
            "end_offset": int(self.end_offset),
            "snippet_text": self.snippet_text,
            "created_at_ms": int(self.created_at_ms),
        }


class PaperPlagStore:
    ACTIVE_STATUSES = {"pending", "running", "canceling"}

    def __init__(self, db_path: str | None = None):
        self.db_path = resolve_auth_db_path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def _conn(self):
        return connect_sqlite(self.db_path)

    @staticmethod
    def _safe_now_ms(now_ms: int | None = None) -> int:
        if now_ms is not None:
            try:
                return int(now_ms)
            except Exception:
                pass
        return int(time.time() * 1000)

    @classmethod
    def _version_from_row(cls, row: Any) -> PaperVersion:
        return PaperVersion(
            id=int(row["id"] or 0),
            paper_id=str(row["paper_id"] or ""),
            version_no=int(row["version_no"] or 1),
            title=str(row["title"] or ""),
            content_hash=(str(row["content_hash"]) if row["content_hash"] is not None else None),
            content_text=(str(row["content_text"]) if row["content_text"] is not None else None),
            author_user_id=str(row["author_user_id"] or ""),
            note=(str(row["note"]) if row["note"] is not None else None),
            created_at_ms=int(row["created_at_ms"] or 0),
            updated_at_ms=int(row["updated_at_ms"] or 0),
        )

    @classmethod
    def _report_from_row(cls, row: Any) -> PaperPlagReport:
        return PaperPlagReport(
            report_id=str(row["report_id"] or ""),
            paper_id=str(row["paper_id"] or ""),
            version_id=(int(row["version_id"]) if row["version_id"] is not None else None),
            task_id=(str(row["task_id"]) if row["task_id"] is not None else None),
            status=str(row["status"] or "pending"),
            score=float(row["score"] or 0.0),
            duplicate_rate=float(row["duplicate_rate"] or 0.0),
            summary=(str(row["summary"]) if row["summary"] is not None else None),
            source_count=int(row["source_count"] or 0),
            report_file_path=(str(row["report_file_path"]) if row["report_file_path"] is not None else None),
            created_by_user_id=str(row["created_by_user_id"] or ""),
            created_at_ms=int(row["created_at_ms"] or 0),
            updated_at_ms=int(row["updated_at_ms"] or 0),
            finished_at_ms=(int(row["finished_at_ms"]) if row["finished_at_ms"] is not None else None),
        )

    @classmethod
    def _hit_from_row(cls, row: Any) -> PaperPlagHit:
        return PaperPlagHit(
            id=int(row["id"] or 0),
            report_id=str(row["report_id"] or ""),
            source_doc_id=(str(row["source_doc_id"]) if row["source_doc_id"] is not None else None),
            source_title=(str(row["source_title"]) if row["source_title"] is not None else None),
            source_uri=(str(row["source_uri"]) if row["source_uri"] is not None else None),
            similarity_score=float(row["similarity_score"] or 0.0),
            start_offset=int(row["start_offset"] or 0),
            end_offset=int(row["end_offset"] or 0),
            snippet_text=(str(row["snippet_text"]) if row["snippet_text"] is not None else None),
            created_at_ms=int(row["created_at_ms"] or 0),
        )

    def create_version(
        self,
        *,
        paper_id: str,
        title: str,
        content_text: str,
        content_hash: str | None,
        author_user_id: str,
        note: str | None = None,
    ) -> PaperVersion:
        normalized_paper_id = str(paper_id or "").strip()
        if not normalized_paper_id:
            raise RuntimeError("paper_id_required")
        now_ms = self._safe_now_ms()
        conn = self._conn()
        try:
            row = conn.execute(
                "SELECT MAX(version_no) AS max_version_no FROM paper_versions WHERE paper_id = ?",
                (normalized_paper_id,),
            ).fetchone()
            next_version_no = int((row["max_version_no"] if row is not None else 0) or 0) + 1
            conn.execute(
                """
                INSERT INTO paper_versions (
                    paper_id, version_no, title, content_hash, content_text, author_user_id, note, created_at_ms, updated_at_ms
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    normalized_paper_id,
                    next_version_no,
                    str(title or ""),
                    content_hash,
                    str(content_text or ""),
                    str(author_user_id or ""),
                    note,
                    now_ms,
                    now_ms,
                ),
            )
            conn.commit()
            created = conn.execute(
                "SELECT * FROM paper_versions WHERE paper_id = ? AND version_no = ?",
                (normalized_paper_id, next_version_no),
            ).fetchone()
            if created is None:
                raise RuntimeError("create_paper_version_failed")
            return self._version_from_row(created)
        finally:
            conn.close()

    def get_version(self, version_id: int) -> PaperVersion | None:
        try:
            normalized_version_id = int(version_id)
        except Exception:
            return None
        if normalized_version_id <= 0:
            return None
        conn = self._conn()
        try:
            row = conn.execute(
                "SELECT * FROM paper_versions WHERE id = ?",
                (normalized_version_id,),
            ).fetchone()
            return self._version_from_row(row) if row is not None else None
        finally:
            conn.close()

    def list_versions(self, *, paper_id: str, limit: int = 50) -> list[PaperVersion]:
        normalized_paper_id = str(paper_id or "").strip()
        if not normalized_paper_id:
            return []
        safe_limit = max(1, min(int(limit or 50), 2000))
        conn = self._conn()
        try:
            rows = conn.execute(
                """
                SELECT *
                FROM paper_versions
                WHERE paper_id = ?
                ORDER BY version_no DESC, id DESC
                LIMIT ?
                """,
                (normalized_paper_id, safe_limit),
            ).fetchall()
            return [self._version_from_row(row) for row in rows or []]
        finally:
            conn.close()

    def create_report(
        self,
        *,
        report_id: str,
        paper_id: str,
        version_id: int | None,
        task_id: str,
        status: str,
        created_by_user_id: str,
        score: float = 0.0,
        duplicate_rate: float = 0.0,
        summary: str | None = None,
        source_count: int = 0,
        report_file_path: str | None = None,
        created_at_ms: int | None = None,
        updated_at_ms: int | None = None,
        finished_at_ms: int | None = None,
    ) -> PaperPlagReport:
        now_ms = self._safe_now_ms()
        created_ms = self._safe_now_ms(created_at_ms) if created_at_ms is not None else now_ms
        updated_ms = self._safe_now_ms(updated_at_ms) if updated_at_ms is not None else now_ms
        conn = self._conn()
        try:
            conn.execute(
                """
                INSERT INTO paper_plag_reports (
                    report_id, paper_id, version_id, task_id, status,
                    score, duplicate_rate, summary, source_count, report_file_path,
                    created_by_user_id, created_at_ms, updated_at_ms, finished_at_ms
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(report_id or ""),
                    str(paper_id or ""),
                    version_id,
                    str(task_id or ""),
                    str(status or "pending"),
                    float(score or 0.0),
                    float(duplicate_rate or 0.0),
                    summary,
                    int(source_count or 0),
                    report_file_path,
                    str(created_by_user_id or ""),
                    int(created_ms),
                    int(updated_ms),
                    (int(finished_at_ms) if finished_at_ms is not None else None),
                ),
            )
            conn.commit()
        finally:
            conn.close()
        report = self.get_report(str(report_id or ""))
        if report is None:
            raise RuntimeError("create_paper_plag_report_failed")
        return report

    def get_report(self, report_id: str) -> PaperPlagReport | None:
        conn = self._conn()
        try:
            row = conn.execute(
                "SELECT * FROM paper_plag_reports WHERE report_id = ?",
                (str(report_id or ""),),
            ).fetchone()
            return self._report_from_row(row) if row is not None else None
        finally:
            conn.close()

    def list_reports(
        self,
        *,
        limit: int = 100,
        statuses: list[str] | None = None,
        paper_id: str | None = None,
    ) -> list[PaperPlagReport]:
        safe_limit = max(1, min(int(limit or 100), 2000))
        normalized_statuses = [str(item or "").strip() for item in (statuses or []) if str(item or "").strip()]
        conn = self._conn()
        try:
            query = "SELECT * FROM paper_plag_reports WHERE 1=1"
            params: list[Any] = []
            if normalized_statuses:
                placeholders = ", ".join(["?"] * len(normalized_statuses))
                query += f" AND status IN ({placeholders})"
                params.extend(normalized_statuses)
            normalized_paper_id = str(paper_id or "").strip()
            if normalized_paper_id:
                query += " AND paper_id = ?"
                params.append(normalized_paper_id)
            query += " ORDER BY updated_at_ms DESC LIMIT ?"
            params.append(safe_limit)
            rows = conn.execute(query, params).fetchall()
            return [self._report_from_row(row) for row in rows or []]
        finally:
            conn.close()

    def update_report(self, report_id: str, **updates) -> PaperPlagReport | None:
        normalized_report_id = str(report_id or "").strip()
        if not normalized_report_id:
            return None
        if not updates:
            return self.get_report(normalized_report_id)
        update_map = dict(updates)
        if "updated_at_ms" not in update_map:
            update_map["updated_at_ms"] = self._safe_now_ms()
        set_clause = ", ".join(f"{key} = ?" for key in update_map.keys())
        params = [update_map[key] for key in update_map.keys()]
        params.append(normalized_report_id)
        conn = self._conn()
        try:
            conn.execute(
                f"UPDATE paper_plag_reports SET {set_clause} WHERE report_id = ?",
                params,
            )
            conn.commit()
        finally:
            conn.close()
        return self.get_report(normalized_report_id)

    def request_cancel_report(self, report_id: str) -> PaperPlagReport | None:
        current = self.get_report(report_id)
        if current is None:
            return None
        status = str(current.status or "").strip().lower()
        if status in ("completed", "failed", "canceled"):
            return current
        now_ms = self._safe_now_ms()
        if status == "pending":
            return self.update_report(
                report_id,
                status="canceled",
                finished_at_ms=now_ms,
                summary=current.summary or "canceled_before_start",
            )
        if status in ("running", "canceling"):
            return self.update_report(report_id, status="canceling")
        return current

    def replace_hits(self, *, report_id: str, hits: list[dict[str, Any]]) -> None:
        now_ms = self._safe_now_ms()
        conn = self._conn()
        try:
            conn.execute(
                "DELETE FROM paper_plag_hits WHERE report_id = ?",
                (str(report_id or ""),),
            )
            for item in hits or []:
                conn.execute(
                    """
                    INSERT INTO paper_plag_hits (
                        report_id, source_doc_id, source_title, source_uri,
                        similarity_score, start_offset, end_offset, snippet_text, created_at_ms
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(report_id or ""),
                        item.get("source_doc_id"),
                        item.get("source_title"),
                        item.get("source_uri"),
                        float(item.get("similarity_score") or 0.0),
                        int(item.get("start_offset") or 0),
                        int(item.get("end_offset") or 0),
                        item.get("snippet_text"),
                        int(item.get("created_at_ms") or now_ms),
                    ),
                )
            conn.commit()
        finally:
            conn.close()

    def list_hits(self, *, report_id: str, limit: int = 200) -> list[PaperPlagHit]:
        safe_limit = max(1, min(int(limit or 200), 5000))
        conn = self._conn()
        try:
            rows = conn.execute(
                """
                SELECT *
                FROM paper_plag_hits
                WHERE report_id = ?
                ORDER BY similarity_score DESC, id ASC
                LIMIT ?
                """,
                (str(report_id or ""), safe_limit),
            ).fetchall()
            return [self._hit_from_row(row) for row in rows or []]
        finally:
            conn.close()
