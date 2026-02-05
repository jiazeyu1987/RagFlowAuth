from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Iterator

import requests


@dataclass(frozen=True)
class RagflowHttpClientConfig:
    base_url: str
    api_key: str
    timeout_s: float = 10.0


class RagflowHttpClient:
    def __init__(self, config: RagflowHttpClientConfig, *, logger: logging.Logger | None = None):
        self._config = config
        self._logger = logger or logging.getLogger(__name__)

    @property
    def config(self) -> RagflowHttpClientConfig:
        return self._config

    def set_config(self, config: RagflowHttpClientConfig) -> None:
        self._config = config

    def headers(self) -> dict[str, str]:
        return self._headers()

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._config.api_key}",
            "Content-Type": "application/json",
        }

    def _timeout(self, timeout_s: float | None) -> float:
        return float(timeout_s if timeout_s is not None else self._config.timeout_s)

    def get_json(self, path: str, *, params: dict[str, Any] | None = None) -> dict[str, Any] | None:
        url = f"{self._config.base_url.rstrip('/')}{path}"
        try:
            resp = requests.get(url, headers=self._headers(), params=params, timeout=self._timeout(None))
        except Exception as exc:
            self._logger.error("RAGFlow GET %s failed: %s", url, exc)
            return None

        if resp.status_code != 200:
            self._logger.error("RAGFlow GET %s failed: HTTP %s", url, resp.status_code)
            return None

        try:
            data = resp.json()
        except Exception as exc:
            self._logger.error("RAGFlow GET %s invalid JSON: %s", url, exc)
            return None

        return data if isinstance(data, dict) else None

    def post_json(
        self, path: str, *, body: dict[str, Any] | None = None, params: dict[str, Any] | None = None
    ) -> dict[str, Any] | None:
        url = f"{self._config.base_url.rstrip('/')}{path}"
        try:
            resp = requests.post(
                url,
                headers=self._headers(),
                params=params,
                json=body or {},
                timeout=self._timeout(None),
            )
        except Exception as exc:
            self._logger.error("RAGFlow POST %s failed: %s", url, exc)
            return None

        if resp.status_code != 200:
            self._logger.error("RAGFlow POST %s failed: HTTP %s", url, resp.status_code)
            return None

        try:
            data = resp.json()
        except Exception as exc:
            self._logger.error("RAGFlow POST %s invalid JSON: %s", url, exc)
            return None

        return data if isinstance(data, dict) else None

    def delete_json(
        self, path: str, *, body: dict[str, Any] | None = None, params: dict[str, Any] | None = None
    ) -> dict[str, Any] | None:
        url = f"{self._config.base_url.rstrip('/')}{path}"
        try:
            resp = requests.delete(
                url,
                headers=self._headers(),
                params=params,
                json=body or {},
                timeout=self._timeout(None),
            )
        except Exception as exc:
            self._logger.error("RAGFlow DELETE %s failed: %s", url, exc)
            return None

        if resp.status_code != 200:
            self._logger.error("RAGFlow DELETE %s failed: HTTP %s", url, resp.status_code)
            return None

        try:
            data = resp.json()
        except Exception as exc:
            self._logger.error("RAGFlow DELETE %s invalid JSON: %s", url, exc)
            return None

        return data if isinstance(data, dict) else None

    def post_sse(
        self,
        path: str,
        *,
        body: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        timeout_s: float | None = None,
    ) -> Iterator[dict[str, Any]]:
        """
        POST an SSE endpoint and yield decoded JSON objects from `data:` lines.

        Expected payload format per line:
        - `data: {...json...}`
        """
        url = f"{self._config.base_url.rstrip('/')}{path}"
        try:
            resp = requests.post(
                url,
                headers=self._headers(),
                params=params,
                json=body or {},
                stream=True,
                timeout=self._timeout(timeout_s),
            )
        except Exception as exc:
            self._logger.error("RAGFlow SSE POST %s failed: %s", url, exc)
            yield {"code": -1, "message": str(exc)}
            return

        if resp.status_code != 200:
            self._logger.error("RAGFlow SSE POST %s failed: HTTP %s", url, resp.status_code)
            yield {"code": resp.status_code, "message": f"HTTP {resp.status_code}"}
            return

        for line in resp.iter_lines():
            if not line:
                continue
            try:
                text = line.decode("utf-8")
            except Exception:
                continue
            if not text.startswith("data:"):
                continue
            data_str = text[5:].strip()
            if not data_str:
                continue
            if data_str == "[DONE]":
                return
            try:
                import json as _json

                obj = _json.loads(data_str)
            except Exception:
                self._logger.warning("Failed to parse SSE data: %s", data_str)
                continue
            if isinstance(obj, dict):
                yield obj

    def coerce_list(self, value: Any, *, context: str) -> list[dict[str, Any]]:
        if value is None:
            return []
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
        self._logger.error("Unexpected %s response type: %s", context, type(value).__name__)
        return []

    def get_list(
        self,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        context: str,
        data_field: str = "data",
        ok_code: int = 0,
    ) -> list[dict[str, Any]]:
        payload = self.get_json(path, params=params)
        if not payload:
            return []
        if payload.get("code") != ok_code:
            self._logger.error("RAGFlow %s failed: %s", context, payload.get("message"))
            return []
        return self.coerce_list(payload.get(data_field, []), context=context)
