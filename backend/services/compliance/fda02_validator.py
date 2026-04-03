from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import re

from .r7_validator import ComplianceIssue


@dataclass(slots=True)
class Fda02ComplianceReport:
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
    "doc/compliance/inspection_evidence_export_sop.md": (
        "版本:",
        "更新时间:",
        "人可读副本:",
        "便携格式:",
        "仓库外残余项:",
    ),
    "doc/compliance/urs.md": ("URS-011", "FDA-02"),
    "doc/compliance/srs.md": ("SRS-011", "URS-011"),
    "doc/compliance/traceability_matrix.md": ("FDA-02", "SRS-011"),
}

REQUIRED_FILES: tuple[str, ...] = (
    "backend/app/modules/audit/router.py",
    "backend/services/audit/evidence_export.py",
    "backend/tests/test_audit_evidence_export_api_unit.py",
    "backend/tests/test_fda02_compliance_gate_unit.py",
    "scripts/validate_fda02_repo_compliance.py",
)

REQUIRED_PATTERNS: tuple[tuple[str, str, str], ...] = (
    (
        "doc/compliance/inspection_evidence_export_sop.md",
        r"manifest\.json",
        "检查取证 SOP 缺少 manifest.json 完整性摘要说明",
    ),
    (
        "doc/compliance/inspection_evidence_export_sop.md",
        r"checksums\.json",
        "检查取证 SOP 缺少 checksums.json 完整性摘要说明",
    ),
    (
        "doc/compliance/inspection_evidence_export_sop.md",
        r"/api/audit/evidence-export",
        "检查取证 SOP 未引用受控导出接口",
    ),
    (
        "doc/compliance/traceability_matrix.md",
        r"test_audit_evidence_export_api_unit",
        "追踪矩阵缺少 FDA-02 自动化测试映射",
    ),
)


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def validate_fda02_repo_state(repo_root: str | Path) -> Fda02ComplianceReport:
    root = Path(repo_root).resolve()
    report = Fda02ComplianceReport(checked_at=datetime.now().astimezone().isoformat(timespec="seconds"))
    docs_cache: dict[str, str] = {}

    for rel_path, keys in REQUIRED_DOCS.items():
        report.checked_files.append(rel_path)
        path = root / rel_path
        if not path.exists():
            report.blocking_issues.append(
                ComplianceIssue(code="missing_required_doc", message="缺少 FDA-02 必需受控文档", path=rel_path)
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
                ComplianceIssue(code="missing_required_artifact", message="缺少 FDA-02 必需实现或测试文件", path=rel_path)
            )

    for rel_path, pattern, message in REQUIRED_PATTERNS:
        text = docs_cache.get(rel_path, "")
        if text and re.search(pattern, text) is None:
            report.blocking_issues.append(
                ComplianceIssue(code="required_mapping_missing", message=message, path=rel_path)
            )

    sop = docs_cache.get("doc/compliance/inspection_evidence_export_sop.md", "")
    if "线下交付签收" in sop:
        report.external_gaps.append(
            ComplianceIssue(
                code="external_chain_of_custody_pending",
                message="线下导出介质交付签收或检查员取证链路记录仍需在线下受控体系归档",
                path="doc/compliance/inspection_evidence_export_sop.md",
            )
        )

    return report
