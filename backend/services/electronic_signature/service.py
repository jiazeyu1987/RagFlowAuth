from __future__ import annotations

import hashlib
import json
import secrets
import time
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from backend.services.users import resolve_login_block, verify_password

from .store import ElectronicSignature, ElectronicSignatureStore


SIGN_TOKEN_TTL_MS = 5 * 60 * 1000


@dataclass(frozen=True)
class AuthorizedSignatureContext:
    token_id: str
    user_id: str
    consumed_at_ms: int
    expires_at_ms: int


@dataclass
class ElectronicSignatureError(Exception):
    code: str
    status_code: int = 400

    def __str__(self) -> str:
        return self.code


class ElectronicSignatureService:
    def __init__(self, store: ElectronicSignatureStore, *, sign_token_ttl_ms: int = SIGN_TOKEN_TTL_MS):
        self._store = store
        self._sign_token_ttl_ms = int(sign_token_ttl_ms)

    @staticmethod
    def _normalize_required(value: str | None, *, field_name: str) -> str:
        normalized = str(value or "").strip()
        if not normalized:
            raise ElectronicSignatureError(field_name, status_code=400)
        return normalized

    @staticmethod
    def _to_json(value: Any) -> str:
        try:
            return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
        except Exception as exc:
            raise ElectronicSignatureError("signature_record_payload_invalid", status_code=400) from exc

    @classmethod
    def _hash_token(cls, token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    @staticmethod
    def _assert_user_can_sign(user: Any) -> None:
        blocked, reason = resolve_login_block(user)
        if not blocked:
            return
        if reason == "account_inactive":
            raise ElectronicSignatureError("signature_user_inactive", status_code=403)
        raise ElectronicSignatureError("signature_user_disabled", status_code=403)

    def issue_challenge(self, *, user: Any, password: str, user_store: Any | None = None) -> dict[str, Any]:
        self._assert_user_can_sign(user)
        password_text = self._normalize_required(password, field_name="signature_password_required")
        password_hash = str(getattr(user, "password_hash", "") or "")
        if not password_hash:
            raise ElectronicSignatureError("signature_password_hash_missing", status_code=400)

        password_ok, needs_rehash = verify_password(password_text, password_hash)
        if not password_ok:
            locked_until_ms = None
            if user_store is not None and getattr(user, "user_id", None) and hasattr(user_store, "record_credential_failure"):
                locked_until_ms = user_store.record_credential_failure(str(getattr(user, "user_id")))
            if locked_until_ms is not None:
                raise ElectronicSignatureError("signature_credentials_locked", status_code=423)
            raise ElectronicSignatureError("signature_password_invalid", status_code=400)
        if user_store is not None and getattr(user, "user_id", None):
            if hasattr(user_store, "clear_credential_failures"):
                user_store.clear_credential_failures(str(getattr(user, "user_id")))
            if needs_rehash and hasattr(user_store, "update_password"):
                user_store.update_password(str(getattr(user, "user_id")), password_text)

        now_ms = int(time.time() * 1000)
        token_id = str(uuid4())
        sign_token = secrets.token_urlsafe(32)
        expires_at_ms = now_ms + self._sign_token_ttl_ms
        self._store.create_challenge(
            token_id=token_id,
            user_id=str(getattr(user, "user_id", "") or ""),
            token_hash=self._hash_token(sign_token),
            issued_at_ms=now_ms,
            expires_at_ms=expires_at_ms,
        )
        return {
            "sign_token": sign_token,
            "expires_at_ms": expires_at_ms,
            "token_id": token_id,
        }

    def consume_sign_token(self, *, user: Any, sign_token: str, action: str) -> AuthorizedSignatureContext:
        self._assert_user_can_sign(user)
        token_value = self._normalize_required(sign_token, field_name="sign_token_required")
        action_name = self._normalize_required(action, field_name="signature_action_required")
        challenge = self._store.get_challenge_by_hash(self._hash_token(token_value))
        if challenge is None:
            raise ElectronicSignatureError("sign_token_invalid", status_code=401)
        user_id = str(getattr(user, "user_id", "") or "")
        if challenge.user_id != user_id:
            raise ElectronicSignatureError("sign_token_user_mismatch", status_code=403)

        now_ms = int(time.time() * 1000)
        if challenge.expires_at_ms < now_ms:
            raise ElectronicSignatureError("sign_token_expired", status_code=401)
        if challenge.consumed_at_ms is not None:
            raise ElectronicSignatureError("sign_token_already_used", status_code=409)

        updated = self._store.mark_challenge_consumed(
            token_id=challenge.token_id,
            consumed_by_action=action_name,
            consumed_at_ms=now_ms,
        )
        if updated is None or updated.consumed_at_ms is None:
            raise ElectronicSignatureError("sign_token_already_used", status_code=409)

        return AuthorizedSignatureContext(
            token_id=updated.token_id,
            user_id=updated.user_id,
            consumed_at_ms=int(updated.consumed_at_ms),
            expires_at_ms=updated.expires_at_ms,
        )

    def create_signature(
        self,
        *,
        signing_context: AuthorizedSignatureContext,
        user: Any,
        record_type: str,
        record_id: str,
        action: str,
        meaning: str,
        reason: str,
        record_payload: Any,
        status: str = "signed",
    ) -> ElectronicSignature:
        record_type_value = self._normalize_required(record_type, field_name="signature_record_type_required")
        record_id_value = self._normalize_required(record_id, field_name="signature_record_id_required")
        action_value = self._normalize_required(action, field_name="signature_action_required")
        meaning_value = self._normalize_required(meaning, field_name="signature_meaning_required")
        reason_value = self._normalize_required(reason, field_name="signature_reason_required")
        status_value = self._normalize_required(status, field_name="signature_status_required")

        signed_by = self._normalize_required(getattr(user, "user_id", None), field_name="signature_user_required")
        signed_by_username = self._normalize_required(
            getattr(user, "username", None),
            field_name="signature_username_required",
        )
        self._assert_user_can_sign(user)
        if signing_context.user_id != signed_by:
            raise ElectronicSignatureError("signature_context_user_mismatch", status_code=403)

        record_payload_json = self._to_json(record_payload)
        record_hash = hashlib.sha256(
            self._to_json(
                {
                    "record_type": record_type_value,
                    "record_id": record_id_value,
                    "action": action_value,
                    "meaning": meaning_value,
                    "reason": reason_value,
                    "signed_by": signed_by,
                    "signed_by_username": signed_by_username,
                    "record_payload": json.loads(record_payload_json),
                }
            ).encode("utf-8")
        ).hexdigest()

        signed_at_ms = int(time.time() * 1000)
        signature_hash = hashlib.sha256(
            self._to_json(
                {
                    "sign_token_id": signing_context.token_id,
                    "record_hash": record_hash,
                    "signed_by": signed_by,
                    "signed_by_username": signed_by_username,
                    "signed_at_ms": signed_at_ms,
                    "status": status_value,
                }
            ).encode("utf-8")
        ).hexdigest()

        return self._store.create_signature(
            signature_id=str(uuid4()),
            record_type=record_type_value,
            record_id=record_id_value,
            action=action_value,
            meaning=meaning_value,
            reason=reason_value,
            signed_by=signed_by,
            signed_by_username=signed_by_username,
            signed_at_ms=signed_at_ms,
            sign_token_id=signing_context.token_id,
            record_hash=record_hash,
            signature_hash=signature_hash,
            status=status_value,
            record_payload_json=record_payload_json,
        )

    def get_signature(self, signature_id: str) -> ElectronicSignature:
        signature = self._store.get_signature(signature_id)
        if signature is None:
            raise ElectronicSignatureError("signature_not_found", status_code=404)
        return signature

    def list_by_record(self, *, record_type: str, record_id: str) -> list[ElectronicSignature]:
        return self._store.list_by_record(record_type=record_type, record_id=record_id)

    def list_signatures(
        self,
        *,
        record_type: str | None = None,
        record_id: str | None = None,
        action: str | None = None,
        signed_by: str | None = None,
        status: str | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> tuple[int, list[ElectronicSignature]]:
        return self._store.list_signatures(
            record_type=record_type,
            record_id=record_id,
            action=action,
            signed_by=signed_by,
            status=status,
            offset=offset,
            limit=limit,
        )

    def latest_by_record(self, *, record_type: str, record_id: str) -> ElectronicSignature | None:
        return self._store.get_latest_by_record(record_type=record_type, record_id=record_id)

    def latest_by_records(self, *, record_type: str, record_ids: list[str]) -> dict[str, ElectronicSignature]:
        return self._store.get_latest_by_records(record_type=record_type, record_ids=record_ids)

    def verify_signature(self, *, signature_id: str, record_payload: Any | None = None) -> bool:
        signature = self.get_signature(signature_id)
        payload = signature.record_payload if record_payload is None else record_payload
        expected = self.create_signature_hashes(
            record_type=signature.record_type,
            record_id=signature.record_id,
            action=signature.action,
            meaning=signature.meaning,
            reason=signature.reason,
            signed_by=signature.signed_by,
            signed_by_username=signature.signed_by_username,
            sign_token_id=signature.sign_token_id,
            signed_at_ms=signature.signed_at_ms,
            status=signature.status,
            record_payload=payload,
        )
        return (
            signature.record_hash == expected["record_hash"]
            and signature.signature_hash == expected["signature_hash"]
        )

    def create_signature_hashes(
        self,
        *,
        record_type: str,
        record_id: str,
        action: str,
        meaning: str,
        reason: str,
        signed_by: str,
        signed_by_username: str,
        sign_token_id: str,
        signed_at_ms: int,
        status: str,
        record_payload: Any,
    ) -> dict[str, str]:
        record_hash = hashlib.sha256(
            self._to_json(
                {
                    "record_type": record_type,
                    "record_id": record_id,
                    "action": action,
                    "meaning": meaning,
                    "reason": reason,
                    "signed_by": signed_by,
                    "signed_by_username": signed_by_username,
                    "record_payload": record_payload,
                }
            ).encode("utf-8")
        ).hexdigest()
        signature_hash = hashlib.sha256(
            self._to_json(
                {
                    "sign_token_id": sign_token_id,
                    "record_hash": record_hash,
                    "signed_by": signed_by,
                    "signed_by_username": signed_by_username,
                    "signed_at_ms": int(signed_at_ms),
                    "status": status,
                }
            ).encode("utf-8")
        ).hexdigest()
        return {
            "record_hash": record_hash,
            "signature_hash": signature_hash,
        }
