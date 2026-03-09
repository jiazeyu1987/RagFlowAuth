from typing import Any, Dict, List


class RagflowCitationService:
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
