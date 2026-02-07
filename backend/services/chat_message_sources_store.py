from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any

from backend.database.paths import resolve_auth_db_path
from backend.database.sqlite import connect_sqlite


def _strip_think_tags(value: str) -> str:
    # Keep behavior consistent with the frontend:
    # - remove complete <think>...</think>
    # - hide an unfinished tail "<think>..."
    import re

    text = str(value or "")
    if not text:
        return ""
    out = re.sub(r"<think>[\s\S]*?</think>", "", text)
    out = re.sub(r"<think>[\s\S]*$", "", out)
    return out


def _normalize_for_hash(value: str) -> str:
    text = str(value or "")
    if not text:
        return ""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # Remove NULs that can appear in some streaming payloads.
    return text.replace("\u0000", "")


def content_hash_hex(value: str) -> str:
    """
    Match the frontend (Chat.js) djb2-like 32-bit hash used in localStorage keys.

    JS:
      hash = 5381
      hash = ((hash << 5) + hash) ^ charCode
      hash >>>= 0
    """
    text = _normalize_for_hash(_strip_think_tags(value))
    h = 5381
    for ch in text:
        h = ((h << 5) + h) ^ ord(ch)
        h &= 0xFFFFFFFF
    return format(h, "x")


@dataclass(frozen=True)
class ChatMessageSourcesRow:
    chat_id: str
    session_id: str
    content_hash: str
    sources: list[dict[str, Any]]
    updated_at_ms: int


class ChatMessageSourcesStore:
    """
    Persist retrieval sources (chunks + doc refs) for assistant messages.

    Why:
    - RAGFlow session history does not include our `sources`.
    - Frontend previously cached `sources` in localStorage only, which is lost after backup/restore.
    - Storing sources in auth.db makes them portable and recoverable.
    """

    def __init__(self, db_path: str | None = None) -> None:
        self.db_path = resolve_auth_db_path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def _conn(self):
        return connect_sqlite(self.db_path)

    def upsert_sources(self, *, chat_id: str, session_id: str, assistant_text: str, sources: list[dict[str, Any]]) -> None:
        chat_id = str(chat_id or "").strip()
        session_id = str(session_id or "").strip()
        if not chat_id or not session_id:
            return
        if not isinstance(sources, list) or len(sources) == 0:
            return

        h = content_hash_hex(assistant_text)
        now_ms = int(time.time() * 1000)
        try:
            sources_json = json.dumps(sources, ensure_ascii=False, separators=(",", ":"))
        except Exception:
            return

        conn = self._conn()
        try:
            conn.execute(
                """
                INSERT INTO chat_message_sources (
                    chat_id, session_id, content_hash, sources_json, created_at_ms, updated_at_ms
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(chat_id, session_id, content_hash)
                DO UPDATE SET sources_json = excluded.sources_json, updated_at_ms = excluded.updated_at_ms
                """,
                (chat_id, session_id, h, sources_json, now_ms, now_ms),
            )
            conn.commit()
        finally:
            conn.close()

    def get_sources_map(
        self, *, chat_id: str, session_id: str, content_hashes: list[str]
    ) -> dict[str, list[dict[str, Any]]]:
        chat_id = str(chat_id or "").strip()
        session_id = str(session_id or "").strip()
        hashes = [str(x or "").strip() for x in (content_hashes or []) if str(x or "").strip()]
        if not chat_id or not session_id or not hashes:
            return {}

        # SQLite parameter limit is high enough for our typical session sizes, but cap defensively.
        hashes = hashes[:500]
        placeholders = ",".join(["?"] * len(hashes))

        conn = self._conn()
        try:
            rows = conn.execute(
                f"""
                SELECT content_hash, sources_json, updated_at_ms
                FROM chat_message_sources
                WHERE chat_id = ? AND session_id = ? AND content_hash IN ({placeholders})
                """,
                [chat_id, session_id, *hashes],
            ).fetchall()
        finally:
            conn.close()

        out: dict[str, list[dict[str, Any]]] = {}
        for r in rows or []:
            try:
                ch = str(r["content_hash"])
                parsed = json.loads(r["sources_json"] or "[]")
                if isinstance(parsed, list):
                    out[ch] = [x for x in parsed if isinstance(x, dict)]
            except Exception:
                continue
        return out

