from __future__ import annotations

import json
import time
from dataclasses import dataclass

from backend.database.paths import resolve_auth_db_path
from backend.database.sqlite import connect_sqlite


@dataclass(frozen=True)
class ElectronicSignatureChallenge:
    token_id: str
    user_id: str
    token_hash: str
    issued_at_ms: int
    expires_at_ms: int
    consumed_at_ms: int | None = None
    consumed_by_action: str | None = None


@dataclass(frozen=True)
class ElectronicSignature:
    signature_id: str
    record_type: str
    record_id: str
    action: str
    meaning: str
    reason: str
    signed_by: str
    signed_by_username: str
    signed_at_ms: int
    sign_token_id: str
    record_hash: str
    signature_hash: str
    status: str
    record_payload_json: str

    @property
    def record_payload(self):
        try:
            return json.loads(self.record_payload_json)
        except Exception:
            return None


class ElectronicSignatureStore:
    def __init__(self, db_path: str | None = None):
        self.db_path = resolve_auth_db_path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def _conn(self):
        return connect_sqlite(self.db_path)

    @staticmethod
    def _to_challenge(row) -> ElectronicSignatureChallenge | None:
        if not row:
            return None
        return ElectronicSignatureChallenge(
            token_id=str(row["token_id"] or ""),
            user_id=str(row["user_id"] or ""),
            token_hash=str(row["token_hash"] or ""),
            issued_at_ms=int(row["issued_at_ms"] or 0),
            expires_at_ms=int(row["expires_at_ms"] or 0),
            consumed_at_ms=(int(row["consumed_at_ms"]) if row["consumed_at_ms"] is not None else None),
            consumed_by_action=(str(row["consumed_by_action"]) if row["consumed_by_action"] is not None else None),
        )

    @staticmethod
    def _to_signature(row) -> ElectronicSignature | None:
        if not row:
            return None
        return ElectronicSignature(
            signature_id=str(row["signature_id"] or ""),
            record_type=str(row["record_type"] or ""),
            record_id=str(row["record_id"] or ""),
            action=str(row["action"] or ""),
            meaning=str(row["meaning"] or ""),
            reason=str(row["reason"] or ""),
            signed_by=str(row["signed_by"] or ""),
            signed_by_username=str(row["signed_by_username"] or ""),
            signed_at_ms=int(row["signed_at_ms"] or 0),
            sign_token_id=str(row["sign_token_id"] or ""),
            record_hash=str(row["record_hash"] or ""),
            signature_hash=str(row["signature_hash"] or ""),
            status=str(row["status"] or "signed"),
            record_payload_json=str(row["record_payload_json"] or "null"),
        )

    def create_challenge(
        self,
        *,
        token_id: str,
        user_id: str,
        token_hash: str,
        issued_at_ms: int,
        expires_at_ms: int,
    ) -> ElectronicSignatureChallenge:
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO electronic_signature_challenges (
                    token_id, user_id, token_hash, issued_at_ms, expires_at_ms
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    token_id,
                    user_id,
                    token_hash,
                    int(issued_at_ms),
                    int(expires_at_ms),
                ),
            )
            conn.commit()
        item = self.get_challenge(token_id)
        if item is None:
            raise RuntimeError("electronic_signature_challenge_create_failed")
        return item

    def get_challenge(self, token_id: str) -> ElectronicSignatureChallenge | None:
        with self._conn() as conn:
            row = conn.execute(
                """
                SELECT
                    token_id,
                    user_id,
                    token_hash,
                    issued_at_ms,
                    expires_at_ms,
                    consumed_at_ms,
                    consumed_by_action
                FROM electronic_signature_challenges
                WHERE token_id = ?
                """,
                (token_id,),
            ).fetchone()
        return self._to_challenge(row)

    def get_challenge_by_hash(self, token_hash: str) -> ElectronicSignatureChallenge | None:
        with self._conn() as conn:
            row = conn.execute(
                """
                SELECT
                    token_id,
                    user_id,
                    token_hash,
                    issued_at_ms,
                    expires_at_ms,
                    consumed_at_ms,
                    consumed_by_action
                FROM electronic_signature_challenges
                WHERE token_hash = ?
                """,
                (token_hash,),
            ).fetchone()
        return self._to_challenge(row)

    def mark_challenge_consumed(
        self,
        *,
        token_id: str,
        consumed_by_action: str,
        consumed_at_ms: int | None = None,
    ) -> ElectronicSignatureChallenge | None:
        now_ms = int(consumed_at_ms or time.time() * 1000)
        with self._conn() as conn:
            cursor = conn.execute(
                """
                UPDATE electronic_signature_challenges
                SET consumed_at_ms = ?, consumed_by_action = ?
                WHERE token_id = ?
                  AND consumed_at_ms IS NULL
                """,
                (now_ms, consumed_by_action, token_id),
            )
            conn.commit()
            if cursor.rowcount <= 0:
                return None
        return self.get_challenge(token_id)

    def create_signature(
        self,
        *,
        signature_id: str,
        record_type: str,
        record_id: str,
        action: str,
        meaning: str,
        reason: str,
        signed_by: str,
        signed_by_username: str,
        signed_at_ms: int,
        sign_token_id: str,
        record_hash: str,
        signature_hash: str,
        status: str,
        record_payload_json: str,
    ) -> ElectronicSignature:
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO electronic_signatures (
                    signature_id,
                    record_type,
                    record_id,
                    action,
                    meaning,
                    reason,
                    signed_by,
                    signed_by_username,
                    signed_at_ms,
                    sign_token_id,
                    record_hash,
                    signature_hash,
                    status,
                    record_payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    signature_id,
                    record_type,
                    record_id,
                    action,
                    meaning,
                    reason,
                    signed_by,
                    signed_by_username,
                    int(signed_at_ms),
                    sign_token_id,
                    record_hash,
                    signature_hash,
                    status,
                    record_payload_json,
                ),
            )
            conn.commit()
        item = self.get_signature(signature_id)
        if item is None:
            raise RuntimeError("electronic_signature_create_failed")
        return item

    def get_signature(self, signature_id: str) -> ElectronicSignature | None:
        with self._conn() as conn:
            row = conn.execute(
                """
                SELECT
                    signature_id,
                    record_type,
                    record_id,
                    action,
                    meaning,
                    reason,
                    signed_by,
                    signed_by_username,
                    signed_at_ms,
                    sign_token_id,
                    record_hash,
                    signature_hash,
                    status,
                    record_payload_json
                FROM electronic_signatures
                WHERE signature_id = ?
                """,
                (signature_id,),
            ).fetchone()
        return self._to_signature(row)

    def list_by_record(self, *, record_type: str, record_id: str) -> list[ElectronicSignature]:
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT
                    signature_id,
                    record_type,
                    record_id,
                    action,
                    meaning,
                    reason,
                    signed_by,
                    signed_by_username,
                    signed_at_ms,
                    sign_token_id,
                    record_hash,
                    signature_hash,
                    status,
                    record_payload_json
                FROM electronic_signatures
                WHERE record_type = ? AND record_id = ?
                ORDER BY signed_at_ms DESC, signature_id DESC
                """,
                (record_type, record_id),
            ).fetchall()
        return [self._to_signature(row) for row in rows if row]

    def list_signatures(
        self,
        *,
        record_type: str | None = None,
        record_id: str | None = None,
        action: str | None = None,
        signed_by: str | None = None,
        status: str | None = None,
        signed_at_from_ms: int | None = None,
        signed_at_to_ms: int | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> tuple[int, list[ElectronicSignature]]:
        where = ["1=1"]
        params: list[object] = []

        if record_type:
            where.append("record_type = ?")
            params.append(str(record_type))
        if record_id:
            where.append("record_id = ?")
            params.append(str(record_id))
        if action:
            where.append("action = ?")
            params.append(str(action))
        if signed_by:
            where.append("(signed_by = ? OR signed_by_username = ?)")
            params.append(str(signed_by))
            params.append(str(signed_by))
        if status:
            where.append("status = ?")
            params.append(str(status))
        if signed_at_from_ms is not None:
            where.append("signed_at_ms >= ?")
            params.append(int(signed_at_from_ms))
        if signed_at_to_ms is not None:
            where.append("signed_at_ms <= ?")
            params.append(int(signed_at_to_ms))

        safe_offset = max(0, int(offset))
        safe_limit = max(1, min(500, int(limit)))
        where_sql = " AND ".join(where)

        with self._conn() as conn:
            total = int(
                conn.execute(
                    f"SELECT COUNT(*) AS count FROM electronic_signatures WHERE {where_sql}",
                    params,
                ).fetchone()["count"]
            )
            rows = conn.execute(
                f"""
                SELECT
                    signature_id,
                    record_type,
                    record_id,
                    action,
                    meaning,
                    reason,
                    signed_by,
                    signed_by_username,
                    signed_at_ms,
                    sign_token_id,
                    record_hash,
                    signature_hash,
                    status,
                    record_payload_json
                FROM electronic_signatures
                WHERE {where_sql}
                ORDER BY signed_at_ms DESC, signature_id DESC
                LIMIT ? OFFSET ?
                """,
                [*params, safe_limit, safe_offset],
            ).fetchall()
        return total, [self._to_signature(row) for row in rows if row]

    def get_latest_by_record(self, *, record_type: str, record_id: str) -> ElectronicSignature | None:
        items = self.list_by_record(record_type=record_type, record_id=record_id)
        return items[0] if items else None

    def get_latest_by_records(self, *, record_type: str, record_ids: list[str]) -> dict[str, ElectronicSignature]:
        normalized_ids = []
        seen: set[str] = set()
        for item in record_ids:
            value = str(item or "").strip()
            if not value or value in seen:
                continue
            seen.add(value)
            normalized_ids.append(value)
        if not normalized_ids:
            return {}

        placeholders = ",".join("?" for _ in normalized_ids)
        sql = f"""
            WITH ranked AS (
                SELECT
                    signature_id,
                    record_type,
                    record_id,
                    action,
                    meaning,
                    reason,
                    signed_by,
                    signed_by_username,
                    signed_at_ms,
                    sign_token_id,
                    record_hash,
                    signature_hash,
                    status,
                    record_payload_json,
                    ROW_NUMBER() OVER (
                        PARTITION BY record_id
                        ORDER BY signed_at_ms DESC, signature_id DESC
                    ) AS rn
                FROM electronic_signatures
                WHERE record_type = ?
                  AND record_id IN ({placeholders})
            )
            SELECT
                signature_id,
                record_type,
                record_id,
                action,
                meaning,
                reason,
                signed_by,
                signed_by_username,
                signed_at_ms,
                sign_token_id,
                record_hash,
                signature_hash,
                status,
                record_payload_json
            FROM ranked
            WHERE rn = 1
        """
        with self._conn() as conn:
            rows = conn.execute(sql, [str(record_type), *normalized_ids]).fetchall()
        result: dict[str, ElectronicSignature] = {}
        for row in rows:
            signature = self._to_signature(row)
            if signature is not None:
                result[signature.record_id] = signature
        return result
