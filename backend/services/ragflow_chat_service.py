import logging
from typing import Optional, List, AsyncIterator, Dict, Any

from .ragflow_connection import RagflowConnection, create_ragflow_connection


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
