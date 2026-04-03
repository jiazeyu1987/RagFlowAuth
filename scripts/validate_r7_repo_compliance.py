from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.services.compliance import validate_r7_repo_state


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate repository-controlled R7/GMP compliance evidence.")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]), help="Repository root path")
    parser.add_argument("--json", action="store_true", help="Print JSON report")
    args = parser.parse_args()

    report = validate_r7_repo_state(args.root)
    if args.json:
        print(json.dumps(report.as_dict(), ensure_ascii=False, indent=2))
    else:
        print(f"R7 repository gate: {'PASS' if report.passed else 'FAIL'}")
        print(f"Checked files: {len(report.checked_files)}")
        print(f"Blocking issues: {len(report.blocking_issues)}")
        print(f"External gaps: {len(report.external_gaps)}")
        for item in report.blocking_issues:
            print(f"[BLOCK] {item.code}: {item.message} ({item.path})")
        for item in report.external_gaps:
            print(f"[INFO] {item.code}: {item.message} ({item.path})")
    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
