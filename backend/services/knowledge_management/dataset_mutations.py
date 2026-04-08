from __future__ import annotations

from typing import Any

from backend.services.ragflow_service import RagflowService

from .contracts import KnowledgeManagementError
from .directory_actions import KnowledgeDirectoryActions
from .scope_resolver import KnowledgeManagementScopeResolver


class KnowledgeDatasetMutations:
    def __init__(
        self,
        *,
        ragflow_service: RagflowService,
        scope_resolver: KnowledgeManagementScopeResolver,
        directory_actions: KnowledgeDirectoryActions,
    ):
        self._ragflow_service = ragflow_service
        self._scope_resolver = scope_resolver
        self._directory_actions = directory_actions

    def create_dataset(self, *, user: Any, payload: dict[str, Any]) -> dict[str, Any]:
        body = self.prepare_dataset_create_payload(user=user, payload=payload)
        node_id = body.pop("node_id", None)

        try:
            created = self._ragflow_service.create_dataset(body)
        except Exception as exc:
            raise KnowledgeManagementError(str(exc) or "dataset_create_failed", status_code=502) from exc
        if not created or not isinstance(created, dict) or not created.get("id"):
            raise KnowledgeManagementError("dataset_create_failed", status_code=500)

        if node_id:
            self._directory_actions.assign_dataset(
                user=user,
                dataset_ref=str(created.get("id")),
                node_id=str(node_id),
            )
        return created

    def update_dataset(self, *, user: Any, dataset_ref: str, updates: dict[str, Any]) -> dict[str, Any]:
        _, dataset_id = self._scope_resolver.assert_dataset_manageable(user, dataset_ref)
        try:
            updated = self._ragflow_service.update_dataset(dataset_id, updates)
        except Exception as exc:
            raise KnowledgeManagementError(str(exc) or "dataset_update_failed", status_code=502) from exc
        if updated:
            return updated
        raise KnowledgeManagementError("dataset_update_failed", status_code=500)

    def delete_dataset(self, *, user: Any, dataset_ref: str) -> str:
        _, dataset_id = self._scope_resolver.assert_dataset_manageable(user, dataset_ref)
        try:
            self._ragflow_service.delete_dataset_if_empty(dataset_id)
        except ValueError as exc:
            code = str(exc) or "dataset_delete_failed"
            if code == "dataset_not_found":
                raise KnowledgeManagementError(code, status_code=404) from exc
            if code == "dataset_not_empty":
                raise KnowledgeManagementError(code, status_code=409) from exc
            raise KnowledgeManagementError(code, status_code=400) from exc
        except Exception as exc:
            raise KnowledgeManagementError(str(exc) or "dataset_delete_failed", status_code=502) from exc
        return dataset_id

    def prepare_dataset_create_payload(self, *, user: Any, payload: dict[str, Any]) -> dict[str, Any]:
        scope = self._scope_resolver.assert_can_manage(user)
        body = dict(payload or {})
        node_id = body.get("node_id")
        name = str(body.get("name") or "").strip()
        if not name:
            raise KnowledgeManagementError("missing_name", status_code=400)
        body["name"] = name
        body.pop("id", None)
        body.pop("dataset_id", None)
        if scope.mode == "subtree":
            if not isinstance(node_id, str) or not node_id.strip():
                raise KnowledgeManagementError("target_node_required_for_sub_admin", status_code=400)
            self._scope_resolver.assert_node_manageable(user, node_id)
        return body

    def prepare_dataset_delete(self, *, user: Any, dataset_ref: str) -> dict[str, str]:
        _, dataset_id = self._scope_resolver.assert_dataset_manageable(user, dataset_ref)
        detail = self._ragflow_service.get_dataset_detail(dataset_id)
        if not detail:
            raise KnowledgeManagementError("dataset_not_found", status_code=404)
        try:
            doc_count = int(detail.get("document_count") or 0)
        except Exception:
            doc_count = 0
        try:
            chunk_count = int(detail.get("chunk_count") or 0)
        except Exception:
            chunk_count = 0
        if doc_count > 0 or chunk_count > 0:
            raise KnowledgeManagementError("dataset_not_empty", status_code=409)
        dataset_name = str(detail.get("name") or dataset_id)
        return {
            "dataset_ref": dataset_ref,
            "dataset_id": dataset_id,
            "dataset_name": dataset_name,
        }
