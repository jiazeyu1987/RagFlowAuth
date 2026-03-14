from __future__ import annotations

import asyncio
import difflib
import hashlib
import logging
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.app.core.config import settings
from backend.services.paper_plag_store import PaperPlagStore

logger = logging.getLogger(__name__)

_TOKEN_RE = re.compile(r"[A-Za-z0-9_]{2,}|[\u4e00-\u9fff]")
_PLAG_TASK_LOCK = asyncio.Lock()
_PLAG_RUNNING_REPORTS: set[str] = set()
_PLAG_QUEUE: list[tuple[int, str, dict[str, Any]]] = []


def _normalize_threshold(value: Any) -> float:
    try:
        normalized = float(value)
    except Exception:
        normalized = 0.2
    return max(0.0, min(normalized, 1.0))


def _normalize_priority(value: Any) -> int:
    try:
        normalized = int(value)
    except Exception:
        normalized = 100
    return max(1, min(normalized, 1000))


def _tokenize(text: str) -> set[str]:
    raw = str(text or "")
    tokens = {token.strip().lower() for token in _TOKEN_RE.findall(raw) if token and token.strip()}
    return {item for item in tokens if item}


def _jaccard_similarity(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    inter = len(left & right)
    union = len(left | right)
    if union <= 0:
        return 0.0
    return max(0.0, min(float(inter) / float(union), 1.0))


class PaperPlagiarismService:
    TASK_KIND = "paper_plagiarism"
    _ACTIVE_STATUSES = {"pending", "running", "canceling"}

    def __init__(self, *, store: PaperPlagStore | None = None):
        self.store = store or PaperPlagStore()

    @staticmethod
    def _concurrency_limit() -> int:
        try:
            value = int(getattr(settings, "TASK_PAPER_PLAG_CONCURRENCY_LIMIT", 1) or 1)
        except Exception:
            value = 1
        return max(1, min(value, 32))

    @staticmethod
    def _content_hash(content_text: str) -> str:
        return hashlib.sha256(str(content_text or "").encode("utf-8")).hexdigest()

    @staticmethod
    def _now_utc_text() -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    def _build_hits(
        self,
        *,
        content_text: str,
        sources: list[dict[str, Any]],
        threshold: float,
    ) -> tuple[list[dict[str, Any]], float]:
        target_tokens = _tokenize(content_text)
        max_similarity = 0.0
        hits: list[dict[str, Any]] = []
        for item in sources or []:
            source_text = str(item.get("content_text") or "")
            source_tokens = _tokenize(source_text)
            similarity = _jaccard_similarity(target_tokens, source_tokens)
            max_similarity = max(max_similarity, similarity)
            if similarity < threshold:
                continue
            snippet = source_text.strip().replace("\n", " ")
            if len(snippet) > 200:
                snippet = f"{snippet[:200]}..."
            hits.append(
                {
                    "source_doc_id": str(item.get("source_doc_id") or ""),
                    "source_title": str(item.get("source_title") or ""),
                    "source_uri": str(item.get("source_uri") or ""),
                    "similarity_score": round(similarity, 4),
                    "start_offset": 0,
                    "end_offset": min(len(source_text), len(snippet)),
                    "snippet_text": snippet,
                }
            )
        return hits, round(max_similarity, 4)

    def _build_summary(self, *, duplicate_rate: float, source_count: int) -> str:
        similarity_pct = round(float(duplicate_rate) * 100.0, 2)
        originality_pct = round(max(0.0, 100.0 - similarity_pct), 2)
        return f"max_similarity={similarity_pct}%, originality_score={originality_pct}, matched_sources={int(source_count)}"

    async def _drain_queue(self) -> None:
        limit = self._concurrency_limit()
        while True:
            next_payload: dict[str, Any] | None = None
            async with _PLAG_TASK_LOCK:
                if len(_PLAG_RUNNING_REPORTS) >= limit:
                    return
                if not _PLAG_QUEUE:
                    return
                _PLAG_QUEUE.sort(key=lambda item: (item[0], item[1]))
                _priority, report_id, payload = _PLAG_QUEUE.pop(0)
                if report_id in _PLAG_RUNNING_REPORTS:
                    continue
                _PLAG_RUNNING_REPORTS.add(report_id)
                next_payload = payload
            if next_payload is None:
                return
            asyncio.create_task(self._run_report_task(**next_payload))

    async def _run_report_task(
        self,
        *,
        report_id: str,
        content_text: str,
        sources: list[dict[str, Any]],
        similarity_threshold: float,
    ) -> None:
        try:
            current = self.store.get_report(report_id)
            if current is None:
                return
            if str(current.status or "").strip().lower() in ("canceled", "canceling"):
                now_ms = int(asyncio.get_running_loop().time() * 1000)
                self.store.update_report(
                    report_id,
                    status="canceled",
                    finished_at_ms=now_ms,
                    summary=current.summary or "canceled_before_start",
                )
                return

            self.store.update_report(report_id, status="running")
            await asyncio.sleep(0)
            hits, duplicate_rate = self._build_hits(
                content_text=content_text,
                sources=sources,
                threshold=similarity_threshold,
            )

            check = self.store.get_report(report_id)
            if check is not None and str(check.status or "").strip().lower() == "canceling":
                self.store.update_report(
                    report_id,
                    status="canceled",
                    finished_at_ms=int(asyncio.get_running_loop().time() * 1000),
                    summary=check.summary or "canceled_while_running",
                )
                return

            self.store.replace_hits(report_id=report_id, hits=hits)
            originality_score = round(max(0.0, 100.0 - float(duplicate_rate) * 100.0), 2)
            self.store.update_report(
                report_id,
                status="completed",
                score=originality_score,
                duplicate_rate=duplicate_rate,
                source_count=len(hits),
                summary=self._build_summary(duplicate_rate=duplicate_rate, source_count=len(hits)),
                finished_at_ms=int(asyncio.get_running_loop().time() * 1000),
            )
        except Exception as exc:
            logger.exception("paper_plag_task_failed report_id=%s err=%s", report_id, exc)
            self.store.update_report(
                report_id,
                status="failed",
                summary=f"paper_plag_task_failed: {exc}",
                finished_at_ms=int(asyncio.get_running_loop().time() * 1000),
            )
        finally:
            async with _PLAG_TASK_LOCK:
                _PLAG_RUNNING_REPORTS.discard(str(report_id or ""))
            await self._drain_queue()

    async def start_report(
        self,
        *,
        actor_user_id: str,
        paper_id: str,
        title: str,
        content_text: str,
        note: str | None,
        sources: list[dict[str, Any]] | None,
        similarity_threshold: float,
        priority: int | None = None,
    ) -> dict[str, Any]:
        normalized_content = str(content_text or "")
        if not normalized_content.strip():
            raise RuntimeError("paper_content_required")
        normalized_paper_id = str(paper_id or "").strip()
        if not normalized_paper_id:
            raise RuntimeError("paper_id_required")

        version = self.store.create_version(
            paper_id=normalized_paper_id,
            title=str(title or ""),
            content_text=normalized_content,
            content_hash=self._content_hash(normalized_content),
            author_user_id=str(actor_user_id or ""),
            note=note,
        )
        report_id = str(uuid.uuid4().hex)
        report = self.store.create_report(
            report_id=report_id,
            paper_id=normalized_paper_id,
            version_id=int(version.id),
            task_id=report_id,
            status="pending",
            created_by_user_id=str(actor_user_id or ""),
        )
        payload = {
            "report_id": report_id,
            "content_text": normalized_content,
            "sources": list(sources or []),
            "similarity_threshold": _normalize_threshold(similarity_threshold),
        }
        async with _PLAG_TASK_LOCK:
            _PLAG_QUEUE.append((_normalize_priority(priority), report_id, payload))
            if len(_PLAG_QUEUE) > 10000:
                _PLAG_QUEUE[:] = _PLAG_QUEUE[-10000:]
        await self._drain_queue()
        return {
            "report": report.as_dict(),
            "hits": [],
        }

    def get_report(self, report_id: str) -> dict[str, Any]:
        report = self.store.get_report(str(report_id or "").strip())
        if report is None:
            raise RuntimeError("report_not_found")
        hits = self.store.list_hits(report_id=report.report_id, limit=2000)
        return {
            "report": report.as_dict(),
            "hits": [item.as_dict() for item in hits],
        }

    def list_reports(
        self,
        *,
        limit: int = 50,
        paper_id: str | None = None,
        statuses: list[str] | None = None,
    ) -> dict[str, Any]:
        reports = self.store.list_reports(limit=limit, statuses=statuses, paper_id=paper_id)
        return {
            "total": len(reports),
            "items": [item.as_dict() for item in reports],
        }

    def save_version(
        self,
        *,
        actor_user_id: str,
        paper_id: str,
        title: str,
        content_text: str,
        note: str | None = None,
    ) -> dict[str, Any]:
        normalized_paper_id = str(paper_id or "").strip()
        normalized_content = str(content_text or "")
        if not normalized_paper_id:
            raise RuntimeError("paper_id_required")
        if not normalized_content.strip():
            raise RuntimeError("paper_content_required")
        version = self.store.create_version(
            paper_id=normalized_paper_id,
            title=str(title or ""),
            content_text=normalized_content,
            content_hash=self._content_hash(normalized_content),
            author_user_id=str(actor_user_id or ""),
            note=note,
        )
        return {"version": version.as_dict()}

    def list_versions(self, *, paper_id: str, limit: int = 50) -> dict[str, Any]:
        normalized_paper_id = str(paper_id or "").strip()
        if not normalized_paper_id:
            raise RuntimeError("paper_id_required")
        versions = self.store.list_versions(paper_id=normalized_paper_id, limit=limit)
        return {
            "paper_id": normalized_paper_id,
            "total": len(versions),
            "items": [item.as_dict() for item in versions],
        }

    def get_version(self, *, paper_id: str, version_id: int) -> dict[str, Any]:
        normalized_paper_id = str(paper_id or "").strip()
        if not normalized_paper_id:
            raise RuntimeError("paper_id_required")
        version = self.store.get_version(version_id)
        if version is None or str(version.paper_id or "") != normalized_paper_id:
            raise RuntimeError("paper_version_not_found")
        return {"version": version.as_dict()}

    @staticmethod
    def _build_diff_payload(*, from_text: str, to_text: str) -> dict[str, Any]:
        from_lines = str(from_text or "").splitlines()
        to_lines = str(to_text or "").splitlines()
        matcher = difflib.SequenceMatcher(a=from_lines, b=to_lines)
        added_lines = 0
        removed_lines = 0
        changed_blocks = 0
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == "insert":
                added_lines += max(j2 - j1, 0)
                changed_blocks += 1
            elif tag == "delete":
                removed_lines += max(i2 - i1, 0)
                changed_blocks += 1
            elif tag == "replace":
                removed_lines += max(i2 - i1, 0)
                added_lines += max(j2 - j1, 0)
                changed_blocks += 1
        diff_lines = list(
            difflib.unified_diff(
                from_lines,
                to_lines,
                fromfile="from_version",
                tofile="to_version",
                lineterm="",
            )
        )
        return {
            "added_lines": int(added_lines),
            "removed_lines": int(removed_lines),
            "changed_blocks": int(changed_blocks),
            "diff_preview": diff_lines[:200],
        }

    def compare_versions(
        self,
        *,
        paper_id: str,
        from_version_id: int,
        to_version_id: int,
    ) -> dict[str, Any]:
        normalized_paper_id = str(paper_id or "").strip()
        if not normalized_paper_id:
            raise RuntimeError("paper_id_required")
        from_version = self.store.get_version(from_version_id)
        to_version = self.store.get_version(to_version_id)
        if from_version is None or to_version is None:
            raise RuntimeError("paper_version_not_found")
        if (
            str(from_version.paper_id or "") != normalized_paper_id
            or str(to_version.paper_id or "") != normalized_paper_id
        ):
            raise RuntimeError("paper_version_not_found")
        diff_payload = self._build_diff_payload(
            from_text=str(from_version.content_text or ""),
            to_text=str(to_version.content_text or ""),
        )
        return {
            "paper_id": normalized_paper_id,
            "from_version": from_version.as_dict(),
            "to_version": to_version.as_dict(),
            **diff_payload,
        }

    def rollback_version(
        self,
        *,
        actor_user_id: str,
        paper_id: str,
        version_id: int,
        note: str | None = None,
    ) -> dict[str, Any]:
        normalized_paper_id = str(paper_id or "").strip()
        if not normalized_paper_id:
            raise RuntimeError("paper_id_required")
        source = self.store.get_version(version_id)
        if source is None or str(source.paper_id or "") != normalized_paper_id:
            raise RuntimeError("paper_version_not_found")
        rollback_note = str(note or "").strip()
        if rollback_note:
            rollback_note = f"rollback_from_version={int(source.version_no)}; {rollback_note}"
        else:
            rollback_note = f"rollback_from_version={int(source.version_no)}"
        restored = self.store.create_version(
            paper_id=normalized_paper_id,
            title=str(source.title or ""),
            content_text=str(source.content_text or ""),
            content_hash=str(source.content_hash or "") or self._content_hash(str(source.content_text or "")),
            author_user_id=str(actor_user_id or ""),
            note=rollback_note,
        )
        return {
            "paper_id": normalized_paper_id,
            "restored_from": source.as_dict(),
            "version": restored.as_dict(),
        }

    def export_report(self, report_id: str, *, file_format: str = "md") -> dict[str, Any]:
        normalized_report_id = str(report_id or "").strip()
        if not normalized_report_id:
            raise RuntimeError("report_id_required")
        report_payload = self.get_report(normalized_report_id)
        report = report_payload["report"]
        hits = report_payload["hits"]
        normalized_format = str(file_format or "md").strip().lower()
        if normalized_format not in {"md", "markdown", "txt"}:
            raise RuntimeError("unsupported_export_format")

        lines: list[str] = []
        lines.append("# Paper Plagiarism Report")
        lines.append("")
        lines.append(f"- exported_at: {self._now_utc_text()}")
        lines.append(f"- report_id: {report.get('report_id')}")
        lines.append(f"- paper_id: {report.get('paper_id')}")
        lines.append(f"- status: {report.get('status')}")
        lines.append(f"- duplicate_rate: {round(float(report.get('duplicate_rate') or 0.0) * 100.0, 2)}%")
        lines.append(f"- originality_score: {report.get('score')}")
        lines.append(f"- source_count: {report.get('source_count')}")
        lines.append("")
        lines.append("## Summary")
        lines.append("")
        lines.append(str(report.get("summary") or ""))
        lines.append("")
        lines.append("## Similarity Hits")
        lines.append("")
        if not hits:
            lines.append("- no matched hits")
        else:
            for idx, hit in enumerate(hits, start=1):
                lines.append(f"### Hit #{idx}")
                lines.append(f"- source_doc_id: {hit.get('source_doc_id')}")
                lines.append(f"- source_title: {hit.get('source_title')}")
                lines.append(f"- source_uri: {hit.get('source_uri')}")
                lines.append(f"- similarity_score: {hit.get('similarity_score')}")
                lines.append(f"- range: [{hit.get('start_offset')}, {hit.get('end_offset')}]")
                lines.append(f"- snippet: {hit.get('snippet_text')}")
                lines.append("")

        rendered = "\n".join(lines).strip() + "\n"
        db_path = Path(str(getattr(self.store, "db_path", "") or "data/auth.db"))
        report_dir = db_path.parent / "paper_plag_reports"
        report_dir.mkdir(parents=True, exist_ok=True)
        ext = "txt" if normalized_format == "txt" else "md"
        filename = f"paper_plag_report_{normalized_report_id}.{ext}"
        file_path = report_dir / filename
        file_path.write_text(rendered, encoding="utf-8")
        self.store.update_report(normalized_report_id, report_file_path=str(file_path))
        refreshed = self.get_report(normalized_report_id)
        return {
            "report": refreshed["report"],
            "hits": refreshed["hits"],
            "report_file_path": str(file_path),
            "filename": filename,
            "content_type": "text/plain; charset=utf-8",
            "content": rendered,
            "format": ext,
        }

    async def cancel_report(self, report_id: str) -> dict[str, Any]:
        report = self.store.request_cancel_report(report_id)
        if report is None:
            raise RuntimeError("report_not_found")
        if str(report.status or "").strip().lower() == "canceling":
            async with _PLAG_TASK_LOCK:
                running = str(report.report_id or "") in _PLAG_RUNNING_REPORTS
            if not running:
                report = self.store.update_report(
                    report.report_id,
                    status="canceled",
                    finished_at_ms=int(asyncio.get_running_loop().time() * 1000),
                    summary=report.summary or "canceled",
                ) or report
        return self.get_report(report.report_id)
