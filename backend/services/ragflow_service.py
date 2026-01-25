import logging

from .ragflow_config import (
    DEFAULT_RAGFLOW_BASE_URL,
    is_placeholder_api_key,
)
from .ragflow_connection import RagflowConnection, create_ragflow_connection
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

        try:
            self._init_client()
        except Exception as e:
            self.logger.warning(f"RAGFlow client initialization failed: {e}")

    def _init_client(self):
        from ragflow_sdk import RAGFlow

        api_key = self.config.get("api_key", "")
        base_url = self.config.get("base_url", DEFAULT_RAGFLOW_BASE_URL)

        if is_placeholder_api_key(api_key):
            raise ValueError("RAGFlow API key not configured")

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

