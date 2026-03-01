from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fastapi import HTTPException


@dataclass
class DownloadHistoryManager:
    owner: Any

    def _sessions_by_actor(self, actor: str) -> list[Any]:
        return self.owner.store.list_sessions_by_creator(created_by=str(actor), limit=1000)

    def _group_sessions(self, sessions: list[Any]) -> tuple[dict[str, dict[str, Any]], dict[str, list[Any]]]:
        grouped: dict[str, dict[str, Any]] = {}
        grouped_sessions: dict[str, list[Any]] = {}
        for session in sessions:
            key, keywords, use_and = self.owner._history_group_from_session(session)
            if not keywords:
                continue
            grouped_sessions.setdefault(key, []).append(session)
            node = grouped.get(key)
            if not node:
                node = {
                    "history_key": key,
                    "keywords": keywords,
                    "use_and": bool(use_and),
                    "keyword_display": f" {'AND' if use_and else 'OR'} ".join(keywords),
                    "latest_session_id": session.session_id,
                    "latest_at_ms": int(session.created_at_ms),
                    "session_count": 0,
                }
                grouped[key] = node
            node["session_count"] = int(node["session_count"]) + 1
            if int(session.created_at_ms) >= int(node["latest_at_ms"]):
                node["latest_at_ms"] = int(session.created_at_ms)
                node["latest_session_id"] = session.session_id
        return grouped, grouped_sessions

    def _merge_items(self, sessions: list[Any]) -> list[Any]:
        merged: dict[str, Any] = {}
        for session in sorted(sessions, key=lambda x: int(x.created_at_ms), reverse=True):
            for item in self.owner.store.list_items(session_id=session.session_id):
                key = self.owner._history_item_key(item)
                existing = merged.get(key)
                if existing is None or int(getattr(item, "created_at_ms", 0) or 0) >= int(getattr(existing, "created_at_ms", 0) or 0):
                    merged[key] = item
        return list(merged.values())

    def list_history_keywords(self, *, ctx: Any) -> dict[str, Any]:
        actor = str(ctx.payload.sub)
        sessions = self._sessions_by_actor(actor)
        grouped, grouped_sessions = self._group_sessions(sessions)

        for key, node in grouped.items():
            merged_items = self._merge_items(grouped_sessions.get(key, []))
            downloaded_count = sum(1 for item in merged_items if self.owner._is_downloaded_status(getattr(item, "status", None)))
            analyzed_count = sum(
                1
                for item in merged_items
                if self.owner._has_effective_analysis_text(getattr(item, "analysis_text", None))
            )
            added_count = sum(1 for item in merged_items if bool(getattr(item, "added_doc_id", None)))
            node["downloaded_count"] = int(downloaded_count)
            node["analyzed_count"] = int(analyzed_count)
            node["added_count"] = int(added_count)

        history = sorted(grouped.values(), key=lambda x: int(x.get("latest_at_ms", 0)), reverse=True)
        return {"history": history, "count": len(history)}

    def get_history_group_payload(self, *, history_key: str, ctx: Any) -> dict[str, Any]:
        actor = str(ctx.payload.sub)
        sessions = self._sessions_by_actor(actor)

        target_sessions: list[Any] = []
        target_meta: dict[str, Any] | None = None
        for session in sessions:
            key, keywords, use_and = self.owner._history_group_from_session(session)
            if key != str(history_key):
                continue
            target_sessions.append(session)
            if target_meta is None or int(session.created_at_ms) >= int(target_meta.get("latest_at_ms", 0)):
                target_meta = {
                    "history_key": key,
                    "keywords": keywords,
                    "use_and": bool(use_and),
                    "keyword_display": f" {'AND' if use_and else 'OR'} ".join(keywords),
                    "latest_session_id": session.session_id,
                    "latest_at_ms": int(session.created_at_ms),
                }
        if not target_sessions:
            raise HTTPException(status_code=404, detail="history_keyword_not_found")

        merged_items = sorted(
            self._merge_items(target_sessions),
            key=lambda x: int(getattr(x, "created_at_ms", 0) or 0),
            reverse=True,
        )
        return {
            "history": {
                **(target_meta or {}),
                "session_count": len(target_sessions),
                "item_count": len(merged_items),
            },
            "items": [self.owner._serialize_item(item) for item in merged_items],
            "summary": {
                "total": len(merged_items),
                "downloaded": sum(1 for item in merged_items if self.owner._is_downloaded_status(getattr(item, "status", None))),
                "failed": sum(1 for item in merged_items if not self.owner._is_downloaded_status(getattr(item, "status", None))),
            },
        }

    def delete_history_group(self, *, history_key: str, ctx: Any) -> dict[str, Any]:
        actor = str(ctx.payload.sub)
        sessions = self._sessions_by_actor(actor)
        target_session_ids: list[str] = []
        for session in sessions:
            key, _, _ = self.owner._history_group_from_session(session)
            if key == str(history_key):
                target_session_ids.append(str(session.session_id))
        if not target_session_ids:
            raise HTTPException(status_code=404, detail="history_keyword_not_found")

        deleted_sessions = 0
        deleted_items = 0
        deleted_files = 0
        errors: list[dict[str, Any]] = []
        for session_id in target_session_ids:
            try:
                result = self.owner.delete_session(session_id=session_id, ctx=ctx, delete_local_kb=False)
                deleted_sessions += 1
                deleted_items += int(result.get("deleted_items", 0) or 0)
                deleted_files += int(result.get("deleted_files", 0) or 0)
            except Exception as e:
                errors.append({"session_id": session_id, "error": str(e)})

        return {
            "ok": True,
            "history_key": str(history_key),
            "deleted_sessions": deleted_sessions,
            "deleted_items": deleted_items,
            "deleted_files": deleted_files,
            "errors": errors,
        }

    def add_history_group_to_local_kb(self, *, history_key: str, ctx: Any, kb_ref: str) -> dict[str, Any]:
        actor = str(ctx.payload.sub)
        sessions = self._sessions_by_actor(actor)
        target_sessions: list[Any] = []
        for session in sessions:
            key, _, _ = self.owner._history_group_from_session(session)
            if key == str(history_key):
                target_sessions.append(session)
        if not target_sessions:
            raise HTTPException(status_code=404, detail="history_keyword_not_found")

        merged_items = self._merge_items(target_sessions)
        success = 0
        failed = 0
        skipped = 0
        details: list[dict[str, Any]] = []
        for item in merged_items:
            if not self.owner._is_downloaded_status(getattr(item, "status", None)):
                skipped += 1
                details.append(
                    {
                        "session_id": item.session_id,
                        "item_id": int(item.item_id),
                        "ok": False,
                        "skipped": True,
                        "reason": "not_downloaded",
                    }
                )
                continue
            if getattr(item, "added_doc_id", None):
                skipped += 1
                details.append({"session_id": item.session_id, "item_id": int(item.item_id), "ok": True, "already_added": True})
                continue
            try:
                self.owner.add_item_to_local_kb(
                    session_id=str(item.session_id),
                    item_id=int(item.item_id),
                    ctx=ctx,
                    kb_ref=kb_ref,
                    from_batch=True,
                )
                success += 1
                details.append({"session_id": item.session_id, "item_id": int(item.item_id), "ok": True})
            except Exception as e:
                failed += 1
                details.append({"session_id": item.session_id, "item_id": int(item.item_id), "ok": False, "error": str(e)})

        return {
            "ok": True,
            "history_key": str(history_key),
            "success": success,
            "failed": failed,
            "skipped": skipped,
            "items": details,
        }
