from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
import re

from .r7_validator import ComplianceIssue


@dataclass(slots=True)
class Gbz03ComplianceReport:
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
    "doc/compliance/release_and_retirement_sop.md": (
        "版本:",
        "更新时间:",
        "/api/knowledge/documents/{doc_id}/retire",
        "/api/knowledge/retired-documents",
        "/api/audit/retired-records/{doc_id}/package",
        "retirement_manifest.json",
        "checksums.json",
    ),
    "doc/compliance/retirement_plan.md": (
        "版本:",
        "更新时间:",
        "当前发布版本:",
        "退役对象范围:",
        "保留期映射:",
        "归档包校验:",
        "仓库外残余项:",
    ),
    "doc/compliance/retirement_archive_status.md": (
        "版本:",
        "更新时间:",
        "最后仓库复核日期:",
        "下次仓库复核截止日期:",
        "仓库内证据状态:",
        "仓库外证据状态:",
        "Residual gap 边界:",
    ),
    "doc/compliance/controlled_document_register.md": (
        "doc/compliance/retirement_plan.md",
        "doc/compliance/retirement_archive_status.md",
    ),
    "doc/compliance/urs.md": ("URS-015", "GBZ-03"),
    "doc/compliance/srs.md": ("SRS-015", "URS-015"),
    "doc/compliance/traceability_matrix.md": ("GBZ-03", "SRS-015"),
    "doc/compliance/validation_plan.md": (
        "validate_gbz03_repo_compliance.py",
        "test_retired_document_access_unit",
        "test_gbz03_compliance_gate_unit",
    ),
    "doc/compliance/validation_report.md": (
        "GBZ-03",
        "validate_gbz03_repo_compliance.py",
        "external_retirement_archive_records_pending",
    ),
}

REQUIRED_FILES: tuple[str, ...] = (
    "backend/services/compliance/retired_records.py",
    "backend/services/compliance/gbz03_validator.py",
    "backend/app/modules/knowledge/routes/retired.py",
    "backend/app/modules/knowledge/router.py",
    "backend/app/modules/audit/router.py",
    "backend/tests/test_retired_document_access_unit.py",
    "backend/tests/test_gbz03_compliance_gate_unit.py",
    "scripts/validate_gbz03_repo_compliance.py",
)

REQUIRED_PATTERNS: tuple[tuple[str, str, str], ...] = (
    (
        "doc/compliance/traceability_matrix.md",
        r"\|\s*GBZ-03\s*\|\s*URS-015\s*\|\s*SRS-015\s*\|",
        "追踪矩阵缺少 GBZ-03 映射",
    ),
    (
        "doc/compliance/traceability_matrix.md",
        r"backend/services/compliance/retired_records\.py",
        "追踪矩阵缺少退役记录实现映射",
    ),
    (
        "doc/compliance/traceability_matrix.md",
        r"backend\.tests\.test_retired_document_access_unit",
        "追踪矩阵缺少退役记录测试映射",
    ),
    (
        "doc/compliance/release_and_retirement_sop.md",
        r"/api/audit/retired-records\b",
        "发布与退役 SOP 缺少退役记录审计检索路径",
    ),
)


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _extract_value(text: str, label: str) -> str | None:
    match = re.search(rf"(?m)^{re.escape(label)}\s*(.+?)\s*$", text)
    if not match:
        return None
    return match.group(1).strip()


