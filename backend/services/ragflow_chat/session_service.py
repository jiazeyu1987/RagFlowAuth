from typing import Optional, Dict, Any, List


class RagflowChatSessionService:
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
        self._chat_ref_cache = None
        self._chat_ref_cache_at_s = 0.0
        return data if isinstance(data, dict) else None

    def update_chat(self, chat_id: str, payload: dict[str, Any]) -> Optional[dict]:
        self._reload_config_if_changed()
        body = self._sanitize_chat_payload(payload, for_update=True)
        unready_dataset_ids = self._find_unready_dataset_ids(self._extract_dataset_ids(body))
        if unready_dataset_ids:
            raise ValueError(f"chat_dataset_not_ready: {','.join(unready_dataset_ids)}")

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
                    current = self.get_chat(chat_id) or {}
                    cur_ids = self._extract_dataset_ids(current)
                    desired_ids = self._extract_dataset_ids(body)

                    # If the chat currently has no dataset linkage, this lock almost always comes
                    # from stale hidden parsed-file bindings copied from another chat. Clear them
                    # once and retry the user's desired dataset update.
                    if not cur_ids:
                        clear_fields = self._parsed_file_clear_fields(current)
                        if clear_fields:
                            self.logger.warning(
                                "RAGFlow update_chat hit parsed-file ownership on an unbound chat; clearing stale parsed-file bindings before retry. desired=%s",
                                desired_ids,
                            )
                            self.clear_chat_parsed_files(chat_id)
                            resp_after_clear = self._client.put_json(f"/api/v1/chats/{chat_id}", body=minimal)
                            if resp_after_clear and resp_after_clear.get("code") == 0:
                                data_after_clear = _coerce_updated_chat(resp_after_clear, minimal)
                                self._chat_ref_cache = None
                                self._chat_ref_cache_at_s = 0.0
                                return data_after_clear
                            if resp_after_clear and resp_after_clear.get("code") != 0 and not self._is_dataset_ownership_error(resp_after_clear):
                                self.logger.error("RAGFlow update_chat failed (retry#clear): %s", resp_after_clear.get("message"))
                                raise ValueError(str(resp_after_clear.get("message") or "chat_update_failed"))
                            if resp_after_clear:
                                resp2 = resp_after_clear

                    # Second-chance: some RAGFlow versions require keeping datasets that already
                    # own existing parsed files. In that case, we cannot "deselect" those datasets
                    # via update. Merge current dataset ids and retry to keep the chat usable.
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

