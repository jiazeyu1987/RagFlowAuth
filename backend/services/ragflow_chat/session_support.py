from __future__ import annotations

from typing import Any, Optional


class RagflowChatSessionSupport:
    def _invalidate_chat_ref_cache(self) -> None:
        self._chat_ref_cache = None
        self._chat_ref_cache_at_s = 0.0

    @staticmethod
    def _response_message(payload: dict | None) -> str:
        if not isinstance(payload, dict):
            return ""
        try:
            msg = str(payload.get("message") or payload.get("detail") or "")
        except Exception:
            msg = ""
        if msg:
            return msg
        try:
            return str(payload)
        except Exception:
            return ""

    @classmethod
    def _is_method_not_allowed_error(cls, payload: dict | None) -> bool:
        msg = cls._response_message(payload).lower()
        return ("methodnotallowed" in msg) or ("405" in msg)

    @classmethod
    def _is_not_found_error(cls, payload: dict | None) -> bool:
        msg = cls._response_message(payload).lower()
        return ("notfound" in msg) or ("404" in msg)

    @classmethod
    def _is_dataset_ownership_error(cls, payload: dict | None) -> bool:
        msg = cls._response_message(payload).lower()
        return ("doesn't own parsed file" in msg) or ("does not own parsed file" in msg)

    def _coerce_updated_chat(
        self,
        chat_id: str,
        resp_payload: dict | None,
        fallback_fields: dict[str, Any],
    ) -> Optional[dict]:
        """
        RAGFlow update endpoints are inconsistent across versions:
        - Some return a full chat object in `data`
        - Some return `null`/non-dict, even when the update is applied
        - Some return the chat object directly (no {code,data} wrapper)
        For UI stability, fall back to `get_chat(chat_id)` when `data` isn't a dict.
        """
        if isinstance(resp_payload, dict) and resp_payload.get("id"):
            return resp_payload

        if isinstance(resp_payload, dict) and resp_payload.get("code") == 0:
            data = resp_payload.get("data")
            if isinstance(data, dict):
                return data

            fresh = self.get_chat(chat_id)
            if isinstance(fresh, dict) and fresh.get("id"):
                return fresh

            out = {"id": chat_id}
            for key, value in (fallback_fields or {}).items():
                if key in ("name", "dataset_ids", "kb_ids"):
                    out[key] = value
            return out

        return None

    def _verify_update_applied(
        self,
        chat_id: str,
        fallback_fields: dict[str, Any],
    ) -> Optional[dict]:
        """
        If the HTTP request succeeded server-side but the response was missing/invalid,
        refetch and verify only the fields that were part of the requested update.
        """
        fresh = self.get_chat(chat_id)
        if not isinstance(fresh, dict) or not fresh.get("id"):
            return None

        if "name" in fallback_fields:
            desired_name = str(fallback_fields.get("name") or "").strip()
            actual_name = str(fresh.get("name") or "").strip()
            if desired_name and desired_name != actual_name:
                return None

        if ("dataset_ids" in fallback_fields) or ("kb_ids" in fallback_fields):
            desired_ids = self._extract_dataset_ids(fallback_fields)
            actual_ids = self._extract_dataset_ids(fresh)
            if sorted(desired_ids) != sorted(actual_ids):
                return None

        return fresh

    @staticmethod
    def _minimal_chat_update_payload(body: dict[str, Any]) -> dict[str, Any]:
        minimal: dict[str, Any] = {}
        if "name" in body:
            minimal["name"] = body.get("name")
        if "dataset_ids" in body:
            minimal["dataset_ids"] = body.get("dataset_ids")
        elif "kb_ids" in body:
            minimal["kb_ids"] = body.get("kb_ids")
        return minimal

    @staticmethod
    def _merge_dataset_ids(current_ids: list[str], desired_ids: list[str]) -> list[str]:
        merged: list[str] = []
        seen: set[str] = set()
        for raw in list(current_ids) + list(desired_ids):
            value = str(raw or "").strip()
            if not value or value in seen:
                continue
            seen.add(value)
            merged.append(value)
        return merged

    def _raise_chat_update_error(
        self,
        resp_payload: dict | None,
        *,
        log_label: str,
        allow_locked_code: bool = False,
    ) -> None:
        message = ""
        if isinstance(resp_payload, dict):
            message = str(resp_payload.get("message") or "")
        self.logger.error("%s: %s", log_label, message)
        if allow_locked_code and self._is_dataset_ownership_error(resp_payload):
            raise ValueError(f"chat_dataset_locked: {message}")
        raise ValueError(str(message or "chat_update_failed"))

    def _retry_locked_chat_update(
        self,
        chat_id: str,
        body: dict[str, Any],
        resp_payload: dict | None,
    ) -> Optional[dict]:
        minimal = self._minimal_chat_update_payload(body)
        self.logger.warning(
            "RAGFlow update_chat failed with parsed-file ownership error; retrying minimal update. msg=%s",
            (resp_payload or {}).get("message") if isinstance(resp_payload, dict) else None,
        )
        retry_payload = self._client.put_json(f"/api/v1/chats/{chat_id}", body=minimal)
        if retry_payload and retry_payload.get("code") == 0:
            return self._coerce_updated_chat(chat_id, retry_payload, minimal)

        if (
            retry_payload
            and retry_payload.get("code") != 0
            and self._is_dataset_ownership_error(retry_payload)
        ):
            current = self.get_chat(chat_id) or {}
            current_ids = self._extract_dataset_ids(current)
            desired_ids = self._extract_dataset_ids(body)

            if not current_ids:
                clear_fields = self._parsed_file_clear_fields(current)
                if clear_fields:
                    self.logger.warning(
                        "RAGFlow update_chat hit parsed-file ownership on an unbound chat; clearing stale parsed-file bindings before retry. desired=%s",
                        desired_ids,
                    )
                    self.clear_chat_parsed_files(chat_id)
                    retry_after_clear = self._client.put_json(f"/api/v1/chats/{chat_id}", body=minimal)
                    if retry_after_clear and retry_after_clear.get("code") == 0:
                        return self._coerce_updated_chat(chat_id, retry_after_clear, minimal)
                    if (
                        retry_after_clear
                        and retry_after_clear.get("code") != 0
                        and not self._is_dataset_ownership_error(retry_after_clear)
                    ):
                        self._raise_chat_update_error(
                            retry_after_clear,
                            log_label="RAGFlow update_chat failed (retry#clear)",
                        )
                    if retry_after_clear:
                        retry_payload = retry_after_clear

            merged_ids = self._merge_dataset_ids(current_ids, desired_ids)
            if merged_ids and merged_ids != desired_ids:
                merged_payload = dict(minimal)
                if "dataset_ids" in minimal:
                    merged_payload["dataset_ids"] = merged_ids
                elif "kb_ids" in minimal:
                    merged_payload["kb_ids"] = merged_ids
                self.logger.warning(
                    "RAGFlow update_chat still failed with parsed-file ownership; retrying with merged dataset ids. cur=%s desired=%s merged=%s",
                    current_ids,
                    desired_ids,
                    merged_ids,
                )
                merged_retry = self._client.put_json(f"/api/v1/chats/{chat_id}", body=merged_payload)
                if merged_retry and merged_retry.get("code") == 0:
                    return self._coerce_updated_chat(chat_id, merged_retry, merged_payload)
                if merged_retry and merged_retry.get("code") != 0:
                    self._raise_chat_update_error(
                        merged_retry,
                        log_label="RAGFlow update_chat failed (retry#2)",
                    )

        if retry_payload is None:
            self._raise_chat_update_error(
                resp_payload,
                log_label="RAGFlow update_chat failed",
            )
        if retry_payload and retry_payload.get("code") != 0:
            self._raise_chat_update_error(
                retry_payload,
                log_label="RAGFlow update_chat failed (retry)",
                allow_locked_code=True,
            )
        return None

    def _delete_with_compat(
        self,
        attempts: list[dict[str, Any]],
        *,
        not_found_code: str,
        generic_error: str,
        log_label: str,
    ) -> bool:
        for index, attempt in enumerate(attempts):
            resp = self._client.delete_json(
                attempt["path"],
                body=attempt.get("body"),
                params=attempt.get("params"),
            )
            if resp and resp.get("code") == 0:
                self._invalidate_chat_ref_cache()
                return True
            if resp and self._is_not_found_error(resp):
                raise ValueError(not_found_code)
            if resp:
                is_last_attempt = index == len(attempts) - 1
                if is_last_attempt or not self._is_method_not_allowed_error(resp):
                    self.logger.error("%s: %s", log_label, resp.get("message"))
                    raise ValueError(str(resp.get("message") or generic_error))
        return False
