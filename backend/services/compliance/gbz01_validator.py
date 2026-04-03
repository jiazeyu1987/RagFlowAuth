from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
import re

from .gbz01_maintenance import ChangeItem, Gbz01MaintenanceService
from .r7_validator import ComplianceIssue


@dataclass(slots=True)
class Gbz01ComplianceReport:
    checked_at: str
    blocking_issues: list[ComplianceIssue] = field(default_factory=list)
    external_gaps: list[ComplianceIssue] = field(default_factory=list)
    checked_files: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not self.blocking_issues

    def as_dict(self) -> dict[str, object]:
        return {
            "checked_at": self.checked_at,
            "passed": self.passed,
            "blocking_issues": [item.as_dict() for item in self.blocking_issues],
            "external_gaps": [item.as_dict() for item in self.external_gaps],
            "checked_files": list(self.checked_files),
        }


REQUIRED_DOCS: dict[str, tuple[str, ...]] = {
    "doc/compliance/maintenance_plan.md": (
        "版本:",
        "更新时间:",
        "当前环境:",
        "计划覆盖变更类别:",
        "维护责任人:",
        "QA复核人:",
        "下次维护计划复核日期:",
        "仓库外残余项:",
    ),
    "doc/compliance/maintenance_review_status.md": (
        "版本:",
        "更新时间:",
        "最后仓库复核日期:",
        "下次仓库复核截止日期:",
        "当前验证状态:",
        "预期用途复核状态:",
        "仓库内证据状态:",
        "仓库外证据状态:",
        "Residual gap 边界:",
    ),
    "doc/compliance/intended_use.md": ("版本:", "更新时间:", "维护阶段复核", "旧验证结论"),
    "doc/compliance/urs.md": ("URS-013", "GBZ-01"),
    "doc/compliance/srs.md": ("SRS-013", "URS-013"),
    "doc/compliance/traceability_matrix.md": ("GBZ-01", "SRS-013"),
    "doc/compliance/validation_plan.md": (
        "validate_gbz01_repo_compliance.py",
        "test_gbz01_maintenance_unit",
        "test_gbz01_compliance_gate_unit",
    ),
    "doc/compliance/validation_report.md": (
        "GBZ-01",
        "validate_gbz01_repo_compliance.py",
        "residual gap",
    ),
}

REQUIRED_FILES: tuple[str, ...] = (
    "backend/services/compliance/gbz01_maintenance.py",
    "backend/services/compliance/gbz01_validator.py",
    "backend/tests/test_gbz01_maintenance_unit.py",
    "backend/tests/test_gbz01_compliance_gate_unit.py",
    "scripts/validate_gbz01_repo_compliance.py",
)

REQUIRED_PATTERNS: tuple[tuple[str, str, str], ...] = (
    (
        "doc/compliance/traceability_matrix.md",
        r"\|\s*GBZ-01\s*\|\s*URS-013\s*\|\s*SRS-013\s*\|",
        "追踪矩阵缺少 GBZ-01 映射",
    ),
    (
        "doc/compliance/traceability_matrix.md",
        r"backend/services/compliance/gbz01_maintenance\.py",
        "追踪矩阵缺少 GBZ-01 维护判定实现映射",
    ),
    (
        "doc/compliance/traceability_matrix.md",
        r"backend\.tests\.test_gbz01_compliance_gate_unit",
        "追踪矩阵缺少 GBZ-01 gate 测试映射",
    ),
)


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _extract_value(text: str, label: str) -> str | None:
    match = re.search(rf"(?m)^{re.escape(label)}\s*(.+?)\s*$", text)
    if not match:
        return None
    return match.group(1).strip()


def _parse_iso_date(value: str, *, code: str, report: Gbz01ComplianceReport, path: str) -> date | None:
    try:
        return date.fromisoformat(value)
    except ValueError:
        report.blocking_issues.append(
            ComplianceIssue(code=code, message=f"日期格式无效: {value}", path=path)
        )
        return None


