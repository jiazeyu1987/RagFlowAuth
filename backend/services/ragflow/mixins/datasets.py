from __future__ import annotations

from time import time
from typing import List

from ...ragflow_config import is_placeholder_api_key


class RagflowDatasetsMixin:
    def list_all_kb_names(self) -> list[str]:
        datasets = self.list_datasets() or []
        seen: set[str] = set()
        names: list[str] = []
        for ds in datasets:
            if not isinstance(ds, dict):
                continue
            name = ds.get("name")
            if not isinstance(name, str) or not name:
                continue
            if name in seen:
                continue
            seen.add(name)
            names.append(name)
        return names

    def list_all_datasets(self) -> list[dict[str, str]]:
        datasets = self.list_datasets() or []
        seen: set[str] = set()
        result: list[dict[str, str]] = []
        for ds in datasets:
            if not isinstance(ds, dict):
                continue
            dataset_id = ds.get("id")
            name = ds.get("name")
            if not isinstance(dataset_id, str) or not dataset_id:
                continue
            if not isinstance(name, str) or not name:
                continue
            if dataset_id in seen:
                continue
            seen.add(dataset_id)
            result.append({"id": dataset_id, "name": name})
        return result

    def get_dataset_index(self, *, ttl_s: float = 30.0) -> dict[str, dict[str, str]]:
        now_s = time()
        if self._dataset_index_cache and (now_s - self._dataset_index_cache_at_s) <= ttl_s:
            return self._dataset_index_cache

        by_id: dict[str, str] = {}
        by_name: dict[str, str] = {}
        for ds in self.list_all_datasets():
            dataset_id = ds["id"]
            name = ds["name"]
            by_id[dataset_id] = name
            by_name[name] = dataset_id

        cache = {"by_id": by_id, "by_name": by_name}
        self._dataset_index_cache = cache
        self._dataset_index_cache_at_s = now_s
        return cache

    def normalize_dataset_id(self, ref: str) -> str | None:
        if not isinstance(ref, str) or not ref:
            return None
        index = self.get_dataset_index()
        by_id = index.get("by_id", {})
        by_name = index.get("by_name", {})
        if ref in by_id:
            return ref
        if ref in by_name:
            return by_name[ref]
        return None

    def normalize_dataset_ids(self, refs: list[str] | set[str] | tuple[str, ...]) -> list[str]:
        ids: list[str] = []
        seen: set[str] = set()
        for ref in refs:
            dataset_id = self.normalize_dataset_id(ref)
            if not dataset_id or dataset_id in seen:
                continue
            seen.add(dataset_id)
            ids.append(dataset_id)
        return ids

    def resolve_dataset_name(self, ref: str) -> str | None:
        if not isinstance(ref, str) or not ref:
            return None
        index = self.get_dataset_index()
        by_id = index.get("by_id", {})
        by_name = index.get("by_name", {})
        if ref in by_name:
            return ref
        if ref in by_id:
            return by_id[ref]
        return None

    def resolve_dataset_names(self, refs: list[str] | set[str] | tuple[str, ...]) -> list[str]:
        names: list[str] = []
        seen: set[str] = set()
        for ref in refs:
            name = self.resolve_dataset_name(ref)
            if not name or name in seen:
                continue
            seen.add(name)
            names.append(name)
        return names

    def list_datasets(self) -> List[dict]:
        api_key = self.config.get("api_key", "")
        if not self.client:
            # Fallback to HTTP API list endpoint when SDK client isn't available.
            if is_placeholder_api_key(api_key):
                return []
            datasets = self._http.get_list("/api/v1/datasets", context="list_datasets")
            result: list[dict] = []
            for dataset in datasets:
                if not isinstance(dataset, dict):
                    continue
                result.append(
                    {
                        "id": dataset.get("id", ""),
                        "name": dataset.get("name", ""),
                    }
                )
            return result

        try:
            datasets = self.client.list_datasets()
            result = []
            for dataset in datasets:
                if hasattr(dataset, "name"):
                    result.append(
                        {
                            "id": getattr(dataset, "id", ""),
                            "name": dataset.name,
                        }
                    )
                elif isinstance(dataset, dict):
                    result.append(
                        {
                            "id": dataset.get("id", ""),
                            "name": dataset.get("name", ""),
                        }
                    )
            return result
        except Exception as e:
            self.logger.error(f"Failed to list datasets: {e}")
            return []

