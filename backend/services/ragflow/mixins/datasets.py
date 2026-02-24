from __future__ import annotations

from time import time
from typing import List

from ...ragflow_config import is_placeholder_api_key


class RagflowDatasetsMixin:
    # RAGFlow dataset create/update endpoints reject unknown fields (pydantic `extra=forbid`).
    # Keep a strict allow-list here to avoid forwarding "read-only" or computed fields from
    # UI copies (e.g. chunk_count, task ids, status), which would make the mutation fail.
    _DATASET_CREATE_ALLOWED_KEYS: set[str] = {
        "name",
        "description",
        "chunk_method",
        "embedding_model",
        "avatar",
    }
    _DATASET_UPDATE_ALLOWED_KEYS: set[str] = {
        "name",
        "description",
        "chunk_method",
        "embedding_model",
        "avatar",
        # Update-only knobs (create forbids these in current RAGFlow version).
        "pagerank",
    }

    def _sanitize_dataset_mutation_body(self, body: dict, *, allowed_keys: set[str]) -> dict:
        if not isinstance(body, dict):
            return {}
        cleaned: dict = {}
        for k, v in body.items():
            if not isinstance(k, str):
                continue
            if k not in allowed_keys:
                continue
            cleaned[k] = v
        return cleaned

    def _sanitize_dataset_create_body(self, body: dict) -> dict:
        return self._sanitize_dataset_mutation_body(body, allowed_keys=self._DATASET_CREATE_ALLOWED_KEYS)

    def _sanitize_dataset_update_body(self, body: dict) -> dict:
        return self._sanitize_dataset_mutation_body(body, allowed_keys=self._DATASET_UPDATE_ALLOWED_KEYS)

    def _unwrap_dataset_payload(self, payload: dict | None) -> dict | None:
        """
        RAGFlow HTTP APIs usually return: {code, message, data}.
        Keep this helper permissive so we can survive minor upstream changes.
        """
        if not payload or not isinstance(payload, dict):
            return None
        # Common error shape: {code: nonzero, message: "...", data: null}
        if payload.get("code") not in (0, None):
            return None
        data = payload.get("data")
        if isinstance(data, dict):
            return data
        # Some endpoints may return the dataset object directly.
        if isinstance(payload.get("id"), (str, int)):
            return payload
        return None

    def _payload_error_message(self, payload: dict | None) -> str | None:
        if not payload or not isinstance(payload, dict):
            return None
        msg = payload.get("message")
        if isinstance(msg, str) and msg.strip():
            return msg.strip()
        return None

    def _payload_ok(self, payload: dict | None) -> bool:
        if not payload or not isinstance(payload, dict):
            return False
        return payload.get("code") in (0, None)

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
        reload_cfg = getattr(self, "_reload_config_if_changed", None)
        if callable(reload_cfg):
            reload_cfg()

        api_key = self.config.get("api_key", "")
        if not self.client:
            # Fallback to HTTP API list endpoint when SDK client isn't available.
            if is_placeholder_api_key(api_key):
                return []
            datasets = self._http.get_list("/api/v1/datasets", context="list_datasets")
            # Keep the full dataset objects from the upstream list endpoint. This enables UI features
            # like "delete only when empty" based on document_count/chunk_count.
            return [d for d in datasets if isinstance(d, dict)]

        try:
            datasets = self.client.list_datasets()
            result = []
            for dataset in datasets:
                if hasattr(dataset, "name"):
                    result.append(
                        {
                            "id": getattr(dataset, "id", ""),
                            "name": dataset.name,
                            "document_count": getattr(dataset, "document_count", None),
                            "chunk_count": getattr(dataset, "chunk_count", None),
                            "description": getattr(dataset, "description", None),
                        }
                    )
                elif isinstance(dataset, dict):
                    result.append(dict(dataset))
            return result
        except Exception as e:
            self.logger.error(f"Failed to list datasets: {e}")
            return []

    def get_dataset_detail(self, dataset_ref: str) -> dict | None:
        reload_cfg = getattr(self, "_reload_config_if_changed", None)
        if callable(reload_cfg):
            reload_cfg()

        if not isinstance(dataset_ref, str) or not dataset_ref.strip():
            return None

        api_key = self.config.get("api_key", "")
        if is_placeholder_api_key(api_key):
            return None

        # Best-effort normalize. If the index cache is stale and normalization misses, fall back to the ref.
        # This avoids false 404s right after create/update where the dataset index hasn't refreshed yet.
        dataset_id = dataset_ref
        try:
            normalize = getattr(self, "normalize_dataset_id", None)
            normalized = normalize(dataset_ref) if callable(normalize) else dataset_ref
            dataset_id = normalized or dataset_ref
        except Exception:
            dataset_id = dataset_ref

        # RAGFlow currently does not support GET /api/v1/datasets/{id} (returns 200 with code=100 MethodNotAllowed).
        # Use the list endpoint and pick the matching dataset object.
        datasets = self._http.get_list("/api/v1/datasets", context="list_datasets_for_detail")
        for ds in datasets:
            if not isinstance(ds, dict):
                continue
            ds_id = ds.get("id")
            ds_name = ds.get("name")
            if ds_id == dataset_id or ds_id == dataset_ref:
                return ds
            if ds_name == dataset_ref or ds_name == dataset_id:
                return ds
        return None

    def update_dataset(self, dataset_ref: str, updates: dict) -> dict | None:
        reload_cfg = getattr(self, "_reload_config_if_changed", None)
        if callable(reload_cfg):
            reload_cfg()

        if not isinstance(dataset_ref, str) or not dataset_ref.strip():
            return None

        if not isinstance(updates, dict):
            return None

        api_key = self.config.get("api_key", "")
        if is_placeholder_api_key(api_key):
            return None

        dataset_id = dataset_ref
        try:
            normalize = getattr(self, "normalize_dataset_id", None)
            normalized = normalize(dataset_ref) if callable(normalize) else dataset_ref
            dataset_id = normalized or dataset_ref
        except Exception:
            dataset_id = dataset_ref

        # If the ref is a name and normalization misses (stale index), resolve id via list endpoint.
        if dataset_id == dataset_ref:
            try:
                datasets = self._http.get_list("/api/v1/datasets", context="list_datasets_for_update_resolve")
                for ds in datasets:
                    if not isinstance(ds, dict):
                        continue
                    if ds.get("id") == dataset_ref:
                        dataset_id = dataset_ref
                        break
                    if ds.get("name") == dataset_ref and isinstance(ds.get("id"), str) and ds.get("id"):
                        dataset_id = ds.get("id")
                        break
            except Exception:
                pass

        cleaned = self._sanitize_dataset_update_body(updates)
        payload = self._http.put_json(f"/api/v1/datasets/{dataset_id}", body=cleaned, params=None)
        out = self._unwrap_dataset_payload(payload)
        if out is None and payload and isinstance(payload, dict):
            msg = self._payload_error_message(payload) or "unknown_error"
            raise RuntimeError(f"RAGFlow update dataset failed: {msg}")
        # Invalidate dataset index cache after mutation so subsequent normalize/resolve doesn't miss.
        try:
            setattr(self, "_dataset_index_cache", None)
            setattr(self, "_dataset_index_cache_at_s", 0.0)
        except Exception:
            pass
        return out

    def create_dataset(self, create_body: dict) -> dict | None:
        reload_cfg = getattr(self, "_reload_config_if_changed", None)
        if callable(reload_cfg):
            reload_cfg()

        if not isinstance(create_body, dict):
            return None

        api_key = self.config.get("api_key", "")
        if is_placeholder_api_key(api_key):
            return None

        cleaned = self._sanitize_dataset_create_body(create_body)
        payload = self._http.post_json("/api/v1/datasets", body=cleaned, params=None)
        out = self._unwrap_dataset_payload(payload)
        if out is None and payload and isinstance(payload, dict):
            msg = self._payload_error_message(payload) or "unknown_error"
            raise RuntimeError(f"RAGFlow create dataset failed: {msg}")
        # Invalidate dataset index cache after mutation so subsequent normalize/resolve doesn't miss.
        try:
            setattr(self, "_dataset_index_cache", None)
            setattr(self, "_dataset_index_cache_at_s", 0.0)
        except Exception:
            pass
        return out

    def delete_dataset_if_empty(self, dataset_ref: str) -> bool:
        reload_cfg = getattr(self, "_reload_config_if_changed", None)
        if callable(reload_cfg):
            reload_cfg()

        if not isinstance(dataset_ref, str) or not dataset_ref.strip():
            raise ValueError("invalid_dataset_ref")

        api_key = self.config.get("api_key", "")
        if is_placeholder_api_key(api_key):
            raise ValueError("ragflow_api_key_not_configured")

        dataset_id = dataset_ref
        try:
            normalize = getattr(self, "normalize_dataset_id", None)
            normalized = normalize(dataset_ref) if callable(normalize) else dataset_ref
            dataset_id = normalized or dataset_ref
        except Exception:
            dataset_id = dataset_ref

        # Use list endpoint for counts and for resolving dataset id from name.
        datasets = self._http.get_list("/api/v1/datasets", context="list_datasets_for_delete")
        target = None
        for ds in datasets:
            if not isinstance(ds, dict):
                continue
            if ds.get("id") == dataset_id or ds.get("id") == dataset_ref:
                target = ds
                dataset_id = ds.get("id") or dataset_id
                break
            if ds.get("name") == dataset_ref and isinstance(ds.get("id"), str) and ds.get("id"):
                target = ds
                dataset_id = ds.get("id")
                break
        if not target:
            raise ValueError("dataset_not_found")

        doc_count = target.get("document_count")
        chunk_count = target.get("chunk_count")
        try:
            doc_count_i = int(doc_count) if doc_count is not None else 0
        except Exception:
            doc_count_i = 0
        try:
            chunk_count_i = int(chunk_count) if chunk_count is not None else 0
        except Exception:
            chunk_count_i = 0

        if doc_count_i > 0 or chunk_count_i > 0:
            raise ValueError("dataset_not_empty")

        # RAGFlow SDK uses DELETE /datasets with a JSON body {"ids":[...]}.
        payload = self._http.delete_json("/api/v1/datasets", body={"ids": [dataset_id]}, params=None)
        if not self._payload_ok(payload):
            msg = self._payload_error_message(payload) or "unknown_error"
            raise RuntimeError(f"RAGFlow delete dataset failed: {msg}")
        # Invalidate dataset index cache after mutation so subsequent normalize/resolve doesn't miss.
        try:
            setattr(self, "_dataset_index_cache", None)
            setattr(self, "_dataset_index_cache_at_s", 0.0)
        except Exception:
            pass
        return True
