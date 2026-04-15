from __future__ import annotations

import inspect
import json
import time
from pathlib import Path
from typing import Optional, List

import requests

from ...ragflow_config import DEFAULT_RAGFLOW_BASE_URL
from backend.app.core.request_id import get_request_id


class RagflowDocumentsMixin:
    _PARSE_DOCUMENT_READY_TIMEOUT_S: float = 30.0
    _PARSE_DOCUMENT_READY_POLL_INTERVAL_S: float = 1.0

    def _dataset_id_from_obj(self, dataset) -> str | None:
        dataset_id = getattr(dataset, "id", None)
        if not dataset_id and isinstance(dataset, dict):
            dataset_id = dataset.get("id")
        return dataset_id if isinstance(dataset_id, str) and dataset_id else None

    def _coerce_document_item(self, doc) -> dict | None:
        if hasattr(doc, "name"):
            item = {
                "id": getattr(doc, "id", ""),
                "name": doc.name,
                "status": getattr(doc, "status", "unknown"),
            }
            chunk_count = getattr(doc, "chunk_count", None)
            progress = getattr(doc, "progress", None)
            run = getattr(doc, "run", None)
            if chunk_count is not None:
                item["chunk_count"] = chunk_count
            if progress is not None:
                item["progress"] = progress
            if run is not None:
                item["run"] = run
            return item
        if isinstance(doc, dict):
            item = {
                "id": doc.get("id", ""),
                "name": doc.get("name", ""),
                "status": doc.get("status", "unknown"),
            }
            if doc.get("chunk_count") is not None:
                item["chunk_count"] = doc.get("chunk_count")
            if doc.get("progress") is not None:
                item["progress"] = doc.get("progress")
            if doc.get("run") is not None:
                item["run"] = doc.get("run")
            return item
        return None

    def _document_is_parse_ready(self, doc) -> bool:
        if doc is None:
            return False
        raw_chunk_count = getattr(doc, "chunk_count", None) if hasattr(doc, "chunk_count") else None
        if raw_chunk_count is None and isinstance(doc, dict):
            raw_chunk_count = doc.get("chunk_count")
        try:
            if int(raw_chunk_count or 0) > 0:
                return True
        except Exception:
            pass

        raw_progress = getattr(doc, "progress", None) if hasattr(doc, "progress") else None
        if raw_progress is None and isinstance(doc, dict):
            raw_progress = doc.get("progress")
        try:
            if float(raw_progress or 0.0) >= 1.0:
                return True
        except Exception:
            pass

        raw_run = getattr(doc, "run", None) if hasattr(doc, "run") else None
        if raw_run is None and isinstance(doc, dict):
            raw_run = doc.get("run")
        run = str(raw_run or "").strip().upper()
        return run in {"DONE", "FAIL", "CANCEL"}

    def _get_sdk_document_by_id(self, dataset, document_id: str):
        list_documents = getattr(dataset, "list_documents", None)
        if not callable(list_documents):
            return None
        try:
            docs = list_documents(id=document_id, page=1, page_size=1)
        except Exception:
            return None
        if not isinstance(docs, list) or not docs:
            return None
        return docs[0]

    def _parse_documents_via_sdk(
        self,
        dataset,
        *,
        document_ids: list[str],
        timeout_s: float,
        poll_interval_s: float,
    ) -> bool:
        deadline = time.time() + max(timeout_s, 0.0)
        parse_requested = False
        dataset_id = self._dataset_id_from_obj(dataset) or ""
        while True:
            visible_count = 0
            ready_count = 0
            for document_id in document_ids:
                doc = self._get_sdk_document_by_id(dataset, document_id)
                if doc is None:
                    continue
                visible_count += 1
                if self._document_is_parse_ready(doc):
                    ready_count += 1

            if ready_count == len(document_ids):
                return True

            if visible_count == len(document_ids) and not parse_requested:
                async_parse = getattr(dataset, "async_parse_documents", None)
                if callable(async_parse):
                    try:
                        async_parse(document_ids)
                    except Exception as exc:
                        if time.time() >= deadline:
                            self.logger.error(
                                "parse_documents: sdk async_parse_documents failed dataset_id=%s error=%s",
                                dataset_id,
                                exc,
                            )
                            return False
                    else:
                        parse_requested = True

            if time.time() >= deadline:
                self.logger.error(
                    "parse_documents: sdk documents not ready dataset_id=%s document_ids=%s",
                    dataset_id,
                    document_ids,
                )
                return False

            time.sleep(max(poll_interval_s, 0.0))

    def _extract_document_batch_from_payload(self, payload: dict | None) -> list[dict]:
        if not isinstance(payload, dict):
            return []
        if payload.get("code") not in (0, None):
            self.logger.error("RAGFlow list_documents failed: %s", payload.get("message"))
            return []

        data = payload.get("data")
        candidates = []
        if isinstance(data, list):
            candidates = data
        elif isinstance(data, dict):
            for key in ("docs", "documents", "items", "list"):
                value = data.get(key)
                if isinstance(value, list):
                    candidates = value
                    break

        result: list[dict] = []
        for item in candidates:
            row = self._coerce_document_item(item)
            if row is not None:
                result.append(row)
        return result

    def _list_documents_via_http(self, dataset_id: str, *, page_size: int) -> list[dict]:
        documents: list[dict] = []
        page = 1
        while True:
            payload = self._http.get_json(
                f"/api/v1/datasets/{dataset_id}/documents",
                params={"page": page, "page_size": page_size},
            )
            batch = self._extract_document_batch_from_payload(payload)
            if not batch:
                break
            documents.extend(batch)
            if len(batch) < page_size:
                break
            page += 1
        return documents

    def _list_documents_via_sdk(self, dataset, *, page_size: int) -> list[dict]:
        list_documents = getattr(dataset, "list_documents", None)
        if not callable(list_documents):
            return []

        supports_page = True
        try:
            sig = inspect.signature(list_documents)
            supports_page = "page" in sig.parameters and "page_size" in sig.parameters
        except Exception:
            supports_page = True

        if not supports_page:
            raise TypeError("DataSet.list_documents() missing page/page_size parameters")

        documents: list[dict] = []
        page = 1
        while True:
            batch = list_documents(page=page, page_size=page_size)
            if not isinstance(batch, list) or not batch:
                break
            for item in batch:
                row = self._coerce_document_item(item)
                if row is not None:
                    documents.append(row)
            if len(batch) < page_size:
                break
            page += 1
        return documents

    def _find_document_metadata_via_http(self, dataset_id: str, document_id: str) -> dict | None:
        t0 = time.perf_counter()
        request_id = get_request_id() or "-"
        payload = self._http.get_json(
            f"/api/v1/datasets/{dataset_id}/documents",
            params={"id": document_id, "page": 1, "page_size": 1},
        )
        batch = self._extract_document_batch_from_payload(payload)
        self.logger.info(
            "ragflow_meta_lookup_done request_id=%s dataset_id=%s document_id=%s found=%s elapsed_ms=%.2f",
            request_id,
            dataset_id,
            document_id,
            bool(batch),
            (time.perf_counter() - t0) * 1000,
        )
        return batch[0] if batch else None

    def _wait_for_document_visible_via_http(
        self,
        dataset_id: str,
        document_id: str,
        *,
        timeout_s: float | None = None,
        poll_interval_s: float | None = None,
    ) -> bool:
        timeout = float(
            timeout_s
            if timeout_s is not None
            else getattr(self, "_PARSE_DOCUMENT_READY_TIMEOUT_S", 30.0)
        )
        poll_interval = float(
            poll_interval_s
            if poll_interval_s is not None
            else getattr(self, "_PARSE_DOCUMENT_READY_POLL_INTERVAL_S", 1.0)
        )
        deadline = time.time() + max(timeout, 0.0)
        while True:
            documents = self._list_documents_via_http(dataset_id, page_size=200)
            if any(str(item.get("id") or "").strip() == document_id for item in documents if isinstance(item, dict)):
                return True
            if time.time() >= deadline:
                return False
            time.sleep(max(poll_interval, 0.0))

    def _download_document_via_http(self, dataset_id: str, document_id: str) -> bytes | None:
        t0 = time.perf_counter()
        request_id = get_request_id() or "-"
        url = f"{self._http.config.base_url.rstrip('/')}/api/v1/datasets/{dataset_id}/documents/{document_id}"
        try:
            resp = requests.get(url, headers=self._http.headers(), timeout=float(self.config.get("timeout", 10) or 10))
        except Exception as exc:
            self.logger.error("RAGFlow download document failed: %s", exc)
            return None

        if resp.status_code != 200:
            self.logger.error(
                "RAGFlow download document failed: HTTP %s request_id=%s dataset_id=%s document_id=%s elapsed_ms=%.2f",
                resp.status_code,
                request_id,
                dataset_id,
                document_id,
                (time.perf_counter() - t0) * 1000,
            )
            return None

        try:
            payload = resp.json()
        except json.JSONDecodeError:
            self.logger.info(
                "ragflow_file_download_done request_id=%s dataset_id=%s document_id=%s size_bytes=%s elapsed_ms=%.2f",
                request_id,
                dataset_id,
                document_id,
                len(resp.content or b""),
                (time.perf_counter() - t0) * 1000,
            )
            return resp.content
        except Exception:
            self.logger.info(
                "ragflow_file_download_done request_id=%s dataset_id=%s document_id=%s size_bytes=%s elapsed_ms=%.2f",
                request_id,
                dataset_id,
                document_id,
                len(resp.content or b""),
                (time.perf_counter() - t0) * 1000,
            )
            return resp.content

        if isinstance(payload, dict) and set(payload.keys()) == {"code", "message"}:
            self.logger.error("RAGFlow download document failed: %s", payload.get("message"))
            return None
        self.logger.info(
            "ragflow_file_download_done request_id=%s dataset_id=%s document_id=%s size_bytes=%s elapsed_ms=%.2f",
            request_id,
            dataset_id,
            document_id,
            len(resp.content or b""),
            (time.perf_counter() - t0) * 1000,
        )
        return resp.content

    def list_documents(self, dataset_name: str = "展厅") -> List[dict]:
        reload_cfg = getattr(self, "_reload_config_if_changed", None)
        if callable(reload_cfg):
            reload_cfg()

        if not self.client:
            return []

        try:
            dataset_name = self._normalize_dataset_name_for_ops(dataset_name)
            dataset = self._find_dataset_by_name(dataset_name)
            if not dataset:
                self.logger.warning(f"Dataset '{dataset_name}' not found")
                return []

            page_size = 200
            try:
                return self._list_documents_via_sdk(dataset, page_size=page_size)
            except TypeError as exc:
                if "page" not in str(exc) and "page_size" not in str(exc):
                    raise
                dataset_id = self._dataset_id_from_obj(dataset)
                if not dataset_id:
                    self.logger.error("Failed to list documents via HTTP: missing dataset_id for '%s'", dataset_name)
                    return []
                self.logger.warning(
                    "SDK list_documents does not support pagination args; falling back to HTTP API for dataset '%s'",
                    dataset_name,
                )
                return self._list_documents_via_http(dataset_id, page_size=page_size)
        except Exception as e:
            self.logger.error(f"Failed to list documents: {e}")
            return []

    def upload_document(self, file_path: str, kb_id: str = "展厅") -> str:
        reload_cfg = getattr(self, "_reload_config_if_changed", None)
        if callable(reload_cfg):
            reload_cfg()

        if not self.client:
            raise ValueError("RAGFlow client not initialized")

        path = Path(file_path).resolve()
        if not path.exists() or not path.is_file():
            raise FileNotFoundError(f"document_file_not_found:{path}")

        return self.upload_document_blob(
            file_filename=path.name,
            file_content=path.read_bytes(),
            kb_id=kb_id,
        )

    def upload_document_blob(self, file_filename: str, file_content: bytes, kb_id: str = "展厅") -> str:
        reload_cfg = getattr(self, "_reload_config_if_changed", None)
        if callable(reload_cfg):
            reload_cfg()

        """
        Upload document to RAGFlow using official HTTP API
        Reference: https://ragflow.io/docs/http_api

        HTTP API: POST /api/v1/datasets/{dataset_id}/documents
        Form: file=@{FILE_PATH}
        """
        import requests
        import io

        if not self.client:
            raise ValueError("RAGFlow client not initialized")

        kb_id = self._normalize_dataset_name_for_ops(kb_id)
        dataset = self._find_dataset_by_name(kb_id)

        if not dataset:
            self.logger.info(f"Creating dataset '{kb_id}'")
            dataset = self.client.create_dataset(name=kb_id)

        try:
            dataset_id = getattr(dataset, "id", None)
            if not dataset_id and isinstance(dataset, dict):
                dataset_id = dataset.get("id")

            if not dataset_id:
                self.logger.error(f"Cannot find dataset ID for '{kb_id}'")
                return None

            base_url = self.config.get("base_url", DEFAULT_RAGFLOW_BASE_URL)
            api_key = self.config.get("api_key", "")

            upload_url = f"{base_url}/api/v1/datasets/{dataset_id}/documents"

            files = {"file": (file_filename, io.BytesIO(file_content))}
            headers = {"Authorization": f"Bearer {api_key}"}

            self.logger.info(
                f"Uploading {file_filename} ({len(file_content)} bytes) to dataset '{kb_id}' (id={dataset_id})"
            )
            self.logger.info(f"POST {upload_url}")

            response = requests.post(upload_url, files=files, headers=headers, timeout=60)

            if response.status_code in [200, 201]:
                self.logger.info(f"Successfully uploaded {file_filename}")
                try:
                    result = response.json()
                    self.logger.info(f"RAGFlow response: {str(result)[:200]}...")

                    if isinstance(result, dict):
                        if "code" in result and result["code"] == 0:
                            if "data" in result and isinstance(result["data"], list):
                                docs = result["data"]
                                if docs and len(docs) > 0:
                                    doc_id = docs[0].get("id")
                                    self.logger.info(f"Document ID: {doc_id}")
                                    return doc_id
                        elif "data" in result and isinstance(result["data"], list):
                            doc_ids = result["data"]
                            if doc_ids and len(doc_ids) > 0:
                                doc_id = doc_ids[0].get("id") if isinstance(doc_ids[0], dict) else doc_ids[0]
                                self.logger.info(f"Document ID: {doc_id}")
                                return doc_id
                        elif "id" in result:
                            return result["id"]

                    self.logger.warning("Could not extract document ID from response")
                    return "uploaded"
                except Exception as e:
                    self.logger.warning(f"Could not parse response JSON: {e}")
                    return "uploaded"
            else:
                self.logger.error(f"Upload failed with status {response.status_code}: {response.text}")
                return None

        except Exception as e:
            self.logger.error(f"Failed to upload document: {e}")
            import traceback

            self.logger.error(traceback.format_exc())
            return None

    def _looks_like_uuid(self, value: str) -> bool:
        if not isinstance(value, str):
            return False
        v = value.strip()
        if len(v) < 32 or len(v) > 64:
            return False
        import re

        return bool(re.fullmatch(r"[0-9a-fA-F-]{32,64}", v))

    def _normalize_dataset_id_for_http(self, dataset_ref: str) -> str | None:
        dataset_ref = (dataset_ref or "").strip()
        if not dataset_ref:
            return None

        try:
            dataset_id = self.normalize_dataset_id(dataset_ref)
        except Exception:
            dataset_id = None

        if dataset_id:
            return dataset_id

        if self._looks_like_uuid(dataset_ref):
            return dataset_ref

        return None

    def parse_documents(self, *, dataset_ref: str, document_ids: list[str]) -> bool:
        reload_cfg = getattr(self, "_reload_config_if_changed", None)
        if callable(reload_cfg):
            reload_cfg()

        dataset_id = self._normalize_dataset_id_for_http(dataset_ref)
        if not dataset_id:
            self.logger.warning("parse_documents: cannot resolve dataset_id for dataset_ref=%r", dataset_ref)
            return False

        doc_ids: list[str] = []
        seen: set[str] = set()
        for doc_id in document_ids or []:
            if not isinstance(doc_id, str):
                continue
            doc_id = doc_id.strip()
            if not doc_id or doc_id in seen:
                continue
            seen.add(doc_id)
            doc_ids.append(doc_id)

        if not doc_ids:
            self.logger.warning("parse_documents: empty document_ids (dataset_ref=%r)", dataset_ref)
            return False

        raw_timeout_s = getattr(self, "_PARSE_DOCUMENT_READY_TIMEOUT_S", 30.0)
        raw_poll_interval_s = getattr(self, "_PARSE_DOCUMENT_READY_POLL_INTERVAL_S", 1.0)
        timeout_s = 30.0 if raw_timeout_s is None else float(raw_timeout_s)
        poll_interval_s = 1.0 if raw_poll_interval_s is None else float(raw_poll_interval_s)

        # Uploads already go through the HTTP dataset endpoint and return document ids from that
        # surface. Prefer parsing through the same HTTP API when we can resolve a dataset id, so
        # newly uploaded documents do not depend on slower SDK visibility propagation.
        if dataset_id:
            for doc_id in doc_ids:
                visible = self._wait_for_document_visible_via_http(
                    dataset_id,
                    doc_id,
                    timeout_s=timeout_s,
                    poll_interval_s=poll_interval_s,
                )
                if not visible:
                    self.logger.error(
                        "parse_documents: document_not_visible dataset_id=%s document_id=%s",
                        dataset_id,
                        doc_id,
                    )
                    return False

            deadline = time.time() + max(timeout_s, 0.0)
            while True:
                payload = self._http.post_json(
                    f"/api/v1/datasets/{dataset_id}/chunks",
                    body={"document_ids": doc_ids},
                )
                if not payload:
                    self.logger.error("parse_documents: request failed (dataset_id=%s)", dataset_id)
                    return False

                code = payload.get("code")
                if code == 0:
                    return True
                if code == 102 and time.time() < deadline:
                    time.sleep(max(poll_interval_s, 0.0))
                    continue

                self.logger.error(
                    "parse_documents: RAGFlow returned error code=%s message=%s dataset_id=%s",
                    code,
                    payload.get("message"),
                    dataset_id,
                )
                return False

        if self.client:
            dataset_name = self._normalize_dataset_name_for_ops(dataset_ref)
            dataset = self._find_dataset_by_name(dataset_name)
            if not dataset:
                self.logger.error("parse_documents: dataset_not_found dataset_ref=%s", dataset_ref)
                return False
            return self._parse_documents_via_sdk(
                dataset,
                document_ids=doc_ids,
                timeout_s=timeout_s,
                poll_interval_s=poll_interval_s,
            )
        self.logger.warning("parse_documents: no available parse path dataset_ref=%r", dataset_ref)
        return False

    def parse_document(self, *, dataset_ref: str, document_id: str) -> bool:
        reload_cfg = getattr(self, "_reload_config_if_changed", None)
        if callable(reload_cfg):
            reload_cfg()

        return self.parse_documents(dataset_ref=dataset_ref, document_ids=[document_id])

    def delete_document(self, document_id: str, dataset_name: str = "展厅") -> bool:
        reload_cfg = getattr(self, "_reload_config_if_changed", None)
        if callable(reload_cfg):
            reload_cfg()

        if not self.client:
            self.logger.error("RAGFlow client not initialized")
            return False

        try:
            self.logger.info(f"Attempting to delete document {document_id} from dataset '{dataset_name}'")

            dataset_name = self._normalize_dataset_name_for_ops(dataset_name)
            dataset = self._find_dataset_by_name(dataset_name)
            if not dataset:
                self.logger.error(f"Dataset '{dataset_name}' not found")
                return False

            self.logger.info(f"Found dataset '{dataset_name}', using delete_documents() method")

            result = dataset.delete_documents(ids=[document_id])

            self.logger.info(f"delete_documents returned: {result}")

            self.logger.info("Verifying deletion...")
            verify_docs = self.list_documents(dataset_name)
            still_exists = any(
                (getattr(d, "id", None) or (d.get("id") if isinstance(d, dict) else None)) == document_id
                for d in verify_docs
            )

            if still_exists:
                self.logger.error(f"Document {document_id} still exists after deletion attempt")
                return False
            else:
                self.logger.info(f"✓ Successfully deleted document {document_id}")
                return True

        except Exception as e:
            self.logger.error(f"Failed to delete document {document_id}: {e}")
            import traceback

            self.logger.error(traceback.format_exc())
            return False

    def get_document_status(self, document_id: str, dataset_name: str = "展厅") -> Optional[str]:
        reload_cfg = getattr(self, "_reload_config_if_changed", None)
        if callable(reload_cfg):
            reload_cfg()

        if not self.client:
            return None

        try:
            dataset_name = self._normalize_dataset_name_for_ops(dataset_name)
            documents = self.list_documents(dataset_name)
            for doc in documents:
                doc_id = getattr(doc, "id", None) or (doc.get("id") if isinstance(doc, dict) else None)
                if doc_id == document_id:
                    return getattr(doc, "status", None) or (doc.get("status") if isinstance(doc, dict) else None)
            return None
        except Exception as e:
            self.logger.error(f"Failed to get document status: {e}")
            return None

    def get_document_detail(self, document_id: str, dataset_name: str = "展厅") -> Optional[dict]:
        reload_cfg = getattr(self, "_reload_config_if_changed", None)
        if callable(reload_cfg):
            reload_cfg()

        if not self.client:
            return None

        try:
            dataset_name = self._normalize_dataset_name_for_ops(dataset_name)
            documents = self.list_documents(dataset_name)
            for doc in documents:
                doc_id = getattr(doc, "id", None) or (doc.get("id") if isinstance(doc, dict) else None)
                if doc_id == document_id:
                    detail = {
                        "id": document_id,
                        "name": getattr(doc, "name", None) or (doc.get("name") if isinstance(doc, dict) else None),
                        "status": getattr(doc, "status", None) or (doc.get("status") if isinstance(doc, dict) else None),
                        "dataset": dataset_name,
                    }

                    for attr in ["chunk_method", "parser_id", "size", "created_at"]:
                        value = getattr(doc, attr, None) or (doc.get(attr) if isinstance(doc, dict) else None)
                        if value:
                            detail[attr] = value

                    return detail
            return None
        except Exception as e:
            self.logger.error(f"Failed to get document detail: {e}")
            return None

    def download_document(self, document_id: str, dataset_name: str = "展厅"):
        reload_cfg = getattr(self, "_reload_config_if_changed", None)
        if callable(reload_cfg):
            reload_cfg()

        if not self.client:
            raise ValueError("RAGFlow client not initialized")

        t0 = time.perf_counter()
        request_id = get_request_id() or "-"
        try:
            dataset_name = self._normalize_dataset_name_for_ops(dataset_name)
            dataset = self._find_dataset_by_name(dataset_name)
            if not dataset:
                self.logger.warning(f"Dataset '{dataset_name}' not found")
                return None, None

            dataset_id = self._dataset_id_from_obj(dataset)
            if not dataset_id:
                self.logger.error(f"Dataset '{dataset_name}' missing id")
                return None, None

            doc_meta = self._find_document_metadata_via_http(dataset_id, document_id)
            if not doc_meta:
                self.logger.warning(f"Document {document_id} not found in dataset '{dataset_name}'")
                return None, None

            filename = doc_meta.get("name") or f"document_{document_id}"
            self.logger.info(f"Downloading document '{filename}' ({document_id}) from RAGFlow")
            file_content = self._download_document_via_http(dataset_id, document_id)

            if file_content:
                self.logger.info(f"Successfully downloaded {len(file_content)} bytes")
                self.logger.info(
                    "ragflow_download_document_done request_id=%s dataset=%s dataset_id=%s document_id=%s size_bytes=%s elapsed_ms=%.2f",
                    request_id,
                    dataset_name,
                    dataset_id,
                    document_id,
                    len(file_content),
                    (time.perf_counter() - t0) * 1000,
                )
                return file_content, filename
            else:
                self.logger.error(f"Download returned empty content for document {document_id}")
                return None, None

        except Exception as e:
            self.logger.error(f"Failed to download document: {e}")
            import traceback

            self.logger.error(traceback.format_exc())
            return None, None

    def batch_download_documents(self, documents_info: list) -> tuple:
        reload_cfg = getattr(self, "_reload_config_if_changed", None)
        if callable(reload_cfg):
            reload_cfg()

        import io
        import zipfile
        import time

        if not self.client:
            raise ValueError("RAGFlow client not initialized")

        zip_buffer = io.BytesIO()
        timestamp = int(time.time())
        zip_filename = f"documents_{timestamp}.zip"

        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for doc_info in documents_info:
                doc_id = doc_info.get("doc_id")
                dataset_name = doc_info.get("dataset_name")
                name = doc_info.get("name")

                if not doc_id or not dataset_name:
                    continue

                file_content, filename = self.download_document(doc_id, dataset_name)

                if file_content:
                    zip_name = name or filename or f"{doc_id}.bin"
                    zip_file.writestr(zip_name, file_content)
                else:
                    self.logger.warning(f"Skipping document {doc_id} - could not download")

        zip_buffer.seek(0)
        return zip_buffer.getvalue(), zip_filename
