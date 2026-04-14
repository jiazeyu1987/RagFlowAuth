from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
from typing import Any

from backend.services.config_change_log_store import ConfigChangeLogStore
from backend.services.document_control import controlled_compliance_relpath


TRACEABILITY_MATRIX_PATH = controlled_compliance_relpath("traceability_matrix.md")
INTENDED_USE_PATH = controlled_compliance_relpath("intended_use.md")

SUPPORTED_CHANGE_CATEGORIES = ("os", "database", "api", "config", "intended_use")
REVALIDATION_CONFIG_DOMAINS = {"upload_allowed_extensions", "data_security_settings"}

REQUIREMENT_HINTS: dict[str, tuple[str, ...]] = {
    "os": ("GBZ-01", "R7", "R10"),
    "database": ("GBZ-01", "R9", "R10"),
    "api": ("GBZ-01", "R4", "R5", "R8", "FDA-02", "FDA-03"),
    "config": ("GBZ-01", "R7", "R10"),
    "intended_use": ("GBZ-01", "R7"),
}

BASE_ARTIFACTS: dict[str, tuple[str, ...]] = {
    "os": (
        controlled_compliance_relpath("maintenance_plan.md"),
        controlled_compliance_relpath("maintenance_review_status.md"),
        controlled_compliance_relpath("validation_plan.md"),
        controlled_compliance_relpath("validation_report.md"),
    ),
    "database": (
        controlled_compliance_relpath("maintenance_plan.md"),
        controlled_compliance_relpath("maintenance_review_status.md"),
        controlled_compliance_relpath("validation_plan.md"),
        controlled_compliance_relpath("validation_report.md"),
    ),
    "api": (
        controlled_compliance_relpath("maintenance_plan.md"),
        controlled_compliance_relpath("validation_plan.md"),
        controlled_compliance_relpath("validation_report.md"),
        controlled_compliance_relpath("traceability_matrix.md"),
    ),
    "config": (
        controlled_compliance_relpath("change_control_sop.md"),
        controlled_compliance_relpath("maintenance_plan.md"),
        controlled_compliance_relpath("maintenance_review_status.md"),
        controlled_compliance_relpath("validation_plan.md"),
        controlled_compliance_relpath("validation_report.md"),
    ),
    "intended_use": (
        controlled_compliance_relpath("intended_use.md"),
        controlled_compliance_relpath("maintenance_plan.md"),
        controlled_compliance_relpath("maintenance_review_status.md"),
        controlled_compliance_relpath("validation_plan.md"),
        controlled_compliance_relpath("validation_report.md"),
        controlled_compliance_relpath("traceability_matrix.md"),
    ),
}


@dataclass(slots=True, frozen=True)
class ChangeItem:
    category: str
    domain: str | None
    before: Any
    after: Any
    validation_completed: bool = False


@dataclass(slots=True, frozen=True)
class TraceabilityReference:
    requirement_id: str
    urs_id: str
    srs_id: str
    row_text: str

    def as_dict(self) -> dict[str, str]:
        return {
            "requirement_id": self.requirement_id,
            "urs_id": self.urs_id,
            "srs_id": self.srs_id,
            "row_text": self.row_text,
        }


@dataclass(slots=True, frozen=True)
class MaintenanceAssessment:
    category: str
    domain: str | None
    requires_revalidation: bool
    blocks_prior_validation: bool
    impacted_artifacts: list[str]
    traceability_refs: list[str]
    rationale: str
    validation_status: str

    def as_dict(self) -> dict[str, object]:
        return {
            "category": self.category,
            "domain": self.domain,
            "requires_revalidation": self.requires_revalidation,
            "blocks_prior_validation": self.blocks_prior_validation,
            "impacted_artifacts": list(self.impacted_artifacts),
            "traceability_refs": list(self.traceability_refs),
            "rationale": self.rationale,
            "validation_status": self.validation_status,
        }


