from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
import re
from pathlib import Path


@dataclass(slots=True)
class ComplianceIssue:
    code: str
    message: str
    path: str | None = None

    def as_dict(self) -> dict[str, str | None]:
        return {"code": self.code, "message": self.message, "path": self.path}


@dataclass(slots=True)
class R7ComplianceReport:
    checked_at: str
    blocking_issues: list[ComplianceIssue] = field(default_factory=list)
    external_gaps: list[ComplianceIssue] = field(default_factory=list)
    warnings: list[ComplianceIssue] = field(default_factory=list)
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
            "warnings": [item.as_dict() for item in self.warnings],
            "checked_files": list(self.checked_files),
        }


REQUIRED_DOCS: dict[str, tuple[str, ...]] = {
    "doc/compliance/gmp_regulatory_baseline.md": ("版本:", "更新时间:", "最新已发布 GMP 基线核对日期:", "下次基线复核截止日期:"),
    "doc/compliance/r7_periodic_review_status.md": ("版本:", "更新时间:", "最后仓库复核日期:", "下次仓库复核截止日期:", "仓库内证据状态:", "仓库外证据状态:"),
    "doc/compliance/intended_use.md": ("版本:", "更新时间:"),
    "doc/compliance/urs.md": ("版本:", "更新时间:"),
    "doc/compliance/srs.md": ("版本:", "更新时间:"),
    "doc/compliance/risk_assessment.md": ("版本:", "更新时间:"),
    "doc/compliance/traceability_matrix.md": ("版本:", "更新时间:"),
    "doc/compliance/validation_plan.md": ("版本:", "更新时间:"),
    "doc/compliance/validation_report.md": ("版本:", "更新时间:"),
}

REQUIRED_ARTIFACTS: tuple[str, ...] = (
    "backend/services/compliance/r7_validator.py",
    "backend/tests/test_r7_compliance_gate_unit.py",
    "backend/tests/test_document_versioning_unit.py",
    "backend/tests/test_config_change_log_unit.py",
    "scripts/validate_r7_repo_compliance.py",
    "fronted/e2e/tests/document.version-history.spec.js",
    "fronted/e2e/tests/admin.config-change-reason.spec.js",
)

REQUIRED_TEXT_PATTERNS: tuple[tuple[str, str, str], ...] = (
    ("doc/compliance/urs.md", r"\|\s*URS-007\s*\|\s*R7\s*\|", "R7 的 URS 映射缺失"),
    ("doc/compliance/srs.md", r"\|\s*SRS-007\s*\|\s*URS-007\s*\|", "R7 的 SRS 映射缺失"),
    ("doc/compliance/risk_assessment.md", r"\|\s*RA-010\s*\|", "R7 的风险条目 RA-010 缺失"),
    ("doc/compliance/traceability_matrix.md", r"\|\s*R7\s*\|\s*URS-007\s*\|\s*SRS-007\s*\|", "追踪矩阵中 R7 行缺失"),
    ("doc/compliance/traceability_matrix.md", r"backend/services/compliance/r7_validator\.py", "追踪矩阵未引用 R7 校验器"),
    ("doc/compliance/traceability_matrix.md", r"backend\.tests\.test_r7_compliance_gate_unit", "追踪矩阵未引用 R7 门禁测试"),
    ("doc/compliance/validation_plan.md", r"validate_r7_repo_compliance\.py", "验证计划未包含 R7 门禁命令"),
    ("doc/compliance/validation_report.md", r"仓库内门禁校验", "验证报告未记录 R7 门禁结论"),
    ("doc/compliance/validation_report.md", r"不替代线下签字", "验证报告未保留仓库外证据边界说明"),
)


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _extract_value(text: str, label: str) -> str | None:
    pattern = rf"(?m)^{re.escape(label)}\s*(.+?)\s*$"
    match = re.search(pattern, text)
    if not match:
        return None
    return match.group(1).strip()


