from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
import re

from backend.services.document_control import controlled_compliance_relpath

from .r7_validator import ComplianceIssue


@dataclass(slots=True)
class Gbz05ComplianceReport:
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
    controlled_compliance_relpath("training_matrix.md"): (
        "版本:",
        "更新时间:",
        "TR-001",
        "TR-002",
        "document_review",
        "restore_drill_execute",
        "curriculum_version",
    ),
    controlled_compliance_relpath("training_operator_qualification_status.md"): (
        "版本:",
        "更新时间:",
        "最后仓库复核日期:",
        "下次仓库复核截止日期:",
        "仓库内证据状态:",
        "仓库外证据状态:",
        "Residual gap 边界:",
    ),
    controlled_compliance_relpath("controlled_document_register.md"): (
        controlled_compliance_relpath("training_matrix.md"),
        controlled_compliance_relpath("training_operator_qualification_status.md"),
    ),
    controlled_compliance_relpath("urs.md"): ("URS-017", "GBZ-05"),
    controlled_compliance_relpath("srs.md"): ("SRS-017", "URS-017"),
    controlled_compliance_relpath("traceability_matrix.md"): ("GBZ-05", "SRS-017"),
    controlled_compliance_relpath("validation_plan.md"): (
        "validate_gbz05_repo_compliance.py",
        "test_training_compliance_api_unit",
        "test_gbz05_compliance_gate_unit",
    ),
    controlled_compliance_relpath("validation_report.md"): (
        "GBZ-05",
        "validate_gbz05_repo_compliance.py",
        "external_training_qualification_records_pending",
    ),
}

REQUIRED_FILES: tuple[str, ...] = (
    "backend/database/schema/training_compliance.py",
    "backend/services/training_compliance.py",
    "backend/app/core/training_support.py",
    "backend/app/modules/training_compliance/router.py",
    "backend/api/training_compliance.py",
    "backend/app/dependencies.py",
    "backend/app/main.py",
    "backend/app/modules/operation_approvals/router.py",
    "backend/services/operation_approval/service.py",
    "backend/app/modules/data_security/router.py",
    "backend/services/compliance/gbz05_validator.py",
    "backend/tests/test_training_compliance_api_unit.py",
    "backend/tests/test_gbz05_compliance_gate_unit.py",
    "scripts/validate_gbz05_repo_compliance.py",
)

REQUIRED_PATTERNS: tuple[tuple[str, str, str], ...] = (
    (
        controlled_compliance_relpath("traceability_matrix.md"),
        r"\|\s*GBZ-05\s*\|\s*URS-017\s*\|\s*SRS-017\s*\|",
        "追踪矩阵缺少 GBZ-05 映射",
    ),
    (
        controlled_compliance_relpath("traceability_matrix.md"),
        r"backend/services/training_compliance\.py",
        "追踪矩阵缺少培训与操作员认证实现映射",
    ),
    (
        controlled_compliance_relpath("traceability_matrix.md"),
        r"backend\.tests\.test_training_compliance_api_unit",
        "追踪矩阵缺少 GBZ-05 测试映射",
    ),
)


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _extract_value(text: str, label: str) -> str | None:
    match = re.search(rf"(?m)^{re.escape(label)}\s*(.+?)\s*$", text)
    if not match:
        return None
    return match.group(1).strip()


