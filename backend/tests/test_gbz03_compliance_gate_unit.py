from __future__ import annotations

from datetime import date
from pathlib import Path
import unittest

from backend.services.compliance import validate_gbz03_repo_state
from backend.tests._util_tempdir import cleanup_dir, make_temp_dir


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _build_repo(root: Path) -> None:
    docs = {
        "doc/compliance/release_and_retirement_sop.md": """# 发布与退役 SOP

版本: v1.0
更新时间: 2026-04-03

/api/knowledge/documents/{doc_id}/retire
/api/knowledge/retired-documents
/api/audit/retired-records
/api/audit/retired-records/{doc_id}/package
retirement_manifest.json
checksums.json
""",
        "doc/compliance/retirement_plan.md": """# 退役计划

版本: v1.0
更新时间: 2026-04-03
当前发布版本: 2.0.0
退役对象范围: 已批准且需要长期归档保留的知识文档版本
保留期映射: SOP/记录最短保留 5 年，发布批次记录按法规保留
归档包校验: 对 ZIP 包和 manifest 执行 SHA-256 复核
仓库外残余项: 线下签字版批准页、介质保管记录、纸质作废回收记录仍需线下归档
""",
        "doc/compliance/retirement_archive_status.md": """# 退役归档状态

版本: v1.0
更新时间: 2026-04-03
最后仓库复核日期: 2026-04-03
下次仓库复核截止日期: 2026-10-03
仓库内证据状态: complete
仓库外证据状态: pending_archive
Residual gap 边界: 线下签字版批准页、介质保管记录和作废回收单不在仓库内伪造
""",
        "doc/compliance/controlled_document_register.md": """# 受控文档登记表

版本: v1.0
更新时间: 2026-04-03
当前发布版本: 2.0.0

doc/compliance/retirement_plan.md
doc/compliance/retirement_archive_status.md
""",
        "doc/compliance/urs.md": "# URS\n\nURS-015 GBZ-03\n",
        "doc/compliance/srs.md": "# SRS\n\nSRS-015 URS-015\n",
        "doc/compliance/traceability_matrix.md": """# TM

| 需求 ID | URS | SRS | 实现证据 | 测试证据 | 文档证据 | 状态 |
|---|---|---|---|---|---|---|
| GBZ-03 | URS-015 | SRS-015 | `backend/services/compliance/retired_records.py`, `backend/app/modules/knowledge/routes/retired.py`, `backend/app/modules/audit/router.py` | `backend.tests.test_retired_document_access_unit`, `backend.tests.test_gbz03_compliance_gate_unit`, `python scripts/validate_gbz03_repo_compliance.py` | `doc/compliance/release_and_retirement_sop.md`, `doc/compliance/retirement_plan.md`, `doc/compliance/retirement_archive_status.md` | 已验证（仓库内） |
""",
        "doc/compliance/validation_plan.md": """# VP

validate_gbz03_repo_compliance.py
test_retired_document_access_unit
test_gbz03_compliance_gate_unit
""",
        "doc/compliance/validation_report.md": """# VR

GBZ-03
validate_gbz03_repo_compliance.py
external_retirement_archive_records_pending
""",
    }
    for rel_path, content in docs.items():
        _write(root / rel_path, content)

    _write(
        root / "backend/services/compliance/retired_records.py",
        "\n".join(
            [
                "retirement_manifest.json",
                "checksums.json",
                "document_already_retired",
                "only_approved_document_can_be_retired",
                "retention_until_must_be_future",
                "archive_package_sha256_mismatch",
                "\"schema_version\": \"gbz03.v1\"",
                "",
            ]
        ),
    )
    _write(root / "backend/services/compliance/gbz03_validator.py", "# validator placeholder\n")
    _write(
        root / "backend/app/modules/knowledge/routes/retired.py",
        "\n".join(
            [
                "@router.post(\"/documents/{doc_id}/retire\")",
                "@router.get(\"/retired-documents\")",
                "@router.get(\"/retired-documents/{doc_id}/download\")",
                "@router.get(\"/retired-documents/{doc_id}/preview\")",
                "RetiredRecordsService",
                "action=\"document_retire\"",
                "",
            ]
        ),
    )
    _write(
        root / "backend/app/modules/knowledge/router.py",
        "\n".join(
            [
                "from fastapi import APIRouter",
                "router = APIRouter()",
                "from .routes.retired import router as retired_router",
                "router.include_router(retired_router)",
                "",
            ]
        ),
    )
    _write(
        root / "backend/app/modules/audit/router.py",
        "\n".join(
            [
                "@router.get(\"/audit/retired-records\")",
                "@router.get(\"/audit/retired-records/{doc_id}/package\")",
                "retired_record_package_export",
                "",
            ]
        ),
    )
    _write(root / "backend/tests/test_retired_document_access_unit.py", "# placeholder\n")
    _write(root / "backend/tests/test_gbz03_compliance_gate_unit.py", "# placeholder\n")
    _write(root / "scripts/validate_gbz03_repo_compliance.py", "# placeholder\n")


class TestGbz03ComplianceGateUnit(unittest.TestCase):
    def test_repo_gate_passes_with_external_gap_only(self):
        tmp = make_temp_dir(prefix="ragflowauth_gbz03_gate_pass")
        try:
            root = Path(tmp)
            _build_repo(root)
            report = validate_gbz03_repo_state(root, as_of=date(2026, 4, 3))
            self.assertTrue(report.passed)
            self.assertEqual(report.blocking_issues, [])
            self.assertEqual(
                [item.code for item in report.external_gaps],
                ["external_retirement_archive_records_pending"],
            )
        finally:
            cleanup_dir(tmp)

    def test_repo_gate_flags_duplicate_retired_router_registration(self):
        tmp = make_temp_dir(prefix="ragflowauth_gbz03_gate_fail")
        try:
            root = Path(tmp)
            _build_repo(root)
            _write(
                root / "backend/app/modules/knowledge/router.py",
                "\n".join(
                    [
                        "from fastapi import APIRouter",
                        "router = APIRouter()",
                        "from .routes.retired import router as retired_router",
                        "router.include_router(retired_router)",
                        "router.include_router(retired_router)",
                        "",
                    ]
                ),
            )
            report = validate_gbz03_repo_state(root, as_of=date(2026, 4, 3))
            self.assertFalse(report.passed)
            self.assertTrue(
                any(item.code == "retired_router_registration_invalid" for item in report.blocking_issues)
            )
        finally:
            cleanup_dir(tmp)


if __name__ == "__main__":
    unittest.main()
