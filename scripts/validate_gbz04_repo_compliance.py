from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.services.compliance import validate_gbz04_repo_state


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate GBZ-04 repository compliance state.")
    parser.add_argument("--root", default=str(REPO_ROOT), help="Repository root path")
    parser.add_argument("--json", action="store_true", help="Print JSON report")
    args = parser.parse_args()

    report = validate_gbz04_repo_state(args.root)
    if args.json:
        print(json.dumps(report.as_dict(), ensure_ascii=False, indent=2))
    else:
        print(f"GBZ-04 repository gate: {'PASS' if report.passed else 'FAIL'}")
        print(f"Blocking issues: {len(report.blocking_issues)}")
        print(f"External gaps: {len(report.external_gaps)}")
    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
