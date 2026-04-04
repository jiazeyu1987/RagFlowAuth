from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import re
from pathlib import Path

from .r7_validator import ComplianceIssue


@dataclass(slots=True)
class Fda01ComplianceReport:
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
    "doc/compliance/electronic_signature_policy.md": ("版本:", "更新时间:", "账号唯一性声明:", "仓库外残余项:"),
    "doc/compliance/signature_authorization_matrix.md": ("版本:", "更新时间:"),
    "doc/compliance/approval_workflow_sop.md": ("版本:", "更新时间:"),
}

REQUIRED_FILES: tuple[str, ...] = (
    "backend/app/modules/operation_approvals/router.py",
    "backend/services/operation_approval/service.py",
    "backend/services/operation_approval/handlers.py",
    "backend/services/electronic_signature/service.py",
    "backend/tests/test_operation_approval_service_unit.py",
    "backend/tests/test_electronic_signature_unit.py",
    "backend/tests/test_fda01_compliance_gate_unit.py",
    "scripts/validate_fda01_repo_compliance.py",
)

REQUIRED_PATTERNS: tuple[tuple[str, str, str], ...] = (
    ("doc/compliance/signature_authorization_matrix.md", r"operation_request_not_current_approver", "责任矩阵未引用当前步骤授权校验"),
    ("doc/compliance/signature_authorization_matrix.md", r"signature_user_disabled", "责任矩阵未引用停权签名阻断"),
    ("doc/compliance/electronic_signature_policy.md", r"账号不得共用", "电子签名策略缺少账号唯一性/禁共用声明"),
    ("doc/compliance/electronic_signature_policy.md", r"仓库外残余项", "电子签名策略缺少仓库外残余项说明"),
    ("doc/compliance/electronic_signature_policy.md", r"当前步骤被授权审批人", "电子签名策略缺少授权审批人与签名绑定说明"),
)


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def validate_fda01_repo_state(repo_root: str | Path) -> Fda01ComplianceReport:
    root = Path(repo_root).resolve()
    report = Fda01ComplianceReport(checked_at=datetime.now().astimezone().isoformat(timespec="seconds"))
    docs_cache: dict[str, str] = {}

    for rel_path, keys in REQUIRED_DOCS.items():
        report.checked_files.append(rel_path)
        path = root / rel_path
        if not path.exists():
            report.blocking_issues.append(
                ComplianceIssue(code="missing_required_doc", message="缺少 FDA-01 必需受控文档", path=rel_path)
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
                ComplianceIssue(code="missing_required_artifact", message="缺少 FDA-01 必需实现或测试文件", path=rel_path)
            )

    for rel_path, pattern, message in REQUIRED_PATTERNS:
        text = docs_cache.get(rel_path, "")
        if text and re.search(pattern, text) is None:
            report.blocking_issues.append(
                ComplianceIssue(code="required_mapping_missing", message=message, path=rel_path)
            )

    policy = docs_cache.get("doc/compliance/electronic_signature_policy.md", "")
    if "线下离岗/转岗签名权限回收记录" in policy:
        report.external_gaps.append(
            ComplianceIssue(
                code="external_revocation_records_pending",
                message="线下离岗/转岗签名权限回收记录仍需在线下体系归档",
                path="doc/compliance/electronic_signature_policy.md",
            )
        )

    return report
