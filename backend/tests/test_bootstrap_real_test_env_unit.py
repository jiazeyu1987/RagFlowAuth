from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from scripts.bootstrap_real_test_env import (
    DEFAULT_E2E_CHAT_NAME,
    DEFAULT_E2E_DATASET_NAME,
    _ensure_dataset_seed_content,
    _is_managed_bootstrap_resource_name,
    _materialize_bootstrap_resource_name,
    _resolve_chat_name,
    _resolve_dataset_name,
    _unbind_previous_managed_dataset_bindings,
)


class _BootstrapRagflowService:
    def __init__(self, documents, *, upload_doc_id: str = "seed-uploaded", delete_fail_ids: set[str] | None = None):
        self.documents = [dict(item) for item in documents]
        self.upload_doc_id = upload_doc_id
        self.delete_fail_ids = set(delete_fail_ids or set())
        self.deleted: list[tuple[str, str]] = []
        self.upload_calls: list[tuple[str, str]] = []
        self.parse_calls: list[tuple[str, str]] = []

    def list_documents(self, dataset_id):
        return [dict(item) for item in self.documents]

    def delete_document(self, document_id, dataset_name=""):
        self.deleted.append((str(document_id), str(dataset_name)))
        if str(document_id) in self.delete_fail_ids:
            return False
        self.documents = [item for item in self.documents if str(item.get("id")) != str(document_id)]
        return True

    def upload_document(self, file_path, kb_id=""):
        self.upload_calls.append((str(file_path), str(kb_id)))
        self.documents.append(
            {
                "id": self.upload_doc_id,
                "name": Path(file_path).name,
                "status": "uploaded",
            }
        )
        return self.upload_doc_id

    def parse_document(self, *, dataset_ref, document_id):
        self.parse_calls.append((str(dataset_ref), str(document_id)))
        return True


class _BootstrapKnowledgeDirectoryStore:
    def __init__(self) -> None:
        self.assign_calls: list[tuple[str, None]] = []

    def assign_dataset(self, dataset_id, node_id):
        self.assign_calls.append((str(dataset_id), node_id))


