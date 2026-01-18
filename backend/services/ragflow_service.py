import logging
from time import time
from typing import Optional, List

from .ragflow_config import (
    DEFAULT_RAGFLOW_BASE_URL,
    is_placeholder_api_key,
)
from .ragflow_connection import RagflowConnection, create_ragflow_connection


class RagflowService:
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
                    result.append({
                        "id": getattr(dataset, "id", ""),
                        "name": dataset.name
                    })
                elif isinstance(dataset, dict):
                    result.append({
                        "id": dataset.get("id", ""),
                        "name": dataset.get("name", "")
                    })
            return result
        except Exception as e:
            self.logger.error(f"Failed to list datasets: {e}")
            return []

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
                    result.append({
                        "id": getattr(doc, "id", ""),
                        "name": doc.name,
                        "status": getattr(doc, "status", "unknown")
                    })
                elif isinstance(doc, dict):
                    result.append({
                        "id": doc.get("id", ""),
                        "name": doc.get("name", ""),
                        "status": doc.get("status", "unknown")
                    })

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

        Args:
            file_filename: Display name of the file
            file_content: Binary content of the file
            kb_id: Dataset name (knowledge base ID)

        Returns:
            Document ID if successful, None otherwise
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
            # Get dataset ID
            dataset_id = getattr(dataset, "id", None)
            if not dataset_id and isinstance(dataset, dict):
                dataset_id = dataset.get("id")

            if not dataset_id:
                self.logger.error(f"Cannot find dataset ID for '{kb_id}'")
                return None

            # Use HTTP API to upload document
            # POST /api/v1/datasets/{dataset_id}/documents
            # Content-Type: multipart/form-data
            # Form: file=@{FILE_PATH}

            base_url = self.config.get("base_url", DEFAULT_RAGFLOW_BASE_URL)
            api_key = self.config.get("api_key", "")

            upload_url = f"{base_url}/api/v1/datasets/{dataset_id}/documents"

            # Prepare multipart form data
            files = {
                'file': (file_filename, io.BytesIO(file_content))
            }

            headers = {
                'Authorization': f'Bearer {api_key}'
            }

            self.logger.info(f"Uploading {file_filename} ({len(file_content)} bytes) to dataset '{kb_id}' (id={dataset_id})")
            self.logger.info(f"POST {upload_url}")

            response = requests.post(upload_url, files=files, headers=headers, timeout=60)

            if response.status_code in [200, 201]:
                self.logger.info(f"Successfully uploaded {file_filename}")
                # Try to extract document ID from response
                try:
                    result = response.json()
                    self.logger.info(f"RAGFlow response: {str(result)[:200]}...")

                    # Response format: {"code": 0, "data": [{"id": "...", ...}]}
                    if isinstance(result, dict):
                        if 'code' in result and result['code'] == 0:
                            # Success response with data array
                            if 'data' in result and isinstance(result['data'], list):
                                docs = result['data']
                                if docs and len(docs) > 0:
                                    doc_id = docs[0].get('id')
                                    self.logger.info(f"Document ID: {doc_id}")
                                    return doc_id
                        # Alternative format check
                        elif 'data' in result and isinstance(result['data'], list):
                            doc_ids = result['data']
                            if doc_ids and len(doc_ids) > 0:
                                doc_id = doc_ids[0].get('id') if isinstance(doc_ids[0], dict) else doc_ids[0]
                                self.logger.info(f"Document ID: {doc_id}")
                                return doc_id
                        elif 'id' in result:
                            return result['id']

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

    def delete_document(self, document_id: str, dataset_name: str = "展厅") -> bool:
        """
        从RAGFlow知识库中删除文档
        使用 dataset.delete_documents(ids=[doc_id]) 方法
        返回: 成功返回True，失败返回False
        """
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

            # 使用RAGFlow SDK的 delete_documents 方法（复数形式）
            # 即使删除单个文档也需要传递列表
            result = dataset.delete_documents(ids=[document_id])

            self.logger.info(f"delete_documents returned: {result}")

            # 验证删除是否成功
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

                    # Try to get additional attributes
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
        """
        下载RAGFlow文档的字节内容
        使用Document.download()方法获取文件内容
        返回: (bytes, filename) 或 (None, None)
        """
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

            # 使用RAGFlow SDK的download()方法下载文件
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
        """
        批量下载文档并打包为zip
        documents_info: [{"doc_id": str, "dataset_name": str, "name": str}, ...]
        返回: (zip_bytes, filename) 或 (None, None)
        """
        import zipfile
        import io
        from datetime import datetime

        if not self.client:
            raise ValueError("RAGFlow client not initialized")

        try:
            self.logger.info(f"Starting batch download for {len(documents_info)} documents")
            self.logger.info(f"Documents info: {documents_info}")

            zip_buffer = io.BytesIO()
            files_added = 0

            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                for idx, doc_info in enumerate(documents_info):
                    doc_id = doc_info.get("doc_id")
                    dataset_name = doc_info.get("dataset_name", "展厅")
                    preferred_name = doc_info.get("name")

                    self.logger.info(f"Processing document {idx + 1}/{len(documents_info)}: {doc_id} from {dataset_name}")

                    try:
                        file_content, ragflow_filename = self.download_document(doc_id, dataset_name)

                        if file_content:
                            filename = preferred_name or ragflow_filename or f"document_{doc_id}"
                            zip_file.writestr(filename, file_content)
                            files_added += 1
                            self.logger.info(f"✓ Added to zip: {filename} ({len(file_content)} bytes)")
                        else:
                            self.logger.warning(f"✗ Failed to download document {doc_id} - no content returned")

                    except Exception as e:
                        self.logger.error(f"✗ Error downloading document {doc_id}: {e}")
                        import traceback
                        self.logger.error(traceback.format_exc())
                        continue

            zip_buffer.seek(0)
            zip_content = zip_buffer.getvalue()

            self.logger.info(f"Zip creation complete: {files_added} files added, {len(zip_content)} bytes total")

            if zip_content and files_added > 0:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"documents_batch_{timestamp}.zip"
                self.logger.info(f"✓ Successfully created zip file: {filename} ({len(zip_content)} bytes)")
                return zip_content, filename
            else:
                self.logger.error("✗ Zip file is empty or no files were added")
                return None, None

        except Exception as e:
            self.logger.error(f"Failed to create batch download: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return None, None
