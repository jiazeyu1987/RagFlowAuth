from __future__ import annotations

import argparse
from pathlib import Path
import sys


DEFAULT_TASK_DIR = Path("docs/tasks/iso-13485-20260413T153016")
REQUIRED_TASK_FILES = (
    "prd.md",
    "test-plan.md",
    "execution-log.md",
    "test-report.md",
    "task-state.json",
)
REQUIRED_COMPLIANCE_FILES = (
    "approval_workflow_sop.md",
    "controlled_document_register.md",
    "electronic_signature_policy.md",
    "gmp_regulatory_baseline.md",
    "inspection_evidence_export_sop.md",
    "intended_use.md",
    "maintenance_plan.md",
    "maintenance_review_status.md",
    "r7_periodic_review_status.md",
    "release_and_retirement_sop.md",
    "retirement_archive_status.md",
    "retirement_plan.md",
    "review_package_sop.md",
    "risk_assessment.md",
    "signature_authorization_matrix.md",
    "srs.md",
    "traceability_matrix.md",
    "training_matrix.md",
    "training_operator_qualification_status.md",
    "urs.md",
    "validation_plan.md",
    "validation_report.md",
)
STALE_PRD_MARKERS = (
    "仍硬编码引用 `doc/compliance/*`",
    "`docs/` 与 `doc/compliance/*` 发生断裂",
)


def collect_missing_files(base_dir: Path, relative_paths: tuple[str, ...]) -> list[str]:
    missing: list[str] = []
    for relative_path in relative_paths:
        if not (base_dir / relative_path).exists():
            missing.append(str(base_dir / relative_path))
    return missing


def validate_prd(task_dir: Path) -> list[str]:
    errors: list[str] = []
    prd_path = task_dir / "prd.md"
    if not prd_path.exists():
        return [f"missing required file: {prd_path}"]
    prd_text = prd_path.read_text(encoding="utf-8")
    for marker in STALE_PRD_MARKERS:
        if marker in prd_text:
            errors.append(f"stale PRD assertion still present: {marker}")
    if "docs/compliance/" not in prd_text:
        errors.append("PRD does not mention docs/compliance/ as the controlled compliance root")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate ISO-13485 task artifacts and controlled compliance docs.")
    parser.add_argument("--task-dir", default=str(DEFAULT_TASK_DIR), help="Task artifact directory")
    parser.add_argument("--repo-root", default=".", help="Repository root")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    task_dir = (repo_root / args.task_dir).resolve()
    compliance_dir = repo_root / "docs/compliance"

    errors: list[str] = []
    errors.extend(collect_missing_files(task_dir, REQUIRED_TASK_FILES))
    errors.extend(collect_missing_files(compliance_dir, REQUIRED_COMPLIANCE_FILES))
    errors.extend(validate_prd(task_dir))

    if errors:
        print("artifact validation: FAIL")
        for error in errors:
            print(f"- {error}")
        return 1

    print("artifact validation: PASS")
    print(f"- task dir: {task_dir}")
    print(f"- compliance dir: {compliance_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