class TestBootstrapRealTestEnvUnit(unittest.TestCase):
    def setUp(self) -> None:
        self.tenant_deps = SimpleNamespace(
            ragflow_service=SimpleNamespace(config={"dataset_name": "展厅"}),
            ragflow_chat_service=SimpleNamespace(config={"default_conversation_name": "展厅聊天"}),
        )

    def test_dataset_name_defaults_to_dedicated_e2e_target(self) -> None:
        with patch.dict(os.environ, {}, clear=False):
            self.assertEqual(_resolve_dataset_name(self.tenant_deps, None), DEFAULT_E2E_DATASET_NAME)

    def test_chat_name_defaults_to_dedicated_e2e_target(self) -> None:
        with patch.dict(os.environ, {}, clear=False):
            self.assertEqual(_resolve_chat_name(self.tenant_deps, None), DEFAULT_E2E_CHAT_NAME)

    def test_dataset_name_env_override_wins(self) -> None:
        with patch.dict(os.environ, {"E2E_REAL_DATASET_NAME": "Custom Dataset"}, clear=False):
            self.assertEqual(_resolve_dataset_name(self.tenant_deps, None), "Custom Dataset")

    def test_chat_name_explicit_override_wins(self) -> None:
        with patch.dict(os.environ, {"E2E_REAL_CHAT_NAME": "Ignored By Explicit"}, clear=False):
            self.assertEqual(_resolve_chat_name(self.tenant_deps, "Explicit Chat"), "Explicit Chat")

    def test_materialize_bootstrap_resource_name_adds_run_tag_without_override(self) -> None:
        with patch.dict(os.environ, {}, clear=False):
            result = _materialize_bootstrap_resource_name(
                DEFAULT_E2E_DATASET_NAME,
                explicit_name=None,
                env_var="E2E_REAL_DATASET_NAME",
                run_tag="run-1",
            )
        self.assertEqual(result, "RagflowAuth E2E Dataset [run-1]")

    def test_materialize_bootstrap_resource_name_keeps_explicit_target(self) -> None:
        with patch.dict(os.environ, {}, clear=False):
            result = _materialize_bootstrap_resource_name(
                "Custom Dataset",
                explicit_name="Custom Dataset",
                env_var="E2E_REAL_DATASET_NAME",
                run_tag="run-1",
            )
        self.assertEqual(result, "Custom Dataset")

    def test_managed_bootstrap_resource_name_matches_default_and_generated_variants(self) -> None:
        self.assertTrue(
            _is_managed_bootstrap_resource_name("RagflowAuth E2E Dataset", base_name=DEFAULT_E2E_DATASET_NAME)
        )
        self.assertTrue(
            _is_managed_bootstrap_resource_name(
                "RagflowAuth E2E Dataset [run-1]",
                base_name=DEFAULT_E2E_DATASET_NAME,
            )
        )
        self.assertFalse(
            _is_managed_bootstrap_resource_name("Custom Dataset", base_name=DEFAULT_E2E_DATASET_NAME)
        )

    def test_unbind_previous_managed_dataset_bindings_clears_only_legacy_e2e_datasets(self) -> None:
        store = _BootstrapKnowledgeDirectoryStore()
        tenant_deps = SimpleNamespace(
            ragflow_service=SimpleNamespace(),
            knowledge_directory_store=store,
        )

        with patch(
            "scripts.bootstrap_real_test_env._probe_ragflow_datasets",
            return_value=[
                {"id": "active", "name": "RagflowAuth E2E Dataset [run-2]"},
                {"id": "legacy-base", "name": "RagflowAuth E2E Dataset"},
                {"id": "legacy-generated", "name": "RagflowAuth E2E Dataset [run-1]"},
                {"id": "foreign", "name": "Custom Dataset"},
            ],
        ):
            _unbind_previous_managed_dataset_bindings(tenant_deps, active_dataset_id="active")

        self.assertEqual(
            store.assign_calls,
            [
                ("legacy-base", None),
                ("legacy-generated", None),
            ],
        )

    def test_ensure_dataset_seed_content_cleans_non_seed_documents(self) -> None:
        seed_name = "ragflowauth-e2e-seed.txt"
        ragflow_service = _BootstrapRagflowService(
            [
                {"id": "seed-1", "name": seed_name, "status": "ready"},
                {"id": "old-1", "name": "historic-a.txt", "status": "ready"},
                {"id": "old-2", "name": "historic-b.txt", "status": "ready"},
                {"id": "seed-2", "name": seed_name, "status": "ready"},
            ]
        )
        tenant_deps = SimpleNamespace(ragflow_service=ragflow_service)

        with tempfile.TemporaryDirectory() as tmpdir:
            seed_path = Path(tmpdir) / seed_name
            seed_path.write_text("seed\n", encoding="utf-8")
            with (
                patch("scripts.bootstrap_real_test_env._ensure_ragflow_seed_file", return_value=seed_path),
                patch(
                    "scripts.bootstrap_real_test_env._probe_ragflow_datasets",
                    return_value=[{"id": "dataset-1", "name": "Dataset", "chunk_count": 1}],
                ),
            ):
                result = _ensure_dataset_seed_content(
                    tenant_deps,
                    dataset_info={"id": "dataset-1", "name": "Dataset"},
                )

        self.assertEqual(result, {"id": "dataset-1", "name": "Dataset"})
        self.assertEqual(
            ragflow_service.deleted,
            [
                ("old-1", "dataset-1"),
                ("old-2", "dataset-1"),
                ("seed-2", "dataset-1"),
            ],
        )
        self.assertEqual(ragflow_service.upload_calls, [])
        self.assertEqual(ragflow_service.parse_calls, [])

    def test_ensure_dataset_seed_content_uploads_seed_after_cleanup(self) -> None:
        seed_name = "ragflowauth-e2e-seed.txt"
        ragflow_service = _BootstrapRagflowService(
            [{"id": "old-1", "name": "historic-a.txt", "status": "ready"}],
            upload_doc_id="seed-uploaded",
        )
        tenant_deps = SimpleNamespace(ragflow_service=ragflow_service)

        with tempfile.TemporaryDirectory() as tmpdir:
            seed_path = Path(tmpdir) / seed_name
            seed_path.write_text("seed\n", encoding="utf-8")
            with (
                patch("scripts.bootstrap_real_test_env._ensure_ragflow_seed_file", return_value=seed_path),
                patch(
                    "scripts.bootstrap_real_test_env._probe_ragflow_datasets",
                    return_value=[{"id": "dataset-1", "name": "Dataset", "chunk_count": 0}],
                ),
                patch(
                    "scripts.bootstrap_real_test_env._wait_for_dataset_ready",
                    return_value={"id": "dataset-1", "name": "Dataset"},
                ) as wait_ready,
            ):
                result = _ensure_dataset_seed_content(
                    tenant_deps,
                    dataset_info={"id": "dataset-1", "name": "Dataset"},
                )

        self.assertEqual(result, {"id": "dataset-1", "name": "Dataset"})
        self.assertEqual(ragflow_service.deleted, [("old-1", "dataset-1")])
        self.assertEqual(ragflow_service.upload_calls, [(str(seed_path), "dataset-1")])
        self.assertEqual(ragflow_service.parse_calls, [("dataset-1", "seed-uploaded")])
        wait_ready.assert_called_once()

    def test_ensure_dataset_seed_content_fails_fast_when_cleanup_delete_fails(self) -> None:
        seed_name = "ragflowauth-e2e-seed.txt"
        ragflow_service = _BootstrapRagflowService(
            [{"id": "old-1", "name": "historic-a.txt", "status": "ready"}],
            delete_fail_ids={"old-1"},
        )
        tenant_deps = SimpleNamespace(ragflow_service=ragflow_service)

        with tempfile.TemporaryDirectory() as tmpdir:
            seed_path = Path(tmpdir) / seed_name
            seed_path.write_text("seed\n", encoding="utf-8")
            with (
                patch("scripts.bootstrap_real_test_env._ensure_ragflow_seed_file", return_value=seed_path),
                patch(
                    "scripts.bootstrap_real_test_env._probe_ragflow_datasets",
                    return_value=[{"id": "dataset-1", "name": "Dataset", "chunk_count": 0}],
                ),
            ):
                with self.assertRaisesRegex(
                    RuntimeError,
                    "ragflow_dataset_cleanup_delete_failed:Dataset; document_id=old-1; name=historic-a.txt",
                ):
                    _ensure_dataset_seed_content(
                        tenant_deps,
                        dataset_info={"id": "dataset-1", "name": "Dataset"},
                    )