def validate_gbz01_repo_state(repo_root: str | Path, *, as_of: date | None = None) -> Gbz01ComplianceReport:
    root = Path(repo_root).resolve()
    current_date = as_of or date.today()
    report = Gbz01ComplianceReport(checked_at=datetime.now().astimezone().isoformat(timespec="seconds"))
    docs_cache: dict[str, str] = {}

    for rel_path, keys in REQUIRED_DOCS.items():
        report.checked_files.append(rel_path)
        path = root / rel_path
        if not path.exists():
            report.blocking_issues.append(
                ComplianceIssue(code="missing_required_doc", message="缺少 GBZ-01 必需文档", path=rel_path)
            )
            continue
        text = _read_text(path)
        docs_cache[rel_path] = text
        for key in keys:
            if key not in text:
                report.blocking_issues.append(
                    ComplianceIssue(code="missing_doc_metadata", message=f"文档缺少字段 {key}", path=rel_path)
                )

    for rel_path in REQUIRED_FILES:
        report.checked_files.append(rel_path)
        if not (root / rel_path).exists():
            report.blocking_issues.append(
                ComplianceIssue(code="missing_required_artifact", message="缺少 GBZ-01 必需实现或测试文件", path=rel_path)
            )

    for rel_path, pattern, message in REQUIRED_PATTERNS:
        text = docs_cache.get(rel_path, "")
        if text and re.search(pattern, text) is None:
            report.blocking_issues.append(
                ComplianceIssue(code="required_mapping_missing", message=message, path=rel_path)
            )

    review_text = docs_cache.get("doc/compliance/maintenance_review_status.md", "")
    if review_text:
        repo_status = _extract_value(review_text, "仓库内证据状态:")
        external_status = _extract_value(review_text, "仓库外证据状态:")
        next_review_raw = _extract_value(review_text, "下次仓库复核截止日期:")
        if repo_status != "complete":
            report.blocking_issues.append(
                ComplianceIssue(
                    code="repo_evidence_incomplete",
                    message="GBZ-01 仓库内证据状态不是 complete",
                    path="doc/compliance/maintenance_review_status.md",
                )
            )
        if external_status and external_status != "archived":
            report.external_gaps.append(
                ComplianceIssue(
                    code="external_maintenance_evidence_pending",
                    message=f"线下维护执行证据仍待归档: {external_status}",
                    path="doc/compliance/maintenance_review_status.md",
                )
            )
        if next_review_raw:
            next_review = _parse_iso_date(
                next_review_raw,
                code="invalid_maintenance_review_date",
                report=report,
                path="doc/compliance/maintenance_review_status.md",
            )
            if next_review and next_review < current_date:
                report.blocking_issues.append(
                    ComplianceIssue(
                        code="maintenance_review_overdue",
                        message="GBZ-01 维护复核已过期",
                        path="doc/compliance/maintenance_review_status.md",
                    )
                )

    plan_text = docs_cache.get("doc/compliance/maintenance_plan.md", "")
    if plan_text:
        next_plan_raw = _extract_value(plan_text, "下次维护计划复核日期:")
        if next_plan_raw:
            next_plan = _parse_iso_date(
                next_plan_raw,
                code="invalid_maintenance_plan_review_date",
                report=report,
                path="doc/compliance/maintenance_plan.md",
            )
            if next_plan and next_plan < current_date:
                report.blocking_issues.append(
                    ComplianceIssue(
                        code="maintenance_plan_review_overdue",
                        message="GBZ-01 维护计划复核已过期",
                        path="doc/compliance/maintenance_plan.md",
                    )
                )

    try:
        service = Gbz01MaintenanceService(repo_root=root)
        baseline_version = service.current_intended_use_version
        assessments = service.assess_change_items(
            [
                ChangeItem(category="os", domain="windows_server_patch", before={"version": "1"}, after={"version": "2"}),
                ChangeItem(category="database", domain="sqlite_engine", before={"version": "1"}, after={"version": "2"}),
                ChangeItem(category="api", domain="audit_router", before={"version": "1"}, after={"version": "2"}),
                ChangeItem(category="config", domain="upload_allowed_extensions", before={"value": 1}, after={"value": 2}),
                ChangeItem(category="config", domain="data_security_settings", before={"value": 1}, after={"value": 2}, validation_completed=True),
                ChangeItem(category="intended_use", domain="intended_use_document", before={"version": "v0.9"}, after={"version": baseline_version}),
            ],
            validated_against_intended_use_version="v0.9",
        )
    except Exception as exc:
        report.blocking_issues.append(
            ComplianceIssue(
                code="maintenance_service_invalid",
                message=f"GBZ-01 维护判定能力不可用: {exc}",
                path="backend/services/compliance/gbz01_maintenance.py",
            )
        )
        assessments = []

    for assessment in assessments:
        if assessment.category in {"os", "database", "api", "intended_use"} and not assessment.requires_revalidation:
            report.blocking_issues.append(
                ComplianceIssue(
                    code="revalidation_rule_missing",
                    message=f"{assessment.category} 变更未触发再确认",
                    path="backend/services/compliance/gbz01_maintenance.py",
                )
            )
        if assessment.category == "intended_use" and not assessment.blocks_prior_validation:
            report.blocking_issues.append(
                ComplianceIssue(
                    code="prior_validation_not_blocked",
                    message="预期用途变化未阻断旧验证结论继续沿用",
                    path="backend/services/compliance/gbz01_maintenance.py",
                )
            )
        if assessment.category == "config" and assessment.domain == "data_security_settings" and assessment.validation_status != "closed":
            report.blocking_issues.append(
                ComplianceIssue(
                    code="validation_closure_missing",
                    message="维护后验证状态未形成 closed 闭环",
                    path="backend/services/compliance/gbz01_maintenance.py",
                )
            )
        if not assessment.traceability_refs:
            report.blocking_issues.append(
                ComplianceIssue(
                    code="traceability_refs_missing",
                    message=f"{assessment.category} 变更未关联追踪矩阵输入",
                    path="doc/compliance/traceability_matrix.md",
                )
            )

    return report