class Gbz01MaintenanceService:
    def __init__(self, *, repo_root: str | Path, db_path: str | Path | None = None):
        self._repo_root = Path(repo_root).resolve()
        self._db_path = Path(db_path).resolve() if db_path is not None else None

    @property
    def current_intended_use_version(self) -> str:
        text = (self._repo_root / INTENDED_USE_PATH).read_text(encoding="utf-8")
        match = re.search(r"(?m)^版本:\s*(.+?)\s*$", text)
        if not match:
            raise ValueError("intended_use_version_missing")
        return match.group(1).strip()

    def assess_change_items(
        self,
        change_items: list[ChangeItem],
        *,
        validated_against_intended_use_version: str,
    ) -> list[MaintenanceAssessment]:
        return [
            self.assess_change_item(
                change_item,
                validated_against_intended_use_version=validated_against_intended_use_version,
            )
            for change_item in change_items
        ]

    def assess_recent_config_changes(
        self,
        *,
        validated_against_intended_use_version: str,
        limit: int = 20,
    ) -> list[MaintenanceAssessment]:
        if self._db_path is None:
            raise ValueError("db_path_required")
        log_store = ConfigChangeLogStore(db_path=self._db_path)
        entries = log_store.list_logs(limit=limit)
        change_items = [
            ChangeItem(
                category="config",
                domain=entry.config_domain,
                before=json.loads(entry.before_json or "{}"),
                after=json.loads(entry.after_json or "{}"),
                validation_completed=False,
            )
            for entry in entries
        ]
        return self.assess_change_items(
            change_items,
            validated_against_intended_use_version=validated_against_intended_use_version,
        )

    def assess_change_item(
        self,
        change_item: ChangeItem,
        *,
        validated_against_intended_use_version: str,
    ) -> MaintenanceAssessment:
        category = self._normalize_category(change_item.category)
        domain = (str(change_item.domain).strip() or None) if change_item.domain else None
        has_change = self._has_change(change_item.before, change_item.after)
        requires_revalidation = self._requires_revalidation(category, domain=domain, has_change=has_change)
        blocks_prior_validation = category == "intended_use" and has_change

        traceability_rows = self._load_traceability_refs(category)
        if not traceability_rows:
            raise ValueError(f"traceability_refs_missing:{category}")

        impacted_artifacts = sorted(set(BASE_ARTIFACTS[category]).union(self._extract_artifacts(traceability_rows)))
        traceability_refs = [f"{row.requirement_id}/{row.srs_id}" for row in traceability_rows]

        current_intended_use_version = self.current_intended_use_version
        if blocks_prior_validation and validated_against_intended_use_version != current_intended_use_version:
            validation_status = "blocked"
            rationale = (
                f"预期用途版本已从 {validated_against_intended_use_version} 变更为 "
                f"{current_intended_use_version}，旧验证结论不得继续沿用。"
            )
        elif requires_revalidation and change_item.validation_completed:
            validation_status = "closed"
            rationale = f"{category} 变更已完成再确认闭环，并已更新验证证据。"
        elif requires_revalidation:
            validation_status = "pending_revalidation"
            rationale = f"{category} 变更命中 GBZ-01 再确认触发器，必须更新验证证据。"
        else:
            validation_status = "not_required"
            rationale = f"{category} 变更未命中当前强制再确认规则。"

        return MaintenanceAssessment(
            category=category,
            domain=domain,
            requires_revalidation=requires_revalidation,
            blocks_prior_validation=blocks_prior_validation,
            impacted_artifacts=impacted_artifacts,
            traceability_refs=traceability_refs,
            rationale=rationale,
            validation_status=validation_status,
        )

    @staticmethod
    def _normalize_category(category: str) -> str:
        normalized = str(category or "").strip().lower()
        if normalized not in SUPPORTED_CHANGE_CATEGORIES:
            raise ValueError(f"unsupported_change_category:{normalized}")
        return normalized

    @staticmethod
    def _normalize_json(value: Any) -> str:
        return json.dumps(value if value is not None else {}, ensure_ascii=False, sort_keys=True)

    def _has_change(self, before: Any, after: Any) -> bool:
        return self._normalize_json(before) != self._normalize_json(after)

    @staticmethod
    def _requires_revalidation(category: str, *, domain: str | None, has_change: bool) -> bool:
        if not has_change:
            return False
        if category in {"os", "database", "api", "intended_use"}:
            return True
        if category == "config":
            return str(domain or "").strip() in REVALIDATION_CONFIG_DOMAINS
        return False

    def _load_traceability_refs(self, category: str) -> list[TraceabilityReference]:
        text = (self._repo_root / TRACEABILITY_MATRIX_PATH).read_text(encoding="utf-8")
        rows = []
        requirement_hints = set(REQUIREMENT_HINTS[category])
        for row in self._parse_matrix_rows(text):
            if row[0] not in requirement_hints:
                continue
            rows.append(
                TraceabilityReference(
                    requirement_id=row[0],
                    urs_id=row[1],
                    srs_id=row[2],
                    row_text=" | ".join(row),
                )
            )
        return rows

    @staticmethod
    def _parse_matrix_rows(text: str) -> list[list[str]]:
        lines = [line.strip() for line in text.splitlines() if line.strip().startswith("|")]
        parsed: list[list[str]] = []
        for line in lines[2:]:
            row = [cell.strip() for cell in line.strip("|").split("|")]
            if len(row) >= 7:
                parsed.append(row[:7])
        return parsed

    @staticmethod
    def _extract_artifacts(rows: list[TraceabilityReference]) -> list[str]:
        artifacts: set[str] = set()
        pattern = re.compile(r"`([^`]+)`")
        for row in rows:
            for match in pattern.findall(row.row_text):
                if "/" in match or match.endswith(".py") or match.endswith(".md"):
                    artifacts.add(match)
        return sorted(artifacts)
