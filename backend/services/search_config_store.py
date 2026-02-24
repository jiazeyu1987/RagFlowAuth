from __future__ import annotations

import json
import sqlite3
import time
import uuid
from dataclasses import dataclass
from typing import Any

from backend.database.paths import resolve_auth_db_path
from backend.database.sqlite import connect_sqlite


@dataclass(frozen=True)
class SearchConfig:
    id: str
    name: str
    config: dict[str, Any]
    created_at_ms: int
    updated_at_ms: int


def _parse_json_object(value: str) -> dict[str, Any]:
    try:
        parsed = json.loads(value or "{}")
    except Exception as e:
        raise ValueError(f"invalid_json: {e}") from e
    if not isinstance(parsed, dict):
        raise ValueError("invalid_json: must be an object")
    return parsed


class SearchConfigStore:
    def __init__(self, db_path: str | None = None) -> None:
        self.db_path = resolve_auth_db_path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def _conn(self):
        return connect_sqlite(self.db_path)

    def list(self) -> list[SearchConfig]:
        conn = self._conn()
        try:
            rows = conn.execute(
                """
                SELECT id, name, config_json, created_at_ms, updated_at_ms
                FROM search_configs
                ORDER BY updated_at_ms DESC, created_at_ms DESC
                """
            ).fetchall()
        finally:
            conn.close()

        out: list[SearchConfig] = []
        for r in rows or []:
            try:
                cfg = _parse_json_object(r["config_json"] or "{}")
            except Exception:
                cfg = {}
            out.append(
                SearchConfig(
                    id=str(r["id"]),
                    name=str(r["name"]),
                    config=cfg,
                    created_at_ms=int(r["created_at_ms"] or 0),
                    updated_at_ms=int(r["updated_at_ms"] or 0),
                )
            )
        return out

    def get(self, config_id: str) -> SearchConfig | None:
        config_id = str(config_id or "").strip()
        if not config_id:
            return None
        conn = self._conn()
        try:
            r = conn.execute(
                """
                SELECT id, name, config_json, created_at_ms, updated_at_ms
                FROM search_configs
                WHERE id = ?
                """,
                (config_id,),
            ).fetchone()
        finally:
            conn.close()
        if not r:
            return None
        cfg = _parse_json_object(r["config_json"] or "{}")
        return SearchConfig(
            id=str(r["id"]),
            name=str(r["name"]),
            config=cfg,
            created_at_ms=int(r["created_at_ms"] or 0),
            updated_at_ms=int(r["updated_at_ms"] or 0),
        )

    def create(self, *, name: str, config: dict[str, Any]) -> SearchConfig:
        name = str(name or "").strip()
        if not name:
            raise ValueError("missing_name")
        if not isinstance(config, dict):
            raise ValueError("invalid_config")

        now_ms = int(time.time() * 1000)
        config_id = uuid.uuid4().hex
        config_json = json.dumps(config, ensure_ascii=False, separators=(",", ":"))

        conn = self._conn()
        try:
            conn.execute(
                """
                INSERT INTO search_configs (id, name, config_json, created_at_ms, updated_at_ms)
                VALUES (?, ?, ?, ?, ?)
                """,
                (config_id, name, config_json, now_ms, now_ms),
            )
            conn.commit()
        except sqlite3.IntegrityError as e:
            msg = str(e).lower()
            if "unique" in msg and "name" in msg:
                raise ValueError("name_exists") from e
            raise
        finally:
            conn.close()

        created = self.get(config_id)
        assert created is not None
        return created

    def update(self, *, config_id: str, name: str, config: dict[str, Any]) -> SearchConfig:
        config_id = str(config_id or "").strip()
        if not config_id:
            raise ValueError("missing_id")
        name = str(name or "").strip()
        if not name:
            raise ValueError("missing_name")
        if not isinstance(config, dict):
            raise ValueError("invalid_config")

        now_ms = int(time.time() * 1000)
        config_json = json.dumps(config, ensure_ascii=False, separators=(",", ":"))

        conn = self._conn()
        try:
            cur = conn.execute(
                """
                UPDATE search_configs
                SET name = ?, config_json = ?, updated_at_ms = ?
                WHERE id = ?
                """,
                (name, config_json, now_ms, config_id),
            )
            conn.commit()
        except sqlite3.IntegrityError as e:
            msg = str(e).lower()
            if "unique" in msg and "name" in msg:
                raise ValueError("name_exists") from e
            raise
        finally:
            conn.close()

        if (cur.rowcount or 0) <= 0:
            raise ValueError("not_found")
        updated = self.get(config_id)
        assert updated is not None
        return updated

    def delete(self, config_id: str) -> bool:
        config_id = str(config_id or "").strip()
        if not config_id:
            return False
        conn = self._conn()
        try:
            cur = conn.execute("DELETE FROM search_configs WHERE id = ?", (config_id,))
            conn.commit()
            return (cur.rowcount or 0) > 0
        finally:
            conn.close()

