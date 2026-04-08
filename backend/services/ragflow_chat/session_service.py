from typing import Optional, Dict, Any, List


from .session_support import RagflowChatSessionSupport


class RagflowChatSessionService(RagflowChatSessionSupport):
    @staticmethod
    def _coerce_count(value: Any) -> int | None:
        if value is None:
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def _find_unready_dataset_ids(self, dataset_ids: list[str]) -> list[str]:
        normalized_ids: list[str] = []
        seen: set[str] = set()
        for raw in dataset_ids or []:
            dataset_id = str(raw or "").strip()
            if not dataset_id or dataset_id in seen:
                continue
            seen.add(dataset_id)
            normalized_ids.append(dataset_id)

        if not normalized_ids:
            return []

        if not hasattr(self._client, "get_list"):
            return []

        datasets = self._client.get_list(
            "/api/v1/datasets",
            params={"page": 1, "page_size": 1000},
            context="list_datasets_for_chat_binding",
        )
        dataset_map: dict[str, dict[str, Any]] = {}
        for item in datasets or []:
            if not isinstance(item, dict):
                continue
            dataset_id = str(item.get("id") or "").strip()
            if dataset_id:
                dataset_map[dataset_id] = item

        unready: list[str] = []
        for dataset_id in normalized_ids:
            item = dataset_map.get(dataset_id)
            if not item:
                continue
            chunk_count = self._coerce_count(item.get("chunk_count"))
            if chunk_count is None:
                chunk_count = self._coerce_count(item.get("chunk_num"))
            document_count = self._coerce_count(item.get("document_count"))
            if chunk_count is not None and chunk_count <= 0:
                unready.append(dataset_id)
                continue
            if chunk_count is None and document_count is not None and document_count <= 0:
                unready.append(dataset_id)
        return unready

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
        鍒楀嚭鑱婂ぉ鍔╂墜

        Args:
            page: 椤电爜锛岄粯璁?
            page_size: 姣忛〉鏁伴噺锛岄粯璁?0
            orderby: 鎺掑簭瀛楁锛岄粯璁reate_time
            desc: 鏄惁闄嶅簭锛岄粯璁rue
            name: 鎸夊悕绉拌繃婊?            chat_id: 鎸塈D杩囨护

        Returns:
            鑱婂ぉ鍔╂墜鍒楄〃
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
        鑾峰彇鍗曚釜鑱婂ぉ鍔╂墜淇℃伅

        Args:
            chat_id: 鑱婂ぉ鍔╂墜ID

        Returns:
            鑱婂ぉ鍔╂墜淇℃伅锛屽鏋滀笉瀛樺湪杩斿洖None
        """
        chats = self.list_chats(chat_id=chat_id)
        return chats[0] if chats else None

    def create_chat(self, payload: dict[str, Any]) -> Optional[dict]:
        self._reload_config_if_changed()
        body = self._sanitize_chat_payload(payload, for_update=False)
        unready_dataset_ids = self._find_unready_dataset_ids(self._extract_dataset_ids(body))
        if unready_dataset_ids:
            raise ValueError(f"chat_dataset_not_ready: {','.join(unready_dataset_ids)}")
        resp = self._client.post_json("/api/v1/chats", body=body)
        if not resp:
            return None
        if resp.get("code") != 0:
            self.logger.error("RAGFlow create_chat failed: %s", resp.get("message"))
            raise ValueError(str(resp.get("message") or "chat_create_failed"))
        data = resp.get("data")
        self._invalidate_chat_ref_cache()
        return data if isinstance(data, dict) else None

    def update_chat(self, chat_id: str, payload: dict[str, Any]) -> Optional[dict]:
        self._reload_config_if_changed()
        body = self._sanitize_chat_payload(payload, for_update=True)
        unready_dataset_ids = self._find_unready_dataset_ids(self._extract_dataset_ids(body))
        if unready_dataset_ids:
            raise ValueError(f"chat_dataset_not_ready: {','.join(unready_dataset_ids)}")

        resp = self._client.put_json(f"/api/v1/chats/{chat_id}", body=body)
        if not resp:
            # Best-effort: if update was applied but response was missing/invalid, avoid false failure.
            verified = self._verify_update_applied(chat_id, body)
            if verified:
                self._invalidate_chat_ref_cache()
                return verified
            return None
        if resp.get("code") != 0:
            if self._is_dataset_ownership_error(resp):
                data = self._retry_locked_chat_update(chat_id, body, resp)
                self._invalidate_chat_ref_cache()
                return data

            self.logger.error("RAGFlow update_chat failed: %s", resp.get("message"))
            raise ValueError(str(resp.get("message") or "chat_update_failed"))

        data = self._coerce_updated_chat(chat_id, resp, body)
        if not data:
            # Some deployments return a wrapper without `code` (or other oddities). Try to verify.
            data = self._verify_update_applied(chat_id, body)
        self._invalidate_chat_ref_cache()
        return data

    def delete_chat(self, chat_id: str) -> bool:
        self._reload_config_if_changed()
        return self._delete_with_compat(
            [
                {"path": "/api/v1/chats", "body": {"ids": [chat_id]}},
                {"path": f"/api/v1/chats/{chat_id}", "body": {}},
                {"path": "/api/v1/chats", "params": {"ids": chat_id}, "body": None},
            ],
            not_found_code="chat_not_found",
            generic_error="chat_delete_failed",
            log_label="RAGFlow delete_chat failed",
        )

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
            data = self._coerce_updated_chat(chat_id, resp, payload)
            self._invalidate_chat_ref_cache()
            return data

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
        鍒涘缓鑱婂ぉ浼氳瘽

        Args:
            chat_id: 鑱婂ぉ鍔╂墜ID
            name: 浼氳瘽鍚嶇О
            user_id: 鐢ㄦ埛ID锛堝彲閫夛級

        Returns:
            鍒涘缓鐨勪細璇濅俊鎭紝澶辫触杩斿洖None
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
        鍒楀嚭鑱婂ぉ鍔╂墜鐨勬墍鏈変細璇?
        Args:
            chat_id: 鑱婂ぉ鍔╂墜ID
            page: 椤电爜
            page_size: 姣忛〉鏁伴噺
            orderby: 鎺掑簭瀛楁
            desc: 鏄惁闄嶅簭
            name: 鎸夊悕绉拌繃婊?            session_id: 鎸変細璇滻D杩囨护
            user_id: 鎸夌敤鎴稩D杩囨护

        Returns:
            浼氳瘽鍒楄〃
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
        鍒犻櫎鑱婂ぉ浼氳瘽

        Args:
            chat_id: 鑱婂ぉ鍔╂墜ID
            session_ids: 瑕佸垹闄ょ殑浼氳瘽ID鍒楄〃锛屽鏋滀负None鍒欏垹闄ゆ墍鏈変細璇?            user_id: 鐢ㄦ埛ID锛堢敤浜庢湰鍦版暟鎹簱鏍囪锛?
        Returns:
            鏄惁鎴愬姛
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
        鍒楀嚭鎵€鏈夋悳绱綋 (Agents)

        Args:
            page: 椤电爜锛岄粯璁?
            page_size: 姣忛〉鏁伴噺锛岄粯璁?0
            orderby: 鎺掑簭瀛楁锛岄粯璁reate_time
            desc: 鏄惁闄嶅簭锛岄粯璁rue
            name: 鎸夊悕绉拌繃婊?            id: 鎸塈D杩囨护

        Returns:
            鎼滅储浣撳垪琛?        """
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
        鑾峰彇鍗曚釜鎼滅储浣撲俊鎭?
        Args:
            agent_id: 鎼滅储浣揑D

        Returns:
            鎼滅储浣撲俊鎭紝濡傛灉涓嶅瓨鍦ㄨ繑鍥濶one
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
            self._invalidate_chat_ref_cache()
            return data

        # Best-effort: refetch newly created agent by title (newest first).
        agents = self.list_agents(page=1, page_size=1000, orderby="create_time", desc=True)
        for agent in agents:
            if not isinstance(agent, dict):
                continue
            if str(agent.get("title") or "").strip() == title:
                self._invalidate_chat_ref_cache()
                return agent

        self._invalidate_chat_ref_cache()
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

        self._invalidate_chat_ref_cache()
        return self.get_agent(agent_id) or {"id": agent_id, "title": body.get("title")}

    def delete_agent(self, agent_id: str) -> bool:
        """
        Delete an agent in RAGFlow.

        Observed compatibility:
        - DELETE /api/v1/agents/{id} works
        - DELETE /api/v1/agents with body {"ids":[...]} may return 405
        """
        self._reload_config_if_changed()
        return self._delete_with_compat(
            [
                {"path": f"/api/v1/agents/{agent_id}", "body": {}},
                {"path": "/api/v1/agents", "body": {"ids": [agent_id]}},
            ],
            not_found_code="agent_not_found",
            generic_error="agent_delete_failed",
            log_label="RAGFlow delete_agent failed",
        )

