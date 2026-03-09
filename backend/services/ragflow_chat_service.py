import logging
from typing import Optional

from .ragflow_connection import RagflowConnection, create_ragflow_connection
from .ragflow_config import (
    DEFAULT_RAGFLOW_BASE_URL,
    effective_api_key,
    format_api_key_for_log,
    load_ragflow_config,
)
from .ragflow_http_client import RagflowHttpClientConfig
from .ragflow_chat import (
    RagflowChatSessionService,
    RagflowChatStreamService,
    RagflowCitationService,
    RagflowPromptBuilder,
)


class RagflowChatService(
    RagflowChatSessionService,
    RagflowChatStreamService,
    RagflowCitationService,
    RagflowPromptBuilder,
):
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