def validate_gbz05_repo_state(repo_root: str | Path, *, as_of: date | None = None) -> Gbz05ComplianceReport:
    root = Path(repo_root).resolve()
    current_date = as_of or date.today()
    report = Gbz05ComplianceReport(
        checked_at=datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    )
    docs_cache: dict[str, str] = {}

    for rel_path, keys in REQUIRED_DOCS.items():
        path = root / rel_path
        report.checked_files.append(rel_path)
        if not path.exists():
            report.blocking_issues.append(
                ComplianceIssue(code="missing_required_doc", message="缺少 GBZ-05 必需受控文档", path=rel_path)
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
                ComplianceIssue(code="missing_required_artifact", message="缺少 GBZ-05 必需实现或测试文件", path=rel_path)
            )

    for rel_path, pattern, message in REQUIRED_PATTERNS:
        text = docs_cache.get(rel_path, "")
        if text and re.search(pattern, text) is None:
            report.blocking_issues.append(
                ComplianceIssue(code="required_mapping_missing", message=message, path=rel_path)
            )

    status_path = controlled_compliance_relpath("training_operator_qualification_status.md")
    status_text = docs_cache.get(status_path, "")
    if status_text:
        repo_status = _extract_value(status_text, "仓库内证据状态:")
        external_status = _extract_value(status_text, "仓库外证据状态:")
        next_review_raw = _extract_value(status_text, "下次仓库复核截止日期:")
        if repo_status != "complete":
            report.blocking_issues.append(
                ComplianceIssue(
                    code="repo_evidence_incomplete",
                    message="GBZ-05 仓库内证据状态不是 complete",
                    path=status_path,
                )
            )
        if external_status and external_status != "archived":
            report.external_gaps.append(
                ComplianceIssue(
                    code="external_training_qualification_records_pending",
                    message=f"线下培训签到、考核签字或例外放行记录仍待归档: {external_status}",
                    path=status_path,
                )
            )
        if next_review_raw:
            try:
                next_review = date.fromisoformat(next_review_raw)
            except ValueError:
                report.blocking_issues.append(
                    ComplianceIssue(
                        code="invalid_training_review_date",
                        message=f"无效日期格式: {next_review_raw}",
                        path=status_path,
                    )
                )
            else:
                if next_review < current_date:
                    report.blocking_issues.append(
                        ComplianceIssue(
                            code="training_review_overdue",
                            message="GBZ-05 仓库复核已过期",
                            path=status_path,
                        )
                    )

    service_path = root / "backend/services/training_compliance.py"
    if service_path.exists():
        service_text = _read_text(service_path)
        for token in (
            "training_curriculum_outdated",
            "operator_certification_expired",
            "document_review",
            "restore_drill_execute",
            "effectiveness_status",
            "training_requirement_not_configured",
        ):
            if token not in service_text:
                report.blocking_issues.append(
                    ComplianceIssue(
                        code="training_service_rule_missing",
                        message=f"培训认证服务缺少关键规则 {token}",
                        path="backend/services/training_compliance.py",
                    )
                )

    route_path = root / "backend/app/modules/training_compliance/router.py"
    if route_path.exists():
        route_text = _read_text(route_path)
        for token in (
            "/training-compliance/requirements",
            "/training-compliance/records",
            "/training-compliance/certifications",
            "/training-compliance/actions/{controlled_action}/users/{user_id}",
            "training_record_create",
            "operator_certification_create",
        ):
            if token not in route_text:
                report.blocking_issues.append(
                    ComplianceIssue(
                        code="training_route_missing",
                        message=f"培训认证路由缺少关键能力 {token}",
                        path="backend/app/modules/training_compliance/router.py",
                    )
                )

    for rel_path in (
        "backend/app/modules/operation_approvals/router.py",
        "backend/app/modules/data_security/router.py",
    ):
        path = root / rel_path
        if not path.exists():
            continue
        text = _read_text(path)
        if "assert_user_training_for_action" not in text:
            report.blocking_issues.append(
                ComplianceIssue(
                    code="runtime_training_gate_missing",
                    message="关键动作未接入培训认证门禁",
                    path=rel_path,
                )
            )

    dependencies_path = root / "backend/app/dependencies.py"
    if dependencies_path.exists():
        dependencies_text = _read_text(dependencies_path)
        if "training_compliance_service" not in dependencies_text:
            report.blocking_issues.append(
                ComplianceIssue(
                    code="training_service_dependency_missing",
                    message="依赖注入未注册 training_compliance_service",
                    path="backend/app/dependencies.py",
                )
            )

    main_path = root / "backend/app/main.py"
    if main_path.exists():
        main_text = _read_text(main_path)
        if "training_compliance.router" not in main_text and "training_compliance.router," not in main_text:
            report.blocking_issues.append(
                ComplianceIssue(
                    code="training_router_not_included",
                    message="应用入口未包含 training_compliance 路由",
                    path="backend/app/main.py",
                )
            )

    return report
