from __future__ import annotations

from typing import Optional, List

from ...ragflow_config import DEFAULT_RAGFLOW_BASE_URL


class RagflowDocumentsMixin:
    def list_documents(self, dataset_name: str = "展厅") -> List[dict]:
        if not self.client:
            return []

        try:
            dataset_name = self._normalize_dataset_name_for_ops(dataset_name)
            dataset = self._find_dataset_by_name(dataset_name)
            if not dataset:
                self.logger.warning(f"Dataset '{dataset_name}' not found")
                return []

            documents = dataset.list_documents()
            result = []

            for doc in documents:
                if hasattr(doc, "name"):
                    result.append(
                        {
                            "id": getattr(doc, "id", ""),
                            "name": doc.name,
                            "status": getattr(doc, "status", "unknown"),
                        }
                    )
                elif isinstance(doc, dict):
                    result.append(
                        {
                            "id": doc.get("id", ""),
                            "name": doc.get("name", ""),
                            "status": doc.get("status", "unknown"),
                        }
                    )

            return result
        except Exception as e:
            self.logger.error(f"Failed to list documents: {e}")
            return []

    def upload_document(self, file_path: str, kb_id: str = "展厅") -> str:
        if not self.client:
            raise ValueError("RAGFlow client not initialized")

        kb_id = self._normalize_dataset_name_for_ops(kb_id)
        dataset = self._find_dataset_by_name(kb_id)

        if not dataset:
            self.logger.info(f"Creating dataset '{kb_id}'")
            dataset = self.client.create_dataset(name=kb_id)

        document = dataset.upload_file(file_path)

        doc_id = getattr(document, "id", None)
        if not doc_id and isinstance(document, dict):
            doc_id = document.get("id")

        return doc_id

    def upload_document_blob(self, file_filename: str, file_content: bytes, kb_id: str = "展厅") -> str:
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

        payload = self._http.post_json(
            f"/api/v1/datasets/{dataset_id}/chunks",
            body={"document_ids": doc_ids},
        )
        if not payload:
            self.logger.error("parse_documents: request failed (dataset_id=%s)", dataset_id)
            return False

        code = payload.get("code")
        if code != 0:
            self.logger.error(
                "parse_documents: RAGFlow returned error code=%s message=%s dataset_id=%s",
                code,
                payload.get("message"),
                dataset_id,
            )
            return False

        return True

    def parse_document(self, *, dataset_ref: str, document_id: str) -> bool:
        return self.parse_documents(dataset_ref=dataset_ref, document_ids=[document_id])

    def delete_document(self, document_id: str, dataset_name: str = "展厅") -> bool:
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
            verify_docs = dataset.list_documents()
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
        if not self.client:
            return None

        try:
            dataset_name = self._normalize_dataset_name_for_ops(dataset_name)
            dataset = self._find_dataset_by_name(dataset_name)
            if not dataset:
                return None

            documents = dataset.list_documents()
            for doc in documents:
                doc_id = getattr(doc, "id", None) or (doc.get("id") if isinstance(doc, dict) else None)
                if doc_id == document_id:
                    return getattr(doc, "status", None) or (doc.get("status") if isinstance(doc, dict) else None)
            return None
        except Exception as e:
            self.logger.error(f"Failed to get document status: {e}")
            return None

    def get_document_detail(self, document_id: str, dataset_name: str = "展厅") -> Optional[dict]:
        if not self.client:
            return None

        try:
            dataset_name = self._normalize_dataset_name_for_ops(dataset_name)
            dataset = self._find_dataset_by_name(dataset_name)
            if not dataset:
                return None

            documents = dataset.list_documents()
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
        if not self.client:
            raise ValueError("RAGFlow client not initialized")

        try:
            dataset_name = self._normalize_dataset_name_for_ops(dataset_name)
            dataset = self._find_dataset_by_name(dataset_name)
            if not dataset:
                self.logger.warning(f"Dataset '{dataset_name}' not found")
                return None, None

            documents = dataset.list_documents()
            target_doc = None
            filename = None

            for doc in documents:
                doc_id = getattr(doc, "id", None) or (doc.get("id") if isinstance(doc, dict) else None)
                if doc_id == document_id:
                    target_doc = doc
                    filename = getattr(doc, "name", None) or (doc.get("name") if isinstance(doc, dict) else None)
                    break

            if not target_doc:
                self.logger.warning(f"Document {document_id} not found in dataset '{dataset_name}'")
                return None, None

            self.logger.info(f"Downloading document '{filename}' ({document_id}) from RAGFlow")
            file_content = target_doc.download()

            if file_content:
                self.logger.info(f"Successfully downloaded {len(file_content)} bytes")
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

