import logging

from .ragflow_config import (
    DEFAULT_RAGFLOW_BASE_URL,
    effective_api_key,
    format_api_key_for_log,
    is_placeholder_api_key,
    load_ragflow_config,
)
from .ragflow_connection import RagflowConnection, create_ragflow_connection
from .ragflow_http_client import RagflowHttpClientConfig
from .ragflow.mixins.datasets import RagflowDatasetsMixin
from .ragflow.mixins.documents import RagflowDocumentsMixin


class RagflowService(RagflowDatasetsMixin, RagflowDocumentsMixin):
    def __init__(
        self,
        config_path: str = None,
        logger: logging.Logger = None,
        *,
        connection: RagflowConnection | None = None,
    ):
        self.logger = logger or logging.getLogger(__name__)
        conn = connection or create_ragflow_connection(config_path=config_path, logger=self.logger)
        self.config_path = conn.config_path
        self.config = conn.config
        self.client = None
        self._http = conn.http
        self._dataset_index_cache: dict[str, dict[str, str]] | None = None
        self._dataset_index_cache_at_s: float = 0.0
        self._config_mtime_ns: int | None = None
        self._config_sig: tuple[str, str, float] | None = None

        try:
            self._init_client()
        except Exception as e:
            self.logger.warning(f"RAGFlow client initialization failed: {e}")

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
        """
        Keep runtime config in sync with `ragflow_config.json`.

        Reason: `create_dependencies()` constructs a single `RagflowService` instance at startup.
        If users/tooling update `ragflow_config.json` (e.g. base_url guardrail), the running
        backend must pick it up without requiring a restart.
        """
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

        old_base_url = (self._config_sig[0] if self._config_sig else "") or str(self.config.get("base_url", ""))
        new_config["base_url"] = new_base_url
        new_config["api_key"] = new_api_key
        self.config = new_config
        self._http.set_config(RagflowHttpClientConfig(base_url=new_base_url, api_key=new_api_key, timeout_s=new_timeout_s))
        self._dataset_index_cache = None
        self._dataset_index_cache_at_s = 0.0

        try:
            if is_placeholder_api_key(new_api_key):
                self.client = None
            else:
                self._init_client()
        except Exception as e:
            self.client = None
            self.logger.warning(f"RAGFlow client re-init failed: {e}")

        self._config_mtime_ns = mtime_ns
        self._config_sig = new_sig
        if old_base_url and new_base_url and old_base_url != new_base_url:
            try:
                logging.getLogger("uvicorn.error").warning(
                    "RAGFlow base_url reloaded: %s -> %s api_key=%s",
                    old_base_url,
                    new_base_url,
                    format_api_key_for_log(new_api_key),
                )
            except Exception:
                pass

    def _init_client(self):
        from ragflow_sdk import RAGFlow

        api_key = self.config.get("api_key", "")
        base_url = self.config.get("base_url", DEFAULT_RAGFLOW_BASE_URL)

        if is_placeholder_api_key(api_key):
            raise ValueError("RAGFlow API key not configured")

        try:
            logging.getLogger("uvicorn.error").warning(
                "RAGFlow client init: base_url=%s api_key=%s",
                base_url,
                format_api_key_for_log(api_key),
            )
        except Exception:
            pass
        self.client = RAGFlow(api_key=api_key, base_url=base_url)

    def _normalize_dataset_name_for_ops(self, dataset_ref: str) -> str:
        # Accept dataset_id or dataset_name. Prefer resolving ids to names for SDK calls.
        try:
            name = self.resolve_dataset_name(dataset_ref)
        except Exception:
            name = None
        return name or dataset_ref

    def _find_dataset_by_name(self, dataset_name: str):
        if not self.client:
            return None

        try:
            datasets = self.client.list_datasets()
            for dataset in datasets:
                if hasattr(dataset, "name"):
                    if dataset.name == dataset_name:
                        return dataset
                elif isinstance(dataset, dict):
                    if dataset.get("name") == dataset_name:
                        return dataset
                else:
                    if dataset_name in str(dataset):
                        return dataset
        except Exception as e:
            self.logger.error(f"Failed to find dataset: {e}")
        return None
