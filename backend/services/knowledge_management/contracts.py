from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class KnowledgeManagementScope:
    mode: str
    root_node_id: str | None
    root_node_path: str | None
    node_ids: frozenset[str]
    dataset_ids: frozenset[str]

    @property
    def can_manage(self) -> bool:
        return self.mode in {"all", "subtree"}

    @property
    def is_admin(self) -> bool:
        return self.mode == "all"


@dataclass
class KnowledgeManagementError(Exception):
    code: str
    status_code: int = 400

    def __str__(self) -> str:
        return self.code
