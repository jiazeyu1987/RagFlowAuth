from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import re

from .r7_validator import ComplianceIssue
from .review_package import ComplianceReviewPackageService, REQUIRED_REVIEW_PACKAGE_GROUPS


@dataclass(slots=True)
class Fda03ComplianceReport:
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
    "doc/compliance/controlled_document_register.md": ("版本:", "更新时间:", "当前发布版本:"),
    "doc/compliance/review_package_sop.md": ("版本:", "更新时间:", "/api/audit/review-package"),
    "doc/compliance/urs.md": ("URS-012", "FDA-03"),
    "doc/compliance/srs.md": ("SRS-012", "URS-012"),
    "doc/compliance/traceability_matrix.md": ("FDA-03", "SRS-012"),
    "doc/compliance/validation_plan.md": ("validate_fda03_repo_compliance.py", "test_compliance_review_package_api_unit"),
    "doc/compliance/validation_report.md": ("FDA-03", "validate_fda03_repo_compliance.py"),
}

REQUIRED_FILES: tuple[str, ...] = (
    "backend/app/modules/audit/router.py",
    "backend/services/compliance/review_package.py",
    "backend/services/compliance/fda03_validator.py",
    "backend/tests/test_compliance_review_package_api_unit.py",
    "backend/tests/test_fda03_compliance_gate_unit.py",
    "scripts/validate_fda03_repo_compliance.py",
)

REQUIRED_PATTERNS: tuple[tuple[str, str, str], ...] = (
    (
        "doc/compliance/review_package_sop.md",
        r"/api/audit/controlled-documents",
        "审查包 SOP 未引用受控文档登记接口",
    ),
    (
        "doc/compliance/review_package_sop.md",
        r"review_package_manifest\.json",
        "审查包 SOP 缺少 review_package_manifest.json 摘要说明",
    ),
    (
        "doc/compliance/traceability_matrix.md",
        r"test_fda03_compliance_gate_unit",
        "追踪矩阵缺少 FDA-03 gate 测试映射",
    ),
)


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def validate_fda03_repo_state(repo_root: str | Path) -> Fda03ComplianceReport:
    root = Path(repo_root).resolve()
    report = Fda03ComplianceReport(checked_at=datetime.now().astimezone().isoformat(timespec="seconds"))
    docs_cache: dict[str, str] = {}

    for rel_path, keys in REQUIRED_DOCS.items():
        report.checked_files.append(rel_path)
        path = root / rel_path
        if not path.exists():
            report.blocking_issues.append(
                ComplianceIssue(code="missing_required_doc", message="缺少 FDA-03 必需受控文档", path=rel_path)
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
                ComplianceIssue(code="missing_required_artifact", message="缺少 FDA-03 必需实现或测试文件", path=rel_path)
            )

    for rel_path, pattern, message in REQUIRED_PATTERNS:
        text = docs_cache.get(rel_path, "")
        if text and re.search(pattern, text) is None:
            report.blocking_issues.append(
                ComplianceIssue(code="required_mapping_missing", message=message, path=rel_path)
            )

    try:
        service = ComplianceReviewPackageService(repo_root=root)
        documents = service.list_controlled_documents()
    except Exception as exc:
        report.blocking_issues.append(
            ComplianceIssue(
                code="controlled_document_registry_invalid",
                message=f"受控文档登记解析失败: {exc}",
                path="doc/compliance/controlled_document_register.md",
            )
        )
        documents = []

    eligible_groups: set[str] = set()
    for item in documents:
        if not item.file_exists:
            report.blocking_issues.append(
                ComplianceIssue(code="controlled_document_missing_file", message="登记文档文件不存在", path=item.path)
            )
        if item.header_version != item.version:
            report.blocking_issues.append(
                ComplianceIssue(
                    code="controlled_document_version_mismatch",
                    message="登记版本与文件头版本不一致",
                    path=item.path,
                )
            )
        if not item.header_updated_at:
            report.blocking_issues.append(
                ComplianceIssue(code="controlled_document_header_missing", message="文件缺少更新时间头信息", path=item.path)
            )
        if item.status in {"effective", "current"} and not item.release_matches:
            report.blocking_issues.append(
                ComplianceIssue(
                    code="controlled_document_release_mismatch",
                    message="现行受控文档的批准发布版本与当前系统发布版本不一致",
                    path=item.path,
                )
            )
        if item.eligible_for_review_package:
            eligible_groups.add(item.package_group)

    missing_groups = sorted(REQUIRED_REVIEW_PACKAGE_GROUPS - eligible_groups)
    if missing_groups:
        report.blocking_issues.append(
            ComplianceIssue(
                code="review_package_group_missing",
                message=f"审查包缺少必需文档分组: {', '.join(missing_groups)}",
                path="doc/compliance/controlled_document_register.md",
            )
        )

    sop = docs_cache.get("doc/compliance/review_package_sop.md", "")
    if "线下签字版批准页" in sop:
        report.external_gaps.append(
            ComplianceIssue(
                code="external_release_signoff_pending",
                message="线下签字版批准页、纸质作废回收记录和真实发布批次签核仍需在线下受控体系归档",
                path="doc/compliance/review_package_sop.md",
            )
        )

    return report