def _parse_iso_date(value: str, *, code: str, report: R7ComplianceReport, path: str) -> date | None:
    try:
        return date.fromisoformat(value)
    except ValueError:
        report.blocking_issues.append(
            ComplianceIssue(code=code, message=f"无效日期格式: {value}", path=path)
        )
        return None


def validate_r7_repo_state(repo_root: str | Path, *, as_of: date | None = None) -> R7ComplianceReport:
    root = Path(repo_root).resolve()
    current_date = as_of or date.today()
    report = R7ComplianceReport(
        checked_at=datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    )

    docs_cache: dict[str, str] = {}

    for rel_path, metadata_keys in REQUIRED_DOCS.items():
        path = root / rel_path
        report.checked_files.append(rel_path)
        if not path.exists():
            report.blocking_issues.append(
                ComplianceIssue(code="missing_required_doc", message="缺少 R7 必需受控文档", path=rel_path)
            )
            continue
        text = _read_text(path)
        docs_cache[rel_path] = text
        for key in metadata_keys:
            if _extract_value(text, key) is None:
                report.blocking_issues.append(
                    ComplianceIssue(code="missing_doc_metadata", message=f"文档缺少元数据字段 {key}", path=rel_path)
                )

    for rel_path in REQUIRED_ARTIFACTS:
        path = root / rel_path
        report.checked_files.append(rel_path)
        if not path.exists():
            report.blocking_issues.append(
                ComplianceIssue(code="missing_required_artifact", message="缺少 R7 必需实现或测试文件", path=rel_path)
            )

    baseline_path = "doc/compliance/gmp_regulatory_baseline.md"
    baseline_text = docs_cache.get(baseline_path, "")
    if baseline_text:
        for token in ("国家药监局令第64号", "2025-11-04", "2026-11-01", "latest_published_pending_effective"):
            if token not in baseline_text:
                report.blocking_issues.append(
                    ComplianceIssue(code="baseline_token_missing", message=f"GMP 基线缺少关键标记 {token}", path=baseline_path)
                )
        next_review_raw = _extract_value(baseline_text, "下次基线复核截止日期:")
        if next_review_raw:
            next_review = _parse_iso_date(next_review_raw, code="invalid_baseline_review_date", report=report, path=baseline_path)
            if next_review and next_review < current_date:
                report.blocking_issues.append(
                    ComplianceIssue(code="baseline_review_overdue", message="GMP 基线复核已过期", path=baseline_path)
                )

    review_path = "doc/compliance/r7_periodic_review_status.md"
    review_text = docs_cache.get(review_path, "")
    if review_text:
        repo_status = _extract_value(review_text, "仓库内证据状态:")
        external_status = _extract_value(review_text, "仓库外证据状态:")
        next_review_raw = _extract_value(review_text, "下次仓库复核截止日期:")
        if repo_status != "complete":
            report.blocking_issues.append(
                ComplianceIssue(code="repo_evidence_incomplete", message="R7 仓库内证据状态不是 complete", path=review_path)
            )
        if external_status and external_status != "archived":
            report.external_gaps.append(
                ComplianceIssue(code="external_evidence_pending", message=f"仓库外执行证据仍待补齐: {external_status}", path=review_path)
            )
        if next_review_raw:
            next_review = _parse_iso_date(next_review_raw, code="invalid_periodic_review_date", report=report, path=review_path)
            if next_review and next_review < current_date:
                report.blocking_issues.append(
                    ComplianceIssue(code="periodic_review_overdue", message="R7 周期复核状态已过期", path=review_path)
                )

    for rel_path, pattern, message in REQUIRED_TEXT_PATTERNS:
        text = docs_cache.get(rel_path, "")
        if text and re.search(pattern, text, flags=re.MULTILINE) is None:
            report.blocking_issues.append(
                ComplianceIssue(code="required_mapping_missing", message=message, path=rel_path)
            )

    return report
