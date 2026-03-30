from __future__ import annotations

import asyncio
import threading
from typing import Any, AsyncIterator, Callable, Optional


class RagflowChatStreamService:
    async def _stream_sync_iterator(self, iterator_factory: Callable[[], Any]) -> AsyncIterator[dict]:
        """
        Bridge a blocking sync iterator into async world without blocking the event loop.

        RAGFlow HTTP client yields SSE chunks via `requests`, which is sync/blocking.
        Running it in a background thread keeps FastAPI's event loop responsive.
        """
        loop = asyncio.get_running_loop()
        queue: asyncio.Queue[tuple[str, Any]] = asyncio.Queue(maxsize=64)

        def _emit(kind: str, payload: Any) -> None:
            try:
                fut = asyncio.run_coroutine_threadsafe(queue.put((kind, payload)), loop)
                fut.result()
            except Exception:
                # If loop is closing, best-effort drop.
                pass

        def _worker() -> None:
            try:
                iterator = iterator_factory()
                for item in iterator:
                    _emit("item", item)
            except Exception as exc:
                _emit("error", exc)
            finally:
                _emit("done", None)

        threading.Thread(target=_worker, daemon=True, name="ragflow-sse-forwarder").start()

        while True:
            kind, payload = await queue.get()
            if kind == "item":
                if isinstance(payload, dict):
                    yield payload
                else:
                    yield {"code": 0, "data": {"answer": str(payload)}}
                continue
            if kind == "error":
                try:
                    self.logger.error("RAGFlow SSE bridge failed: %s", payload)
                except Exception:
                    pass
                yield {"code": -1, "message": f"sse_bridge_error: {payload}"}
            break

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
            async for obj in self._stream_sync_iterator(
                lambda: self._client.post_sse(
                    f"/api/v1/chats/{chat_id}/completions",
                    body=body,
                    timeout_s=30,
                    trace_id=trace_id,
                )
            ):
                yield obj
            return

        payload = await asyncio.to_thread(
            lambda: self._client.post_json(f"/api/v1/chats/{chat_id}/completions", body=body)
        )
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
            async for obj in self._stream_sync_iterator(
                lambda: self._client.post_sse(f"/api/v1/agents/{agent_id}/completions", body=body, timeout_s=30)
            ):
                yield obj
            return

        payload = await asyncio.to_thread(
            lambda: self._client.post_json(f"/api/v1/agents/{agent_id}/completions", body=body)
        )
        if payload is None:
            yield {"code": -1, "message": "Agent chat request failed"}
            return
        yield payload
