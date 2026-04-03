from __future__ import annotations

from pathlib import Path
import unittest

from backend.services.compliance import validate_fda03_repo_state
from backend.tests._util_tempdir import cleanup_dir, make_temp_dir


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _build_repo(root: Path) -> None:
    docs = {
        "doc/compliance/urs.md": "# URS\n\n鐗堟湰: v1.0\n鏇存柊鏃堕棿: 2026-04-03\n\nURS-012 FDA-03\n",
        "doc/compliance/srs.md": "# SRS\n\n鐗堟湰: v1.0\n鏇存柊鏃堕棿: 2026-04-03\n\nSRS-012 URS-012\n",
        "doc/compliance/traceability_matrix.md": (
            "# Matrix\n\n鐗堟湰: v1.0\n鏇存柊鏃堕棿: 2026-04-03\n\n"
            "FDA-03 SRS-012 test_fda03_compliance_gate_unit\n"
        ),
        "doc/compliance/validation_plan.md": (
            "# Plan\n\n鐗堟湰: v1.0\n鏇存柊鏃堕棿: 2026-04-03\n\n"
            "validate_fda03_repo_compliance.py\n"
            "test_compliance_review_package_api_unit\n"
        ),
        "doc/compliance/validation_report.md": (
            "# Report\n\n鐗堟湰: v1.0\n鏇存柊鏃堕棿: 2026-04-03\n\n"
            "FDA-03\nvalidate_fda03_repo_compliance.py\n"
        ),
        "doc/compliance/review_package_sop.md": (
            "# Review Package SOP\n\n鐗堟湰: v1.0\n鏇存柊鏃堕棿: 2026-04-03\n"
            "/api/audit/controlled-documents\n"
            "/api/audit/review-package\n"
            "review_package_manifest.json\n"
            "绾夸笅绛惧瓧鐗堟壒鍑嗛〉\n"
        ),
        "doc/compliance/approval_workflow_sop.md": "# SOP\n\n鐗堟湰: v1.1\n鏇存柊鏃堕棿: 2026-04-03\n",
        "doc/compliance/electronic_signature_policy.md": "# Policy\n\n鐗堟湰: v1.1\n鏇存柊鏃堕棿: 2026-04-03\n",
        "doc/compliance/backup_restore_sop.md": "# Backup SOP\n\n鐗堟湰: v1.1\n鏇存柊鏃堕棿: 2026-04-03\n",
        "doc/compliance/release_and_retirement_sop.md": "# Release SOP\n\n鐗堟湰: v1.0\n鏇存柊鏃堕棿: 2026-04-03\n",
    }
    for rel_path, content in docs.items():
        _write(root / rel_path, content)

    _write(
        root / "doc/compliance/controlled_document_register.md",
        """# Register

鐗堟湰: v1.0
鏇存柊鏃堕棿: 2026-04-03
褰撳墠鍙戝竷鐗堟湰: 2.0.0

| doc_code | title | file_path | version | status | effective_date | review_due_date | approved_release_version | package_group |
|---|---|---|---|---|---|---|---|---|
| CD-001 | URS | doc/compliance/urs.md | v1.0 | effective | 2026-04-03 | 2026-10-03 | 2.0.0 | requirements |
| CD-002 | SRS | doc/compliance/srs.md | v1.0 | effective | 2026-04-03 | 2026-10-03 | 2.0.0 | requirements |
| CD-003 | Traceability | doc/compliance/traceability_matrix.md | v1.0 | effective | 2026-04-03 | 2026-10-03 | 2.0.0 | validation |
| CD-004 | Validation Plan | doc/compliance/validation_plan.md | v1.0 | effective | 2026-04-03 | 2026-10-03 | 2.0.0 | validation |
| CD-005 | Validation Report | doc/compliance/validation_report.md | v1.0 | effective | 2026-04-03 | 2026-10-03 | 2.0.0 | validation |
| CD-006 | Release SOP | doc/compliance/release_and_retirement_sop.md | v1.0 | effective | 2026-04-03 | 2026-10-03 | 2.0.0 | sop |
| CD-007 | Approval Workflow SOP | doc/compliance/approval_workflow_sop.md | v1.1 | effective | 2026-04-03 | 2026-10-03 | 2.0.0 | sop |
| CD-008 | E-Signature Policy | doc/compliance/electronic_signature_policy.md | v1.1 | effective | 2026-04-03 | 2026-10-03 | 2.0.0 | sop |
| CD-009 | Backup Restore SOP | doc/compliance/backup_restore_sop.md | v1.1 | effective | 2026-04-03 | 2026-10-03 | 2.0.0 | sop |
| CD-010 | Review Package SOP | doc/compliance/review_package_sop.md | v1.0 | effective | 2026-04-03 | 2026-10-03 | 2.0.0 | package |
""",
    )

    for rel_path in (
        "backend/app/modules/audit/router.py",
        "backend/services/compliance/review_package.py",
        "backend/services/compliance/fda03_validator.py",
        "backend/tests/test_compliance_review_package_api_unit.py",
        "backend/tests/test_fda03_compliance_gate_unit.py",
        "scripts/validate_fda03_repo_compliance.py",
    ):
        _write(root / rel_path, "# placeholder\n")


class TestFda03ComplianceGateUnit(unittest.TestCase):
    def test_repo_gate_passes_with_external_gap_only(self):
        report = validate_fda03_repo_state(Path(__file__).resolve().parents[2])
        self.assertTrue(report.passed)
        self.assertEqual(report.blocking_issues, [])
        self.assertGreaterEqual(len(report.external_gaps), 1)

    def test_repo_gate_flags_missing_traceability_mapping(self):
        tmp = make_temp_dir(prefix="ragflowauth_fda03_gate")
        try:
            root = Path(tmp)
            _build_repo(root)
            (root / "doc/compliance/traceability_matrix.md").write_text(
                "# Matrix\n\n鐗堟湰: v1.0\n鏇存柊鏃堕棿: 2026-04-03\n\nFDA-03 SRS-012\n",
                encoding="utf-8",
            )
            report = validate_fda03_repo_state(root)
            self.assertFalse(report.passed)
            self.assertTrue(any(item.code == "required_mapping_missing" for item in report.blocking_issues))
        finally:
            cleanup_dir(tmp)


if __name__ == "__main__":
    unittest.main()
