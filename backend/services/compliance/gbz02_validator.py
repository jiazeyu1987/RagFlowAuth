from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
import re

from .r7_validator import ComplianceIssue


@dataclass(slots=True)
class Gbz02ComplianceReport:
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
    "doc/compliance/emergency_change_sop.md": (
        "版本:",
        "更新时间:",
        "先授权后部署再复盘",
        "authorization_basis",
        "risk_control",
        "post_review_summary",
        "capa_actions",
    ),
    "doc/compliance/emergency_change_status.md": (
        "版本:",
        "更新时间:",
        "最后仓库复核日期:",
        "下次仓库复核截止日期:",
        "仓库内证据状态:",
        "仓库外证据状态:",
        "Residual gap 边界:",
    ),
    "doc/compliance/change_control_sop.md": ("紧急变更", "先授权", "后部署", "事后评审"),
    "doc/compliance/urs.md": ("URS-014", "GBZ-02"),
    "doc/compliance/srs.md": ("SRS-014", "URS-014"),
    "doc/compliance/traceability_matrix.md": ("GBZ-02", "SRS-014"),
    "doc/compliance/validation_plan.md": (
        "validate_gbz02_repo_compliance.py",
        "test_emergency_change_api_unit",
        "test_gbz02_compliance_gate_unit",
    ),
    "doc/compliance/validation_report.md": (
        "GBZ-02",
        "validate_gbz02_repo_compliance.py",
        "external_emergency_change_execution_pending",
    ),
    "doc/compliance/controlled_document_register.md": (
        "doc/compliance/emergency_change_sop.md",
        "doc/compliance/emergency_change_status.md",
    ),
}

REQUIRED_FILES: tuple[str, ...] = (
    "backend/database/schema/emergency_changes.py",
    "backend/services/emergency_change.py",
    "backend/app/modules/emergency_changes/router.py",
    "backend/api/emergency_changes.py",
    "backend/services/compliance/gbz02_validator.py",
    "backend/tests/test_emergency_change_api_unit.py",
    "backend/tests/test_gbz02_compliance_gate_unit.py",
    "scripts/validate_gbz02_repo_compliance.py",
)

REQUIRED_PATTERNS: tuple[tuple[str, str, str], ...] = (
    (
        "doc/compliance/traceability_matrix.md",
        r"\|\s*GBZ-02\s*\|\s*URS-014\s*\|\s*SRS-014\s*\|",
        "追踪矩阵缺少 GBZ-02 映射",
    ),
    (
        "doc/compliance/traceability_matrix.md",
        r"backend/services/emergency_change\.py",
        "追踪矩阵缺少紧急变更实现映射",
    ),
    (
        "doc/compliance/traceability_matrix.md",
        r"backend\.tests\.test_emergency_change_api_unit",
        "追踪矩阵缺少 GBZ-02 API 测试映射",
    ),
)


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _extract_value(text: str, label: str) -> str | None:
    match = re.search(rf"(?m)^{re.escape(label)}\s*(.+?)\s*$", text)
    if not match:
        return None
    return match.group(1).strip()


def validate_gbz02_repo_state(repo_root: str | Path, *, as_of: date | None = None) -> Gbz02ComplianceReport:
    root = Path(repo_root).resolve()
    current_date = as_of or date.today()
    report = Gbz02ComplianceReport(
        checked_at=datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    )
    docs_cache: dict[str, str] = {}

    for rel_path, keys in REQUIRED_DOCS.items():
        path = root / rel_path
        report.checked_files.append(rel_path)
        if not path.exists():
            report.blocking_issues.append(
                ComplianceIssue(code="missing_required_doc", message="缺少 GBZ-02 必需受控文档", path=rel_path)
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
        path = root / rel_path
        report.checked_files.append(rel_path)
        if not path.exists():
            report.blocking_issues.append(
                ComplianceIssue(code="missing_required_artifact", message="缺少 GBZ-02 必需实现或测试文件", path=rel_path)
            )

    for rel_path, pattern, message in REQUIRED_PATTERNS:
        text = docs_cache.get(rel_path, "")
        if text and re.search(pattern, text) is None:
            report.blocking_issues.append(
                ComplianceIssue(code="required_mapping_missing", message=message, path=rel_path)
            )

    status_path = "doc/compliance/emergency_change_status.md"
    status_text = docs_cache.get(status_path, "")
    if status_text:
        repo_status = _extract_value(status_text, "仓库内证据状态:")
        external_status = _extract_value(status_text, "仓库外证据状态:")
        next_review_raw = _extract_value(status_text, "下次仓库复核截止日期:")
        if repo_status != "complete":
            report.blocking_issues.append(
                ComplianceIssue(
                    code="repo_evidence_incomplete",
                    message="GBZ-02 仓库内证据状态不是 complete",
                    path=status_path,
                )
            )
        if external_status and external_status != "archived":
            report.external_gaps.append(
                ComplianceIssue(
                    code="external_emergency_change_execution_pending",
                    message=f"线下紧急变更执行证据仍待归档: {external_status}",
                    path=status_path,
                )
            )
        if next_review_raw:
            try:
                next_review = date.fromisoformat(next_review_raw)
            except ValueError:
                report.blocking_issues.append(
                    ComplianceIssue(
                        code="invalid_emergency_change_review_date",
                        message=f"无效日期格式: {next_review_raw}",
                        path=status_path,
                    )
                )
            else:
                if next_review < current_date:
                    report.blocking_issues.append(
                        ComplianceIssue(
                            code="emergency_change_review_overdue",
                            message="GBZ-02 仓库复核已过期",
                            path=status_path,
                        )
                    )

    service_path = root / "backend/services/emergency_change.py"
    if service_path.exists():
        service_text = _read_text(service_path)
        required_tokens = (
            "requested",
            "authorized",
            "deployed",
            "closed",
            "authorization_basis_required",
            "risk_control_required",
            "emergency_change_must_be_authorized_before_deploy",
            "post_review_summary_required",
            "impact_assessment_summary_required",
            "capa_actions_required",
            "verification_summary_required",
        )
        for token in required_tokens:
            if token not in service_text:
                report.blocking_issues.append(
                    ComplianceIssue(
                        code="state_machine_rule_missing",
                        message=f"紧急变更服务缺少关键规则 {token}",
                        path="backend/services/emergency_change.py",
                    )
                )

    return report
