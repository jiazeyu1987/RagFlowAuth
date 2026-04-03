from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
import re

from .r7_validator import ComplianceIssue


@dataclass(slots=True)
class Gbz04ComplianceReport:
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
    "doc/compliance/supplier_assessment.md": (
        "版本:",
        "更新时间:",
        "AVL",
        "OTSS",
        "供应商审核",
        "已知问题",
        "再确认触发",
    ),
    "doc/compliance/environment_qualification_status.md": (
        "版本:",
        "更新时间:",
        "最后仓库复核日期:",
        "下次仓库复核截止日期:",
        "仓库内证据状态:",
        "仓库外证据状态:",
        "Residual gap 边界:",
        "IQ",
        "OQ",
        "PQ",
    ),
    "doc/compliance/controlled_document_register.md": (
        "doc/compliance/supplier_assessment.md",
        "doc/compliance/environment_qualification_status.md",
    ),
    "doc/compliance/urs.md": ("URS-016", "GBZ-04"),
    "doc/compliance/srs.md": ("SRS-016", "URS-016"),
    "doc/compliance/traceability_matrix.md": ("GBZ-04", "SRS-016"),
    "doc/compliance/validation_plan.md": (
        "validate_gbz04_repo_compliance.py",
        "test_supplier_qualification_api_unit",
        "test_gbz04_compliance_gate_unit",
    ),
    "doc/compliance/validation_report.md": (
        "GBZ-04",
        "validate_gbz04_repo_compliance.py",
        "external_supplier_qualification_records_pending",
    ),
}

REQUIRED_FILES: tuple[str, ...] = (
    "backend/database/schema/supplier_qualification.py",
    "backend/services/supplier_qualification.py",
    "backend/app/modules/supplier_qualification/router.py",
    "backend/api/supplier_qualification.py",
    "backend/app/dependencies.py",
    "backend/app/main.py",
    "backend/services/compliance/gbz04_validator.py",
    "backend/tests/test_supplier_qualification_api_unit.py",
    "backend/tests/test_gbz04_compliance_gate_unit.py",
    "scripts/validate_gbz04_repo_compliance.py",
)

REQUIRED_PATTERNS: tuple[tuple[str, str, str], ...] = (
    (
        "doc/compliance/traceability_matrix.md",
        r"\|\s*GBZ-04\s*\|\s*URS-016\s*\|\s*SRS-016\s*\|",
        "追踪矩阵缺少 GBZ-04 映射",
    ),
    (
        "doc/compliance/traceability_matrix.md",
        r"backend/services/supplier_qualification\.py",
        "追踪矩阵缺少供应商/环境确认实现映射",
    ),
    (
        "doc/compliance/traceability_matrix.md",
        r"backend\.tests\.test_supplier_qualification_api_unit",
        "追踪矩阵缺少 GBZ-04 API 测试映射",
    ),
)


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _extract_value(text: str, label: str) -> str | None:
    match = re.search(rf"(?m)^{re.escape(label)}\s*(.+?)\s*$", text)
    if not match:
        return None
    return match.group(1).strip()


def validate_gbz04_repo_state(repo_root: str | Path, *, as_of: date | None = None) -> Gbz04ComplianceReport:
    root = Path(repo_root).resolve()
    current_date = as_of or date.today()
    report = Gbz04ComplianceReport(
        checked_at=datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    )
    docs_cache: dict[str, str] = {}

    for rel_path, keys in REQUIRED_DOCS.items():
        path = root / rel_path
        report.checked_files.append(rel_path)
        if not path.exists():
            report.blocking_issues.append(
                ComplianceIssue(code="missing_required_doc", message="缺少 GBZ-04 必需受控文档", path=rel_path)
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
                ComplianceIssue(code="missing_required_artifact", message="缺少 GBZ-04 必需实现或测试文件", path=rel_path)
            )

    for rel_path, pattern, message in REQUIRED_PATTERNS:
        text = docs_cache.get(rel_path, "")
        if text and re.search(pattern, text) is None:
            report.blocking_issues.append(
                ComplianceIssue(code="required_mapping_missing", message=message, path=rel_path)
            )

    status_path = "doc/compliance/environment_qualification_status.md"
    status_text = docs_cache.get(status_path, "")
    if status_text:
        repo_status = _extract_value(status_text, "仓库内证据状态:")
        external_status = _extract_value(status_text, "仓库外证据状态:")
        next_review_raw = _extract_value(status_text, "下次仓库复核截止日期:")
        if repo_status != "complete":
            report.blocking_issues.append(
                ComplianceIssue(
                    code="repo_evidence_incomplete",
                    message="GBZ-04 仓库内证据状态不是 complete",
                    path=status_path,
                )
            )
        if external_status and external_status != "archived":
            report.external_gaps.append(
                ComplianceIssue(
                    code="external_supplier_qualification_records_pending",
                    message=f"线下供应商审核、环境签字或 IQ/OQ/PQ 记录仍待归档: {external_status}",
                    path=status_path,
                )
            )
        if next_review_raw:
            try:
                next_review = date.fromisoformat(next_review_raw)
            except ValueError:
                report.blocking_issues.append(
                    ComplianceIssue(
                        code="invalid_supplier_review_date",
                        message=f"无效日期格式: {next_review_raw}",
                        path=status_path,
                    )
                )
            else:
                if next_review < current_date:
                    report.blocking_issues.append(
                        ComplianceIssue(
                            code="supplier_review_overdue",
                            message="GBZ-04 仓库复核已过期",
                            path=status_path,
                        )
                    )

    service_path = root / "backend/services/supplier_qualification.py"
    if service_path.exists():
        service_text = _read_text(service_path)
        for token in (
            "supplier_component_requires_requalification",
            "tenant_company_id_required",
            "requalification_required",
            "known_issue_review",
            "migration_plan_summary",
            "QUALIFICATION_PHASE_STATUSES",
        ):
            if token not in service_text:
                report.blocking_issues.append(
                    ComplianceIssue(
                        code="supplier_service_rule_missing",
                        message=f"供应商确认服务缺少关键规则 {token}",
                        path="backend/services/supplier_qualification.py",
                    )
                )

    route_path = root / "backend/app/modules/supplier_qualification/router.py"
    if route_path.exists():
        route_text = _read_text(route_path)
        for token in (
            "/supplier-qualifications/components",
            "/supplier-qualifications/components/{component_code}/version-change",
            "/supplier-qualifications/environment-records",
            "supplier_component_version_change",
            "environment_qualification_record",
        ):
            if token not in route_text:
                report.blocking_issues.append(
                    ComplianceIssue(
                        code="supplier_route_missing",
                        message=f"供应商确认路由缺少关键能力 {token}",
                        path="backend/app/modules/supplier_qualification/router.py",
                    )
                )

    dependencies_path = root / "backend/app/dependencies.py"
    if dependencies_path.exists():
        dependencies_text = _read_text(dependencies_path)
        if "supplier_qualification_service" not in dependencies_text:
            report.blocking_issues.append(
                ComplianceIssue(
                    code="supplier_service_dependency_missing",
                    message="依赖注入未注册 supplier_qualification_service",
                    path="backend/app/dependencies.py",
                )
            )

    main_path = root / "backend/app/main.py"
    if main_path.exists():
        main_text = _read_text(main_path)
        if "supplier_qualification.router" not in main_text and "supplier_qualification.router," not in main_text:
            report.blocking_issues.append(
                ComplianceIssue(
                    code="supplier_router_not_included",
                    message="应用入口未包含 supplier_qualification 路由",
                    path="backend/app/main.py",
                )
            )

    return report
