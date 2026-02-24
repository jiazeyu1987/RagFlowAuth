import logging
from typing import Optional, List, AsyncIterator, Dict, Any
import re

from .ragflow_connection import RagflowConnection, create_ragflow_connection
from .ragflow_config import (
    DEFAULT_RAGFLOW_BASE_URL,
    effective_api_key,
    format_api_key_for_log,
    load_ragflow_config,
)
from .ragflow_http_client import RagflowHttpClientConfig


class RagflowChatService:
    def __init__(
        self,
        config_path: str = None,
        logger: logging.Logger = None,
        session_store=None,
        *,
        connection: RagflowConnection | None = None,
    ):
        self.logger = logger or logging.getLogger(__name__)
        conn = connection or create_ragflow_connection(config_path=config_path, logger=self.logger)
        self.config_path = conn.config_path
        self.config = conn.config
        self.session_store = session_store
        self._client = conn.http
        self._chat_ref_cache: dict[str, str] | None = None
        self._chat_ref_cache_at_s: float = 0.0
        self._config_mtime_ns: int | None = None
        self._config_sig: tuple[str, str, float] | None = None
        self._capture_config_state()

    def _capture_config_state(self) -> None:
        try:
            st = self.config_path.stat()
            self._config_mtime_ns = getattr(st, "st_mtime_ns", None) or int(st.st_mtime * 1_000_000_000)
        except Exception:
            self._config_mtime_ns = None
        try:
            base_url = str(self.config.get("base_url", DEFAULT_RAGFLOW_BASE_URL) or "")
            api_key = str(self.config.get("api_key", "") or "")
            timeout_s = float(self.config.get("timeout", 10) or 10)
            self._config_sig = (base_url, api_key, timeout_s)
        except Exception:
            self._config_sig = None

    def _reload_config_if_changed(self) -> None:
        try:
            st = self.config_path.stat()
            mtime_ns = getattr(st, "st_mtime_ns", None) or int(st.st_mtime * 1_000_000_000)
        except Exception:
            mtime_ns = None

        if mtime_ns is not None and self._config_mtime_ns is not None and mtime_ns == self._config_mtime_ns:
            return

        new_config = load_ragflow_config(self.config_path, logger=self.logger)
        if not isinstance(new_config, dict):
            return

        try:
            new_base_url = str(new_config.get("base_url", DEFAULT_RAGFLOW_BASE_URL) or "")
            new_api_key = effective_api_key(
                base_url=new_base_url,
                configured_api_key=str(new_config.get("api_key", "") or ""),
            )
            new_timeout_s = float(new_config.get("timeout", 10) or 10)
            new_sig = (new_base_url, new_api_key, new_timeout_s)
        except Exception:
            return

        if self._config_sig is not None and new_sig == self._config_sig:
            self._config_mtime_ns = mtime_ns
            return

        new_config["base_url"] = new_base_url
        new_config["api_key"] = new_api_key
        self.config = new_config
        self._client.set_config(RagflowHttpClientConfig(base_url=new_base_url, api_key=new_api_key, timeout_s=new_timeout_s))
        self._chat_ref_cache = None
        self._chat_ref_cache_at_s = 0.0
        self._config_mtime_ns = mtime_ns
        self._config_sig = new_sig
        try:
            logging.getLogger("uvicorn.error").warning(
                "RAGFlow chat config reloaded: base_url=%s api_key=%s",
                new_base_url,
                format_api_key_for_log(new_api_key),
            )
        except Exception:
            pass

    def list_chats(
        self,
        page: int = 1,
        page_size: int = 30,
        orderby: str = "create_time",
        desc: bool = True,
        name: Optional[str] = None,
        chat_id: Optional[str] = None
    ) -> List[dict]:
        """
        列出聊天助手

        Args:
            page: 页码，默认1
            page_size: 每页数量，默认30
            orderby: 排序字段，默认create_time
            desc: 是否降序，默认True
            name: 按名称过滤
            chat_id: 按ID过滤

        Returns:
            聊天助手列表
        """
        self._reload_config_if_changed()
        params: dict[str, Any] = {
            "page": page,
            "page_size": page_size,
            "orderby": orderby,
            "desc": "true" if desc else "false",
        }
        if name:
            params["name"] = name
        if chat_id:
            params["id"] = chat_id
        return self._client.get_list("/api/v1/chats", params=params, context="list_chats")

    def get_chat(self, chat_id: str) -> Optional[dict]:
        """
        获取单个聊天助手信息

        Args:
            chat_id: 聊天助手ID

        Returns:
            聊天助手信息，如果不存在返回None
        """
        chats = self.list_chats(chat_id=chat_id)
        return chats[0] if chats else None

    def _sanitize_chat_payload(self, payload: dict[str, Any], *, for_update: bool) -> dict[str, Any]:
        """
        RAGFlow APIs tend to reject read-only fields (id/tenant/time/status).
        We keep the contract flexible (frontend edits JSON), but strip obvious
        server-managed fields before calling RAGFlow create/update endpoints.
        """
        body: dict[str, Any] = dict(payload or {})

        # Path params control identity; never allow client to override.
        body.pop("id", None)
        body.pop("chat_id", None)

        # Common read-only / computed fields observed in RAGFlow payloads.
        for k in [
            "tenant_id",
            "create_time",
            "update_time",
            "status",
            "token_num",
            "document_count",
            "chunk_count",
        ]:
            body.pop(k, None)

        # Some deployments include task metadata; strip by default.
        for k in list(body.keys()):
            if not isinstance(k, str):
                continue
            if k.endswith("_task_id") or k.endswith("_task_finish_at") or k.endswith("_task_start_at"):
                body.pop(k, None)

        # Update: keep only provided fields (caller may send full object though).
        # Create: allow a full config blob, but caller should ensure required fields exist.
        if for_update:
            # Ensure we don't accidentally send empty updates that would confuse upstream.
            return body
        return body

    @staticmethod
    def _extract_dataset_ids(payload: dict[str, Any]) -> list[str]:
        if not isinstance(payload, dict):
            return []

        raw = payload.get("dataset_ids")
        if isinstance(raw, list):
            out = []
            for x in raw:
                s = str(x or "").strip()
                if s:
                    out.append(s)
            if out:
                return out

        raw = payload.get("kb_ids")
        if isinstance(raw, list):
            out = []
            for x in raw:
                s = str(x or "").strip()
                if s:
                    out.append(s)
            if out:
                return out

        ds = payload.get("datasets")
        if isinstance(ds, list):
            out = []
            for item in ds:
                if item is None:
                    continue
                if isinstance(item, (str, int, float)):
                    s = str(item).strip()
                    if s:
                        out.append(s)
                    continue
                if isinstance(item, dict):
                    raw_id = item.get("id") or item.get("dataset_id") or item.get("kb_id") or item.get("datasetId") or item.get("kbId")
                    s = str(raw_id or "").strip()
                    if s:
                        out.append(s)
            return out

        return []

    def create_chat(self, payload: dict[str, Any]) -> Optional[dict]:
        self._reload_config_if_changed()
        body = self._sanitize_chat_payload(payload, for_update=False)
        resp = self._client.post_json("/api/v1/chats", body=body)
        if not resp:
            return None
        if resp.get("code") != 0:
            self.logger.error("RAGFlow create_chat failed: %s", resp.get("message"))
            raise ValueError(str(resp.get("message") or "chat_create_failed"))
        data = resp.get("data")
        self._chat_ref_cache = None
        self._chat_ref_cache_at_s = 0.0
        return data if isinstance(data, dict) else None

    def update_chat(self, chat_id: str, payload: dict[str, Any]) -> Optional[dict]:
        self._reload_config_if_changed()
        body = self._sanitize_chat_payload(payload, for_update=True)

        def _coerce_updated_chat(resp_payload: dict | None, fallback_fields: dict[str, Any]) -> Optional[dict]:
            """
            RAGFlow update endpoints are inconsistent across versions:
            - Some return a full chat object in `data`
            - Some return `null`/non-dict, even when the update is applied
            - Some return the chat object directly (no {code,data} wrapper)
            For UI stability, fall back to `get_chat(chat_id)` when `data` isn't a dict.
            """
            # Some versions return the chat object directly.
            if isinstance(resp_payload, dict) and resp_payload.get("id"):
                return resp_payload

            if isinstance(resp_payload, dict) and resp_payload.get("code") == 0:
                data = resp_payload.get("data")
                if isinstance(data, dict):
                    return data

                # Fallback: refetch canonical chat config.
                fresh = self.get_chat(chat_id)
                if isinstance(fresh, dict) and fresh.get("id"):
                    return fresh

                # Last resort: return a minimal object so callers don't treat as failure.
                out = {"id": chat_id}
                for k, v in (fallback_fields or {}).items():
                    if k in ("name", "dataset_ids", "kb_ids"):
                        out[k] = v
                return out

            return None

        def _verify_update_applied(fallback_fields: dict[str, Any]) -> Optional[dict]:
            """
            If the HTTP request succeeded server-side but the response was missing/invalid,
            we can avoid false 500s by refetching and verifying only the fields we tried to update.
            """
            fresh = self.get_chat(chat_id)
            if not isinstance(fresh, dict) or not fresh.get("id"):
                return None

            # Verify name if it was part of the update.
            if "name" in fallback_fields:
                desired_name = str(fallback_fields.get("name") or "").strip()
                actual_name = str(fresh.get("name") or "").strip()
                if desired_name and desired_name != actual_name:
                    return None

            # Verify dataset selection if it was part of the update.
            if ("dataset_ids" in fallback_fields) or ("kb_ids" in fallback_fields):
                desired_ids = self._extract_dataset_ids(fallback_fields)
                actual_ids = self._extract_dataset_ids(fresh)
                if sorted(desired_ids) != sorted(actual_ids):
                    return None

            return fresh

        def _is_dataset_ownership_error(resp_payload: dict | None) -> bool:
            if not isinstance(resp_payload, dict):
                return False
            try:
                msg = str(resp_payload.get("message") or resp_payload.get("detail") or "")
            except Exception:
                msg = ""
            if not msg:
                try:
                    msg = str(resp_payload)
                except Exception:
                    msg = ""
            if not msg:
                return False
            msg_l = msg.lower()
            return ("doesn't own parsed file" in msg_l) or ("does not own parsed file" in msg_l)

        resp = self._client.put_json(f"/api/v1/chats/{chat_id}", body=body)
        if not resp:
            # Best-effort: if update was applied but response was missing/invalid, avoid false failure.
            verified = _verify_update_applied(body)
            if verified:
                self._chat_ref_cache = None
                self._chat_ref_cache_at_s = 0.0
                return verified
            return None
        if resp.get("code") != 0:
            # Some RAGFlow versions validate hidden "parsed file" bindings when updating a chat.
            # If a user changes dataset_ids to a dataset that doesn't own those parsed files,
            # RAGFlow rejects the update even though dataset_ids itself is valid.
            #
            # Workaround: retry with a minimal patch (name + dataset_ids only) to avoid
            # touching those hidden bindings. This matches user intent in our UI.
            if _is_dataset_ownership_error(resp):
                minimal: dict[str, Any] = {}
                if "name" in body:
                    minimal["name"] = body.get("name")
                if "dataset_ids" in body:
                    minimal["dataset_ids"] = body.get("dataset_ids")
                elif "kb_ids" in body:
                    minimal["kb_ids"] = body.get("kb_ids")
                self.logger.warning(
                    "RAGFlow update_chat failed with parsed-file ownership error; retrying minimal update. msg=%s",
                    resp.get("message"),
                )
                resp2 = self._client.put_json(f"/api/v1/chats/{chat_id}", body=minimal)
                if resp2 and resp2.get("code") == 0:
                    data2 = _coerce_updated_chat(resp2, minimal)
                    self._chat_ref_cache = None
                    self._chat_ref_cache_at_s = 0.0
                    return data2
                if resp2 and resp2.get("code") != 0 and _is_dataset_ownership_error(resp2):
                    # Second-chance: some RAGFlow versions require keeping datasets that already
                    # own existing parsed files. In that case, we cannot "deselect" those datasets
                    # via update. Merge current dataset ids and retry to keep the chat usable.
                    current = self.get_chat(chat_id) or {}
                    cur_ids = self._extract_dataset_ids(current)
                    desired_ids = self._extract_dataset_ids(body)
                    merged = []
                    seen = set()
                    for x in list(cur_ids) + list(desired_ids):
                        s = str(x or "").strip()
                        if not s or s in seen:
                            continue
                        seen.add(s)
                        merged.append(s)
                    if merged and merged != desired_ids:
                        minimal2: dict[str, Any] = {}
                        if "name" in minimal:
                            minimal2["name"] = minimal.get("name")
                        if "dataset_ids" in minimal:
                            minimal2["dataset_ids"] = merged
                        elif "kb_ids" in minimal:
                            minimal2["kb_ids"] = merged
                        self.logger.warning(
                            "RAGFlow update_chat still failed with parsed-file ownership; retrying with merged dataset ids. cur=%s desired=%s merged=%s",
                            cur_ids,
                            desired_ids,
                            merged,
                        )
                        resp3 = self._client.put_json(f"/api/v1/chats/{chat_id}", body=minimal2)
                        if resp3 and resp3.get("code") == 0:
                            data3 = _coerce_updated_chat(resp3, minimal2)
                            self._chat_ref_cache = None
                            self._chat_ref_cache_at_s = 0.0
                            return data3
                        if resp3 and resp3.get("code") != 0:
                            self.logger.error("RAGFlow update_chat failed (retry#2): %s", resp3.get("message"))
                            raise ValueError(str(resp3.get("message") or "chat_update_failed"))

                if resp2 and resp2.get("code") != 0:
                    self.logger.error("RAGFlow update_chat failed (retry): %s", resp2.get("message"))
                    # Give the UI a stable error code to detect this case.
                    if _is_dataset_ownership_error(resp2):
                        raise ValueError(f"chat_dataset_locked: {resp2.get('message')}")
                    raise ValueError(str(resp2.get("message") or "chat_update_failed"))

            self.logger.error("RAGFlow update_chat failed: %s", resp.get("message"))
            raise ValueError(str(resp.get("message") or "chat_update_failed"))

        data = _coerce_updated_chat(resp, body)
        if not data:
            # Some deployments return a wrapper without `code` (or other oddities). Try to verify.
            data = _verify_update_applied(body)
        self._chat_ref_cache = None
        self._chat_ref_cache_at_s = 0.0
        return data

    def delete_chat(self, chat_id: str) -> bool:
        self._reload_config_if_changed()

        # RAGFlow versions differ:
        # - Some do NOT allow DELETE /api/v1/chats/{id} (returns MethodNotAllowed)
        # - Some accept DELETE /api/v1/chats with body {"ids":[...]} (observed in our env)
        #
        # We must treat "method not allowed" as a signal to fall back, not as a hard failure.
        def _is_method_not_allowed(payload: dict | None) -> bool:
            try:
                msg = str((payload or {}).get("message") or (payload or {}).get("detail") or "")
            except Exception:
                msg = ""
            if not msg:
                return False
            return ("MethodNotAllowed" in msg) or ("405" in msg)

        def _is_not_found(payload: dict | None) -> bool:
            try:
                msg = str((payload or {}).get("message") or (payload or {}).get("detail") or "")
            except Exception:
                msg = ""
            if not msg:
                return False
            return ("NotFound" in msg) or ("404" in msg)

        # Prefer batch delete first; it's the most common contract across RAGFlow versions.
        resp = self._client.delete_json("/api/v1/chats", body={"ids": [chat_id]})
        if resp and resp.get("code") == 0:
            self._chat_ref_cache = None
            self._chat_ref_cache_at_s = 0.0
            return True

        if resp and _is_not_found(resp):
            raise ValueError("chat_not_found")

        if resp and not _is_method_not_allowed(resp):
            self.logger.error("RAGFlow delete_chat failed: %s", resp.get("message"))
            raise ValueError(str(resp.get("message") or "chat_delete_failed"))

        # Fallback 1: older variants support DELETE /api/v1/chats/{id}
        resp2 = self._client.delete_json(f"/api/v1/chats/{chat_id}", body={})
        if resp2 and resp2.get("code") == 0:
            self._chat_ref_cache = None
            self._chat_ref_cache_at_s = 0.0
            return True
        if resp2 and _is_not_found(resp2):
            raise ValueError("chat_not_found")
        if resp2 and (not _is_method_not_allowed(resp2)):
            self.logger.error("RAGFlow delete_chat failed: %s", resp2.get("message"))
            raise ValueError(str(resp2.get("message") or "chat_delete_failed"))

        # Fallback 2: some gateways strip/deny DELETE bodies; use query params: ?ids=<id>
        resp3 = self._client.delete_json("/api/v1/chats", params={"ids": chat_id}, body=None)
        if resp3 and resp3.get("code") == 0:
            self._chat_ref_cache = None
            self._chat_ref_cache_at_s = 0.0
            return True
        if resp3 and _is_not_found(resp3):
            raise ValueError("chat_not_found")
        if resp3 and resp3.get("code") != 0:
            self.logger.error("RAGFlow delete_chat failed: %s", resp3.get("message"))
            raise ValueError(str(resp3.get("message") or "chat_delete_failed"))
        return False

        self._chat_ref_cache = None
        self._chat_ref_cache_at_s = 0.0
        return True

    @staticmethod
    def _parsed_file_clear_fields(payload: dict[str, Any]) -> dict[str, Any]:
        """
        Detect parsed-file binding fields in a chat payload and compute "empty" values.

        RAGFlow versions differ, but the ownership error string indicates there are hidden bindings
        from chat -> parsed files. If present, they typically contain both "parsed" and "file".
        """
        if not isinstance(payload, dict):
            return {}
        fields: dict[str, Any] = {}
        pat = re.compile(r"parsed.*file|file.*parsed", re.IGNORECASE)
        for k, v in payload.items():
            if not isinstance(k, str):
                continue
            if not pat.search(k):
                continue
            # Only clear fields that already exist on this RAGFlow version.
            # Keep the "shape" so the remote validation is more likely to accept it.
            if isinstance(v, list):
                fields[k] = []
            elif isinstance(v, str):
                fields[k] = ""
        return fields

    def clear_chat_parsed_files(self, chat_id: str) -> Optional[dict]:
        """
        Attempt to clear parsed-file bindings for a chat.

        This is a best-effort compatibility feature to unblock switching datasets when RAGFlow
        enforces parsed-file ownership constraints.
        """
        self._reload_config_if_changed()
        current = self.get_chat(chat_id)
        if not isinstance(current, dict) or not current.get("id"):
            raise ValueError("chat_not_found")

        clear_fields = self._parsed_file_clear_fields(current)
        if not clear_fields:
            # Nothing to clear on this RAGFlow version (or not exposed via API).
            return current

        # Keep datasets unchanged while clearing parsed file bindings.
        payload: dict[str, Any] = {}
        for k in ("dataset_ids", "kb_ids"):
            if isinstance(current.get(k), list):
                payload[k] = list(current.get(k) or [])
        payload.update(clear_fields)

        resp = self._client.put_json(f"/api/v1/chats/{chat_id}", body=payload)
        if resp and resp.get("code") == 0:
            data = resp.get("data")
            if isinstance(data, dict) and data.get("id"):
                self._chat_ref_cache = None
                self._chat_ref_cache_at_s = 0.0
                return data

            # Some versions return null/non-dict even when applied; refetch.
            fresh = self.get_chat(chat_id)
            if isinstance(fresh, dict) and fresh.get("id"):
                self._chat_ref_cache = None
                self._chat_ref_cache_at_s = 0.0
                return fresh
            return {"id": chat_id, **{k: payload.get(k) for k in payload.keys() if k != "id"}}

        if resp and resp.get("code") != 0:
            raise ValueError(str(resp.get("message") or resp.get("detail") or "chat_clear_parsed_failed"))

        # No response/unknown; return current so callers can decide.
        return current

    def create_session(
        self,
        chat_id: str,
        name: str,
        user_id: Optional[str] = None
    ) -> Optional[dict]:
        """
        创建聊天会话

        Args:
            chat_id: 聊天助手ID
            name: 会话名称
            user_id: 用户ID（可选）

        Returns:
            创建的会话信息，失败返回None
        """
        self._reload_config_if_changed()
        body: dict[str, Any] = {"name": name}
        if user_id:
            body["user_id"] = user_id

        payload = self._client.post_json(f"/api/v1/chats/{chat_id}/sessions", body=body)
        if not payload:
            return None
        if payload.get("code") != 0:
            self.logger.error("Failed to create session: %s", payload.get("message"))
            return None

        session_data = payload.get("data")
        if not isinstance(session_data, dict):
            return None

        # Sync to local DB
        if self.session_store and user_id:
            session_id_value = session_data.get("id")
            if session_id_value:
                self.session_store.create_session(
                    session_id=session_id_value,
                    chat_id=chat_id,
                    user_id=user_id,
                    name=name,
                )

        return session_data

    def list_sessions(
        self,
        chat_id: str,
        page: int = 1,
        page_size: int = 30,
        orderby: str = "create_time",
        desc: bool = True,
        name: Optional[str] = None,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> List[dict]:
        """
        列出聊天助手的所有会话

        Args:
            chat_id: 聊天助手ID
            page: 页码
            page_size: 每页数量
            orderby: 排序字段
            desc: 是否降序
            name: 按名称过滤
            session_id: 按会话ID过滤
            user_id: 按用户ID过滤

        Returns:
            会话列表
        """
        self._reload_config_if_changed()
        params: dict[str, Any] = {
            "page": page,
            "page_size": page_size,
            "orderby": orderby,
            "desc": "true" if desc else "false",
        }
        if name:
            params["name"] = name
        if session_id:
            params["id"] = session_id
        if user_id:
            params["user_id"] = user_id
        return self._client.get_list(
            f"/api/v1/chats/{chat_id}/sessions",
            params=params,
            context="list_sessions",
        )

    async def chat(
        self,
        chat_id: str,
        question: str,
        stream: bool = True,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> AsyncIterator[dict]:
        """
        与聊天助手对话（流式）

        Args:
            chat_id: 聊天助手ID
            question: 问题
            stream: 是否流式输出
            session_id: 会话ID，如果为None则创建新会话
            user_id: 用户ID

        Yields:
            聊天响应数据块
        """
        self._reload_config_if_changed()
        body: dict[str, Any] = {"question": question, "stream": stream}
        if session_id:
            body["session_id"] = session_id
        if user_id:
            body["user_id"] = user_id

        if stream:
            for obj in self._client.post_sse(f"/api/v1/chats/{chat_id}/completions", body=body, timeout_s=30):
                yield obj
            return

        payload = self._client.post_json(f"/api/v1/chats/{chat_id}/completions", body=body)
        if payload is None:
            yield {"code": -1, "message": "Chat request failed"}
            return
        yield payload

    def delete_sessions(
        self,
        chat_id: str,
        session_ids: Optional[List[str]] = None,
        user_id: Optional[str] = None
    ) -> bool:
        """
        删除聊天会话

        Args:
            chat_id: 聊天助手ID
            session_ids: 要删除的会话ID列表，如果为None则删除所有会话
            user_id: 用户ID（用于本地数据库标记）

        Returns:
            是否成功
        """
        self._reload_config_if_changed()
        body: dict[str, Any] = {}
        if session_ids:
            body["ids"] = session_ids
        payload = self._client.delete_json(f"/api/v1/chats/{chat_id}/sessions", body=body)
        if not payload:
            return False
        success = payload.get("code") == 0

        # Sync to local DB (soft delete)
        if success and self.session_store and session_ids and user_id:
            self.session_store.delete_sessions(session_ids=session_ids, chat_id=chat_id, deleted_by=user_id)

        return bool(success)

    def list_agents(
        self,
        page: int = 1,
        page_size: int = 30,
        orderby: str = "create_time",
        desc: bool = True,
        name: Optional[str] = None,
        id: Optional[str] = None
    ) -> List[dict]:
        """
        列出所有搜索体 (Agents)

        Args:
            page: 页码，默认1
            page_size: 每页数量，默认30
            orderby: 排序字段，默认create_time
            desc: 是否降序，默认True
            name: 按名称过滤
            id: 按ID过滤

        Returns:
            搜索体列表
        """
        self._reload_config_if_changed()
        params: dict[str, Any] = {
            "page": page,
            "page_size": page_size,
            "orderby": orderby,
            "desc": "true" if desc else "false",
        }
        if name:
            params["name"] = name
        if id:
            params["id"] = id
        return self._client.get_list("/api/v1/agents", params=params, context="list_agents")

    def get_agent(self, agent_id: str) -> Optional[dict]:
        """
        获取单个搜索体信息

        Args:
            agent_id: 搜索体ID

        Returns:
            搜索体信息，如果不存在返回None
        """
        agents = self.list_agents(id=agent_id)
        return agents[0] if agents else None

    @staticmethod
    def default_agent_dsl() -> Dict[str, Any]:
        """
        Minimal DSL payload required by RAGFlow when creating an agent.

        Note: Always return a new dict to avoid accidental cross-request mutation.
        """
        return {
            "components": {
                "begin": {
                    "downstream": [],
                    "obj": {"component_name": "Begin", "params": {}},
                    "upstream": [],
                }
            },
            "globals": {
                "sys.conversation_turns": 0,
                "sys.files": [],
                "sys.query": "",
                "sys.user_id": "",
            },
            "graph": {
                "edges": [],
                "nodes": [
                    {
                        "data": {"label": "Begin", "name": "begin"},
                        "id": "begin",
                        "position": {"x": 50, "y": 200},
                        "sourcePosition": "left",
                        "targetPosition": "right",
                        "type": "beginNode",
                    }
                ],
            },
            "history": [],
            "path": [],
            "retrieval": [],
        }

    def create_agent(self, payload: Dict[str, Any]) -> Optional[dict]:
        """
        Create an agent (search config) in RAGFlow.

        RAGFlow versions differ: some return only `data=true` without the created object/id.
        We refetch by listing agents and matching title.
        """
        self._reload_config_if_changed()

        title = str(payload.get("title") or "").strip()
        if not title:
            raise ValueError("missing_title")

        body: Dict[str, Any] = {"title": title}
        description = payload.get("description")
        if isinstance(description, str) and description.strip():
            body["description"] = description.strip()

        dsl = payload.get("dsl")
        if isinstance(dsl, dict):
            body["dsl"] = dsl
        else:
            body["dsl"] = self.default_agent_dsl()

        resp = self._client.post_json("/api/v1/agents", body=body)
        if not resp:
            return None
        if resp.get("code") != 0:
            self.logger.error("RAGFlow create_agent failed: %s", resp.get("message"))
            raise ValueError(str(resp.get("message") or "agent_create_failed"))

        # Some versions return the created agent object directly.
        data = resp.get("data")
        if isinstance(data, dict) and data.get("id"):
            self._chat_ref_cache = None
            self._chat_ref_cache_at_s = 0.0
            return data

        # Best-effort: refetch newly created agent by title (newest first).
        agents = self.list_agents(page=1, page_size=1000, orderby="create_time", desc=True)
        for agent in agents:
            if not isinstance(agent, dict):
                continue
            if str(agent.get("title") or "").strip() == title:
                self._chat_ref_cache = None
                self._chat_ref_cache_at_s = 0.0
                return agent

        self._chat_ref_cache = None
        self._chat_ref_cache_at_s = 0.0
        return None

    def update_agent(self, agent_id: str, payload: Dict[str, Any]) -> Optional[dict]:
        """
        Update an agent in RAGFlow.

        Note: RAGFlow may return `data=true` without the updated object. We refetch.
        """
        self._reload_config_if_changed()

        body: Dict[str, Any] = {}
        title = payload.get("title")
        if isinstance(title, str) and title.strip():
            body["title"] = title.strip()

        description = payload.get("description")
        if isinstance(description, str):
            body["description"] = description.strip()

        dsl = payload.get("dsl")
        if isinstance(dsl, dict):
            body["dsl"] = dsl

        resp = self._client.put_json(f"/api/v1/agents/{agent_id}", body=body)
        if not resp:
            return None
        if resp.get("code") != 0:
            self.logger.error("RAGFlow update_agent failed: %s", resp.get("message"))
            raise ValueError(str(resp.get("message") or "agent_update_failed"))

        self._chat_ref_cache = None
        self._chat_ref_cache_at_s = 0.0
        return self.get_agent(agent_id) or {"id": agent_id, "title": body.get("title")}

    def delete_agent(self, agent_id: str) -> bool:
        """
        Delete an agent in RAGFlow.

        Observed compatibility:
        - DELETE /api/v1/agents/{id} works
        - DELETE /api/v1/agents with body {"ids":[...]} may return 405
        """
        self._reload_config_if_changed()

        def _is_method_not_allowed(payload: dict | None) -> bool:
            try:
                msg = str((payload or {}).get("message") or (payload or {}).get("detail") or "")
            except Exception:
                msg = ""
            if not msg:
                return False
            return ("MethodNotAllowed" in msg) or ("405" in msg)

        def _is_not_found(payload: dict | None) -> bool:
            try:
                msg = str((payload or {}).get("message") or (payload or {}).get("detail") or "")
            except Exception:
                msg = ""
            if not msg:
                return False
            return ("NotFound" in msg) or ("404" in msg)

        resp = self._client.delete_json(f"/api/v1/agents/{agent_id}", body={})
        if resp and resp.get("code") == 0:
            self._chat_ref_cache = None
            self._chat_ref_cache_at_s = 0.0
            return True
        if resp and _is_not_found(resp):
            raise ValueError("agent_not_found")
        if resp and (not _is_method_not_allowed(resp)):
            self.logger.error("RAGFlow delete_agent failed: %s", resp.get("message"))
            raise ValueError(str(resp.get("message") or "agent_delete_failed"))

        # Fallback: some versions accept batch delete.
        resp2 = self._client.delete_json("/api/v1/agents", body={"ids": [agent_id]})
        if resp2 and resp2.get("code") == 0:
            self._chat_ref_cache = None
            self._chat_ref_cache_at_s = 0.0
            return True
        if resp2 and _is_not_found(resp2):
            raise ValueError("agent_not_found")
        if resp2 and resp2.get("code") != 0:
            self.logger.error("RAGFlow delete_agent failed: %s", resp2.get("message"))
            raise ValueError(str(resp2.get("message") or "agent_delete_failed"))
        return False

    def list_all_chat_ids(self, *, page_size: int = 1000) -> list[str]:
        """
        Return all chat/agent identifiers in permission-group storage format:
        - chats:  'chat_<id>'
        - agents: 'agent_<id>'
        """
        chats = self.list_chats(page_size=page_size)
        agents = self.list_agents(page_size=page_size)

        result: list[str] = []
        for chat in chats:
            if isinstance(chat, dict) and chat.get("id"):
                result.append(f"chat_{chat['id']}")
        for agent in agents:
            if isinstance(agent, dict) and agent.get("id"):
                result.append(f"agent_{agent['id']}")
        return result

    def get_chat_ref_index(self, *, ttl_s: float = 30.0, page_size: int = 1000) -> dict[str, str]:
        """
        Map raw ids -> canonical permission-group refs (chat_<id> / agent_<id>).
        """
        from time import time as _time

        now_s = _time()
        if self._chat_ref_cache and (now_s - self._chat_ref_cache_at_s) <= ttl_s:
            return self._chat_ref_cache

        index: dict[str, str] = {}
        for ref in self.list_all_chat_ids(page_size=page_size):
            if not isinstance(ref, str) or not ref:
                continue
            if ref.startswith("chat_"):
                index[ref[5:]] = ref
            elif ref.startswith("agent_"):
                index[ref[6:]] = ref

        self._chat_ref_cache = index
        self._chat_ref_cache_at_s = now_s
        return index

    def normalize_chat_ref(self, ref: str) -> str:
        """
        Accept raw id or permission-group ref; return canonical permission-group ref when possible.
        """
        if not isinstance(ref, str) or not ref:
            return ref
        if ref.startswith("chat_") or ref.startswith("agent_"):
            return ref
        try:
            return self.get_chat_ref_index().get(ref) or ref
        except Exception:
            return ref

    async def agent_chat(
        self,
        agent_id: str,
        question: str,
        stream: bool = True,
        session_id: Optional[str] = None,
        inputs: Optional[dict] = None,
        user_id: Optional[str] = None
    ) -> AsyncIterator[dict]:
        """
        与搜索体对话（流式）

        Args:
            agent_id: 搜索体ID
            question: 问题
            stream: 是否流式输出
            session_id: 会话ID，如果为None则创建新会话
            inputs: 额外的输入参数
            user_id: 用户ID

        Yields:
            聊天响应数据块
        """
        self._reload_config_if_changed()
        body: dict[str, Any] = {"question": question, "stream": stream}
        if session_id:
            body["session_id"] = session_id
        if inputs:
            body["inputs"] = inputs
        if user_id:
            body["user"] = user_id

        if stream:
            for obj in self._client.post_sse(f"/api/v1/agents/{agent_id}/completions", body=body, timeout_s=30):
                yield obj
            return

        payload = self._client.post_json(f"/api/v1/agents/{agent_id}/completions", body=body)
        if payload is None:
            yield {"code": -1, "message": "Agent chat request failed"}
            return
        yield payload

    def retrieve_chunks(
        self,
        question: str,
        dataset_ids: List[str],
        page: int = 1,
        page_size: int = 30,
        similarity_threshold: float = 0.2,
        top_k: int = 1024,
        keyword: bool = False,
        highlight: bool = False
    ) -> Dict[str, Any]:
        """
        在知识库中检索文本块

        Args:
            question: 查询问题或关键词
            dataset_ids: 知识库ID列表
            page: 页码，默认1
            page_size: 每页数量，默认30
            similarity_threshold: 相似度阈值（0-1），默认0.2
            top_k: 向量计算参与的chunk数量，默认1024
            keyword: 是否启用关键词匹配，默认False
            highlight: 是否高亮匹配词，默认False

        Returns:
            检索结果字典，包含：
            - chunks: 文本块列表
            - total: 总数量
            - page: 当前页码
            - page_size: 每页数量
        """
        self._reload_config_if_changed()
        body: dict[str, Any] = {
            "question": question,
            "dataset_ids": dataset_ids,
            "page": page,
            "page_size": page_size,
            "similarity_threshold": similarity_threshold,
            "top_k": top_k,
            "keyword": keyword,
            "highlight": highlight,
        }
        payload = self._client.post_json("/api/v1/retrieval", body=body)
        if not payload:
            return {"chunks": [], "total": 0}
        if payload.get("code") != 0:
            self.logger.error("Failed to retrieve chunks: %s", payload.get("message"))
            return {"chunks": [], "total": 0}
        data = payload.get("data")
        return data if isinstance(data, dict) else {"chunks": [], "total": 0}