def validate_gbz03_repo_state(repo_root: str | Path, *, as_of: date | None = None) -> Gbz03ComplianceReport:
    root = Path(repo_root).resolve()
    current_date = as_of or date.today()
    report = Gbz03ComplianceReport(
        checked_at=datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    )
    docs_cache: dict[str, str] = {}

    for rel_path, keys in REQUIRED_DOCS.items():
        path = root / rel_path
        report.checked_files.append(rel_path)
        if not path.exists():
            report.blocking_issues.append(
                ComplianceIssue(code="missing_required_doc", message="缺少 GBZ-03 必需受控文档", path=rel_path)
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
                ComplianceIssue(code="missing_required_artifact", message="缺少 GBZ-03 必需实现或测试文件", path=rel_path)
            )

    for rel_path, pattern, message in REQUIRED_PATTERNS:
        text = docs_cache.get(rel_path, "")
        if text and re.search(pattern, text) is None:
            report.blocking_issues.append(
                ComplianceIssue(code="required_mapping_missing", message=message, path=rel_path)
            )

    status_path = "doc/compliance/retirement_archive_status.md"
    status_text = docs_cache.get(status_path, "")
    if status_text:
        repo_status = _extract_value(status_text, "仓库内证据状态:")
        external_status = _extract_value(status_text, "仓库外证据状态:")
        next_review_raw = _extract_value(status_text, "下次仓库复核截止日期:")
        if repo_status != "complete":
            report.blocking_issues.append(
                ComplianceIssue(
                    code="repo_evidence_incomplete",
                    message="GBZ-03 仓库内证据状态不是 complete",
                    path=status_path,
                )
            )
        if external_status and external_status != "archived":
            report.external_gaps.append(
                ComplianceIssue(
                    code="external_retirement_archive_records_pending",
                    message=f"线下退役签字、介质保管或作废回收证据仍待归档: {external_status}",
                    path=status_path,
                )
            )
        if next_review_raw:
            try:
                next_review = date.fromisoformat(next_review_raw)
            except ValueError:
                report.blocking_issues.append(
                    ComplianceIssue(
                        code="invalid_retirement_review_date",
                        message=f"无效日期格式: {next_review_raw}",
                        path=status_path,
                    )
                )
            else:
                if next_review < current_date:
                    report.blocking_issues.append(
                        ComplianceIssue(
                            code="retirement_review_overdue",
                            message="GBZ-03 仓库复核已过期",
                            path=status_path,
                        )
                    )

    service_path = root / "backend/services/compliance/retired_records.py"
    if service_path.exists():
        service_text = _read_text(service_path)
        required_tokens = (
            "retirement_manifest.json",
            "checksums.json",
            "document_already_retired",
            "only_approved_document_can_be_retired",
            "retention_until_must_be_future",
            "archive_package_sha256_mismatch",
            "\"schema_version\": \"gbz03.v1\"",
        )
        for token in required_tokens:
            if token not in service_text:
                report.blocking_issues.append(
                    ComplianceIssue(
                        code="retired_record_rule_missing",
                        message=f"退役记录服务缺少关键规则 {token}",
                        path="backend/services/compliance/retired_records.py",
                    )
                )

    route_path = root / "backend/app/modules/knowledge/routes/retired.py"
    if route_path.exists():
        route_text = _read_text(route_path)
        for token in (
            "/documents/{doc_id}/retire",
            "/retired-documents",
            "/retired-documents/{doc_id}/download",
            "/retired-documents/{doc_id}/preview",
            "action=\"document_retire\"",
            "RetiredRecordsService",
        ):
            if token not in route_text:
                report.blocking_issues.append(
                    ComplianceIssue(
                        code="retired_route_missing",
                        message=f"退役路由缺少关键能力 {token}",
                        path="backend/app/modules/knowledge/routes/retired.py",
                    )
                )

    audit_route_path = root / "backend/app/modules/audit/router.py"
    if audit_route_path.exists():
        audit_text = _read_text(audit_route_path)
        for token in (
            "/audit/retired-records",
            "/audit/retired-records/{doc_id}/package",
            "retired_record_package_export",
        ):
            if token not in audit_text:
                report.blocking_issues.append(
                    ComplianceIssue(
                        code="retired_audit_route_missing",
                        message=f"审计路由缺少退役记录能力 {token}",
                        path="backend/app/modules/audit/router.py",
                    )
                )

    knowledge_router_path = root / "backend/app/modules/knowledge/router.py"
    if knowledge_router_path.exists():
        router_text = _read_text(knowledge_router_path)
        import_token = "from .routes.retired import router as retired_router"
        if import_token not in router_text:
            report.blocking_issues.append(
                ComplianceIssue(
                    code="knowledge_retired_router_missing",
                    message="knowledge router 未导入 retired_router",
                    path="backend/app/modules/knowledge/router.py",
                )
            )
        include_count = router_text.count("router.include_router(retired_router)")
        if include_count != 1:
            report.blocking_issues.append(
                ComplianceIssue(
                    code="retired_router_registration_invalid",
                    message=f"retired_router 注册次数应为 1，当前为 {include_count}",
                    path="backend/app/modules/knowledge/router.py",
                )
            )

    return report
