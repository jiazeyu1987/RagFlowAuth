from typing import Optional, AsyncIterator, Any


class RagflowChatStreamService:
    async def chat(
        self,
        chat_id: str,
        question: str,
        stream: bool = True,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        trace_id: Optional[str] = None,
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
            for obj in self._client.post_sse(
                f"/api/v1/chats/{chat_id}/completions",
                body=body,
                timeout_s=30,
                trace_id=trace_id,
            ):
                yield obj
            return

        payload = self._client.post_json(f"/api/v1/chats/{chat_id}/completions", body=body)
        if payload is None:
            yield {"code": -1, "message": "Chat request failed"}
            return
        yield payload

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
