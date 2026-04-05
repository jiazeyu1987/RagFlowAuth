from __future__ import annotations

import argparse
import json
import sys

from backend.services.data_reconcile import DataReconcileService


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Audit and safely reconcile managed RagflowAuth data paths.",
    )
    parser.add_argument(
        "mode",
        choices=("report", "apply"),
        help="report only prints drift and cleanup actions; apply executes safe rewrites/deletes.",
    )
    parser.add_argument(
        "--db",
        dest="db_path",
        default=None,
        help="Optional auth DB path. Defaults to backend settings DATABASE_PATH.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    service = DataReconcileService(db_path=args.db_path)
    payload = service.report().to_dict() if args.mode == "report" else service.apply()
    sys.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
