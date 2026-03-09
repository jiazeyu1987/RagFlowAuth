from typing import Optional, Dict, Any, List


class RagflowChatSessionService:
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
            if self._is_dataset_ownership_error(resp):
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
                if resp2 and resp2.get("code") != 0 and self._is_dataset_ownership_error(resp2):
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
                    if self._is_dataset_ownership_error(resp2):
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

        # Prefer batch delete first; it's the most common contract across RAGFlow versions.
        resp = self._client.delete_json("/api/v1/chats", body={"ids": [chat_id]})
        if resp and resp.get("code") == 0:
            self._chat_ref_cache = None
            self._chat_ref_cache_at_s = 0.0
            return True

        if resp and self._is_not_found_error(resp):
            raise ValueError("chat_not_found")

        if resp and not self._is_method_not_allowed_error(resp):
            self.logger.error("RAGFlow delete_chat failed: %s", resp.get("message"))
            raise ValueError(str(resp.get("message") or "chat_delete_failed"))

        # Fallback 1: older variants support DELETE /api/v1/chats/{id}
        resp2 = self._client.delete_json(f"/api/v1/chats/{chat_id}", body={})
        if resp2 and resp2.get("code") == 0:
            self._chat_ref_cache = None
            self._chat_ref_cache_at_s = 0.0
            return True
        if resp2 and self._is_not_found_error(resp2):
            raise ValueError("chat_not_found")
        if resp2 and (not self._is_method_not_allowed_error(resp2)):
            self.logger.error("RAGFlow delete_chat failed: %s", resp2.get("message"))
            raise ValueError(str(resp2.get("message") or "chat_delete_failed"))

        # Fallback 2: some gateways strip/deny DELETE bodies; use query params: ?ids=<id>
        resp3 = self._client.delete_json("/api/v1/chats", params={"ids": chat_id}, body=None)
        if resp3 and resp3.get("code") == 0:
            self._chat_ref_cache = None
            self._chat_ref_cache_at_s = 0.0
            return True
        if resp3 and self._is_not_found_error(resp3):
            raise ValueError("chat_not_found")
        if resp3 and resp3.get("code") != 0:
            self.logger.error("RAGFlow delete_chat failed: %s", resp3.get("message"))
            raise ValueError(str(resp3.get("message") or "chat_delete_failed"))
        return False

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

        resp = self._client.delete_json(f"/api/v1/agents/{agent_id}", body={})
        if resp and resp.get("code") == 0:
            self._chat_ref_cache = None
            self._chat_ref_cache_at_s = 0.0
            return True
        if resp and self._is_not_found_error(resp):
            raise ValueError("agent_not_found")
        if resp and (not self._is_method_not_allowed_error(resp)):
            self.logger.error("RAGFlow delete_agent failed: %s", resp.get("message"))
            raise ValueError(str(resp.get("message") or "agent_delete_failed"))

        # Fallback: some versions accept batch delete.
        resp2 = self._client.delete_json("/api/v1/agents", body={"ids": [agent_id]})
        if resp2 and resp2.get("code") == 0:
            self._chat_ref_cache = None
            self._chat_ref_cache_at_s = 0.0
            return True
        if resp2 and self._is_not_found_error(resp2):
            raise ValueError("agent_not_found")
        if resp2 and resp2.get("code") != 0:
            self.logger.error("RAGFlow delete_agent failed: %s", resp2.get("message"))
            raise ValueError(str(resp2.get("message") or "agent_delete_failed"))
        return False
