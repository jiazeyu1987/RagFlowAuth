from __future__ import annotations

import inspect
from time import time
from typing import Any, List

from ...ragflow_config import is_placeholder_api_key


class RagflowDatasetsMixin:
    _DATASET_LIST_PAGE_SIZE: int = 200
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

    def _coerce_dataset_item(self, dataset: Any) -> dict | None:
        if hasattr(dataset, "name"):
            item = {
                "id": getattr(dataset, "id", ""),
                "name": getattr(dataset, "name", ""),
                "document_count": getattr(dataset, "document_count", None),
                "chunk_count": getattr(dataset, "chunk_count", None),
                "description": getattr(dataset, "description", None),
            }
            chunk_method = getattr(dataset, "chunk_method", None)
            embedding_model = getattr(dataset, "embedding_model", None)
            avatar = getattr(dataset, "avatar", None)
            if chunk_method is not None:
                item["chunk_method"] = chunk_method
            if embedding_model is not None:
                item["embedding_model"] = embedding_model
            if avatar is not None:
                item["avatar"] = avatar
            return item
        if isinstance(dataset, dict):
            return dict(dataset)
        return None

    def _extract_dataset_batch_from_payload(self, payload: dict | None, *, context: str) -> list[dict]:
        if not isinstance(payload, dict):
            return []
        if payload.get("code") not in (0, None):
            logger = getattr(self, "logger", None)
            if logger is not None and hasattr(logger, "error"):
                logger.error("RAGFlow %s failed: %s", context, payload.get("message"))
            return []

        data = payload.get("data")
        candidates: list[Any] = []
        if isinstance(data, list):
            candidates = data
        elif isinstance(data, dict):
            for key in ("datasets", "items", "list", "rows"):
                value = data.get(key)
                if isinstance(value, list):
                    candidates = value
                    break

        result: list[dict] = []
        for item in candidates:
            row = self._coerce_dataset_item(item)
            if row is not None:
                result.append(row)
        return result

    def _list_dataset_page_via_http(self, *, page: int, page_size: int, context: str) -> list[dict]:
        get_json = getattr(self._http, "get_json", None)
        if callable(get_json):
            payload = get_json("/api/v1/datasets", params={"page": page, "page_size": page_size})
            return self._extract_dataset_batch_from_payload(payload, context=context)

        get_list = getattr(self._http, "get_list", None)
        if callable(get_list):
            batch = get_list(
                "/api/v1/datasets",
                params={"page": page, "page_size": page_size},
                context=context,
            )
            result: list[dict] = []
            for item in batch:
                row = self._coerce_dataset_item(item)
                if row is not None:
                    result.append(row)
            return result
        return []

    def _list_datasets_via_http(self, *, page_size: int) -> list[dict]:
        datasets: list[dict] = []
        seen_ids: set[str] = set()
        page = 1
        while True:
            batch = self._list_dataset_page_via_http(page=page, page_size=page_size, context="list_datasets")
            if not batch:
                break
            new_items = 0
            for item in batch:
                dataset_id = str(item.get("id") or "").strip()
                if dataset_id:
                    if dataset_id in seen_ids:
                        continue
                    seen_ids.add(dataset_id)
                new_items += 1
                datasets.append(item)
            if len(batch) < page_size or new_items == 0:
                break
            page += 1
        return datasets

    def _list_datasets_via_sdk(self, *, page_size: int) -> list[dict]:
        list_datasets = getattr(self.client, "list_datasets", None)
        if not callable(list_datasets):
            return []

        supports_page = True
        try:
            sig = inspect.signature(list_datasets)
            supports_page = "page" in sig.parameters and "page_size" in sig.parameters
        except Exception:
            supports_page = True

        datasets: list[dict] = []
        seen_ids: set[str] = set()
        if not supports_page:
            batch = list_datasets()
            if not isinstance(batch, list):
                return []
            for item in batch:
                row = self._coerce_dataset_item(item)
                if row is None:
                    continue
                dataset_id = str(row.get("id") or "").strip()
                if dataset_id:
                    if dataset_id in seen_ids:
                        continue
                    seen_ids.add(dataset_id)
                datasets.append(row)
            return datasets

        page = 1
        while True:
            batch = list_datasets(page=page, page_size=page_size)
            if not isinstance(batch, list) or not batch:
                break
            new_items = 0
            for item in batch:
                row = self._coerce_dataset_item(item)
                if row is None:
                    continue
                dataset_id = str(row.get("id") or "").strip()
                if dataset_id:
                    if dataset_id in seen_ids:
                        continue
                    seen_ids.add(dataset_id)
                new_items += 1
                datasets.append(row)
            if len(batch) < page_size or new_items == 0:
                break
            page += 1
        return datasets

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
        page_size = int(getattr(self, "_DATASET_LIST_PAGE_SIZE", 200) or 200)
        if not self.client:
            if is_placeholder_api_key(api_key):
                return []
            return self._list_datasets_via_http(page_size=page_size)

        try:
            return self._list_datasets_via_sdk(page_size=page_size)
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
        datasets = self.list_datasets() or []
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
                datasets = self.list_datasets() or []
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
        datasets = self.list_datasets() or []
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
