#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

# Ensure repository root is importable when executing directly.
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.database.schema.ensure import ensure_schema
from backend.services.egress_policy_engine import EgressPolicyEngine
from backend.services.egress_policy_store import EgressPolicyStore

DEFAULT_FALSE_ALLOW_THRESHOLD = 0.10
DEFAULT_FALSE_BLOCK_THRESHOLD = 0.10


@dataclass(frozen=True)
class BenchCase:
    case_id: str
    expected: str  # allow|block
    payload: dict[str, Any]
    notes: str


def _default_cases() -> list[BenchCase]:
    return [
        BenchCase(
            case_id="high_sensitive_should_block",
            expected="block",
            payload={"model": "qwen-plus", "question": "contains secret project details"},
            notes="high-sensitive keyword hit",
        ),
        BenchCase(
            case_id="non_whitelist_model_should_block",
            expected="block",
            payload={"model": "gpt-4", "question": "normal question"},
            notes="model outside domestic allowlist",
        ),
        BenchCase(
            case_id="whitelist_model_should_allow",
            expected="allow",
            payload={"model": "qwen-plus", "question": "normal question"},
            notes="domestic allowlist hit",
        ),
        BenchCase(
            case_id="masked_but_allow",
            expected="allow",
            payload={"model": "qwen-plus", "question": "this is internal reference"},
            notes="medium-sensitive should be masked but not blocked",
        ),
    ]


def _configure_policy(*, db_path: Path) -> None:
    store = EgressPolicyStore(db_path=str(db_path))
    store.update(
        {
            "mode": "extranet",
            "minimal_egress_enabled": True,
            "sensitive_classification_enabled": True,
            "auto_desensitize_enabled": True,
            "high_sensitive_block_enabled": True,
            "domestic_model_whitelist_enabled": True,
            "domestic_model_allowlist": ["qwen-plus", "glm-4-plus"],
            "sensitivity_rules": {
                "low": ["public"],
                "medium": ["internal"],
                "high": ["secret", "confidential"],
            },
        },
        actor_user_id="bench_runner",
    )


def _run_bench(
    *,
    db_path: Path,
    false_allow_threshold: float,
    false_block_threshold: float,
) -> dict[str, Any]:
    ensure_schema(str(db_path))
    _configure_policy(db_path=db_path)
    engine = EgressPolicyEngine(db_path=str(db_path))
    cases = _default_cases()

    rows: list[dict[str, Any]] = []
    expected_block_total = 0
    expected_allow_total = 0
    false_allow_count = 0
    false_block_count = 0

    for case in cases:
        decision = engine.evaluate_payload(case.payload)
        actual = "allow" if decision.allowed else "block"

        if case.expected == "block":
            expected_block_total += 1
            if actual == "allow":
                false_allow_count += 1
        else:
            expected_allow_total += 1
            if actual == "block":
                false_block_count += 1

        rows.append(
            {
                "case_id": case.case_id,
                "expected": case.expected,
                "actual": actual,
                "pass": bool(case.expected == actual),
                "blocked_reason": decision.blocked_reason,
                "payload_level": decision.payload_level,
                "target_model": decision.target_model,
                "masked": decision.masked,
                "hit_rule_count": len(decision.hit_rules),
                "notes": case.notes,
            }
        )

    false_allow_rate = 0.0 if expected_block_total <= 0 else (false_allow_count / expected_block_total)
    false_block_rate = 0.0 if expected_allow_total <= 0 else (false_block_count / expected_allow_total)

    verdict = "PASS" if (
        false_allow_rate <= float(false_allow_threshold)
        and false_block_rate <= float(false_block_threshold)
    ) else "FAIL"

    return {
        "bench_name": "SEC-DLP-BENCH-001",
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "db_path": str(db_path),
        "thresholds": {
            "false_allow_rate_max": float(false_allow_threshold),
            "false_block_rate_max": float(false_block_threshold),
        },
        "metrics": {
            "case_total": len(cases),
            "expected_block_total": expected_block_total,
            "expected_allow_total": expected_allow_total,
            "false_allow_count": false_allow_count,
            "false_block_count": false_block_count,
            "false_allow_rate": round(false_allow_rate, 6),
            "false_block_rate": round(false_block_rate, 6),
        },
        "verdict": verdict,
        "cases": rows,
    }


def _render_markdown(report: dict[str, Any]) -> str:
    thresholds = report.get("thresholds") or {}
    metrics = report.get("metrics") or {}
    lines = [
        "# SEC-DLP-BENCH-001 Report",
        "",
        f"- Generated at: {report.get('generated_at')}",
        f"- Verdict: **{report.get('verdict')}**",
        f"- false_allow_rate: {metrics.get('false_allow_rate')} (threshold <= {thresholds.get('false_allow_rate_max')})",
        f"- false_block_rate: {metrics.get('false_block_rate')} (threshold <= {thresholds.get('false_block_rate_max')})",
        "",
        "| Case | Expected | Actual | Pass | Level | Masked | Model | Reason |",
        "|---|---|---|---|---|---|---|---|",
    ]

    for item in report.get("cases") or []:
        lines.append(
            "| {case_id} | {expected} | {actual} | {passed} | {level} | {masked} | {model} | {reason} |".format(
                case_id=item.get("case_id"),
                expected=item.get("expected"),
                actual=item.get("actual"),
                passed="YES" if item.get("pass") else "NO",
                level=item.get("payload_level"),
                masked=item.get("masked"),
                model=item.get("target_model"),
                reason=item.get("blocked_reason") or "",
            )
        )

    lines.append("")
    return "\n".join(lines) + "\n"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run SEC-DLP-BENCH-001 benchmark.")
    parser.add_argument("--db-path", default="", help="Optional benchmark DB path. Uses temp DB when omitted.")
    parser.add_argument("--false-allow-threshold", type=float, default=DEFAULT_FALSE_ALLOW_THRESHOLD)
    parser.add_argument("--false-block-threshold", type=float, default=DEFAULT_FALSE_BLOCK_THRESHOLD)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    if str(args.db_path or "").strip():
        db_path = Path(str(args.db_path)).resolve()
        db_path.parent.mkdir(parents=True, exist_ok=True)
    else:
        tmp_dir = Path(tempfile.gettempdir()) / f"ragflowauth_egress_dlp_bench_{uuid4().hex}"
        tmp_dir.mkdir(parents=True, exist_ok=True)
        db_path = tmp_dir / "auth.db"

    report = _run_bench(
        db_path=db_path,
        false_allow_threshold=float(args.false_allow_threshold),
        false_block_threshold=float(args.false_block_threshold),
    )

    report_dir = Path("doc/test/reports")
    report_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    md_text = _render_markdown(report)
    md_output = report_dir / f"egress_dlp_bench_report_{ts}.md"
    md_latest = report_dir / "egress_dlp_bench_report_latest.md"
    json_output = report_dir / f"egress_dlp_bench_report_{ts}.json"
    json_latest = report_dir / "egress_dlp_bench_report_latest.json"

    md_output.write_text(md_text, encoding="utf-8")
    md_latest.write_text(md_text, encoding="utf-8")
    json_output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    json_latest.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[EgressBench] verdict={report.get('verdict')}")
    print(f"[EgressBench] markdown={md_output}")
    print(f"[EgressBench] markdown_latest={md_latest}")
    print(f"[EgressBench] json={json_output}")
    print(f"[EgressBench] json_latest={json_latest}")

    return 0 if str(report.get("verdict")) == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
