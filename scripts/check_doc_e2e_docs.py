#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, OrderedDict
from pathlib import Path

SCOPES = ("unit", "role")
STATUS_HEADING = "## 全真链路状态"
PENDING_SECTION = "## 自动化接入建议"
AUTOMATED_STATUS = "自动化状态：已接入 `doc/e2e` 全真链路"
AUTOMATED_FORBIDDEN_SNIPPETS = (
    "自动化状态：待接入 `doc/e2e` 全真链路",
    "尚未登记到 `doc/e2e/manifest.json`",
    "## 自动化接入建议",
    "建议新增 spec：",
)


def repo_root_from_script() -> Path:
    return Path(__file__).resolve().parents[1]


def to_repo_rel(path: Path, repo_root: Path) -> str:
    return path.relative_to(repo_root).as_posix()


def load_manifest(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SystemExit(f"[ERROR] Manifest not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"[ERROR] Manifest JSON invalid: {path}: {exc}") from exc


def collect_business_docs(repo_root: Path) -> list[dict]:
    docs: list[dict] = []
    for scope in SCOPES:
        scope_dir = repo_root / "doc" / "e2e" / scope
        if not scope_dir.exists():
            raise SystemExit(f"[ERROR] Missing scope directory: {scope_dir}")
        for path in sorted(scope_dir.glob("*.md")):
            if path.name == "README.md":
                continue
            docs.append(
                {
                    "scope": scope,
                    "path": path,
                    "rel": to_repo_rel(path, repo_root),
                }
            )
    if not docs:
        raise SystemExit("[ERROR] No business docs found under doc/e2e/unit or doc/e2e/role")
    return docs


def collect_manifest_entries(manifest: dict) -> list[dict]:
    groups = manifest.get("groups")
    if not isinstance(groups, dict):
        raise SystemExit("[ERROR] Manifest missing object field: groups")

    entries: list[dict] = []
    for scope in SCOPES:
        group_entries = groups.get(scope)
        if not isinstance(group_entries, list):
            raise SystemExit(f"[ERROR] Manifest group is not a list: {scope}")
        for item in group_entries:
            if not isinstance(item, dict):
                raise SystemExit(f"[ERROR] Manifest entry in group {scope} is not an object")
            doc = item.get("doc")
            specs = item.get("specs")
            if not isinstance(doc, str) or not doc.strip():
                raise SystemExit(f"[ERROR] Manifest entry in group {scope} missing doc")
            if not isinstance(specs, list) or not specs or not all(isinstance(spec, str) and spec.strip() for spec in specs):
                raise SystemExit(f"[ERROR] Manifest entry for {doc} must contain a non-empty specs list")
            entries.append({"scope": scope, "doc": doc, "specs": specs})
    return entries


def validate_manifest(
    *,
    repo_root: Path,
    manifest: dict,
    entries: list[dict],
    business_doc_rels: set[str],
) -> tuple[dict[str, dict], int]:
    errors: list[str] = []
    automated_map: dict[str, dict] = {}
    unique_specs: OrderedDict[str, None] = OrderedDict()
    scope_counts: Counter[str] = Counter()

    for entry in entries:
        doc_rel = entry["doc"]
        expected_prefix = f"doc/e2e/{entry['scope']}/"
        if not doc_rel.startswith(expected_prefix):
            errors.append(f"Manifest doc scope mismatch: {doc_rel} is not under {expected_prefix}")
        if doc_rel in automated_map:
            errors.append(f"Manifest doc duplicated: {doc_rel}")
            continue

        doc_path = repo_root / doc_rel
        if not doc_path.exists():
            errors.append(f"Manifest doc missing on disk: {doc_rel}")
        if doc_rel not in business_doc_rels:
            errors.append(f"Manifest doc is not a business doc under unit/role: {doc_rel}")

        for spec_rel in entry["specs"]:
            unique_specs.setdefault(spec_rel, None)
            if not (repo_root / spec_rel).exists():
                errors.append(f"Manifest spec missing on disk: {spec_rel}")

        automated_map[doc_rel] = entry
        scope_counts.update([entry["scope"]])

    coverage = manifest.get("coverage")
    if not isinstance(coverage, dict):
        errors.append("Manifest missing object field: coverage")
    else:
        expected_auto = len(automated_map)
        expected_pending = len(business_doc_rels) - expected_auto
        expected_unique_specs = len(unique_specs)
        if coverage.get("automated_doc_count") != expected_auto:
            errors.append(
                "Manifest coverage automated_doc_count mismatch: "
                f"expected {expected_auto}, got {coverage.get('automated_doc_count')}"
            )
        if coverage.get("pending_doc_count") != expected_pending:
            errors.append(
                "Manifest coverage pending_doc_count mismatch: "
                f"expected {expected_pending}, got {coverage.get('pending_doc_count')}"
            )
        if coverage.get("unique_spec_count") != expected_unique_specs:
            errors.append(
                "Manifest coverage unique_spec_count mismatch: "
                f"expected {expected_unique_specs}, got {coverage.get('unique_spec_count')}"
            )
        scope_summary = coverage.get("scopes")
        if not isinstance(scope_summary, dict):
            errors.append("Manifest coverage missing object field: scopes")
        else:
            for scope in SCOPES:
                expected_count = scope_counts[scope]
                field_name = f"{scope}_automated"
                if scope_summary.get(field_name) != expected_count:
                    errors.append(
                        f"Manifest coverage scopes.{field_name} mismatch: "
                        f"expected {expected_count}, got {scope_summary.get(field_name)}"
                    )

    if errors:
        raise SystemExit("[ERROR] Manifest validation failed:\n- " + "\n- ".join(errors))

    return automated_map, len(unique_specs)


def validate_docs(
    *,
    docs: list[dict],
    automated_map: dict[str, dict],
) -> None:
    errors: list[str] = []

    for doc in docs:
        text = doc["path"].read_text(encoding="utf-8")
        rel = doc["rel"]
        if STATUS_HEADING not in text:
            errors.append(f"{rel}: missing `{STATUS_HEADING}`")

        if rel in automated_map:
            if AUTOMATED_STATUS not in text:
                errors.append(f"{rel}: automated doc must declare `{AUTOMATED_STATUS}`")
            for snippet in AUTOMATED_FORBIDDEN_SNIPPETS:
                if snippet in text:
                    errors.append(f"{rel}: automated doc still contains stale snippet `{snippet}`")
            for spec_rel in automated_map[rel]["specs"]:
                if spec_rel not in text:
                    errors.append(f"{rel}: automated doc does not mention mapped spec `{spec_rel}`")
        else:
            if PENDING_SECTION not in text:
                errors.append(f"{rel}: pending doc must keep `{PENDING_SECTION}`")
            if AUTOMATED_STATUS in text:
                errors.append(f"{rel}: pending doc must not claim it is already automated")

    if errors:
        raise SystemExit("[ERROR] Doc validation failed:\n- " + "\n- ".join(errors))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate doc/e2e business docs against the full-real-chain manifest.")
    parser.add_argument("--repo-root", help="Repository root. Defaults to the parent of this script.")
    parser.add_argument("--manifest", help="Manifest path. Defaults to doc/e2e/manifest.json under the repo root.")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve() if args.repo_root else repo_root_from_script()
    manifest_path = Path(args.manifest).resolve() if args.manifest else (repo_root / "doc" / "e2e" / "manifest.json")

    docs = collect_business_docs(repo_root)
    business_doc_rels = {doc["rel"] for doc in docs}
    manifest = load_manifest(manifest_path)
    entries = collect_manifest_entries(manifest)
    automated_map, unique_spec_count = validate_manifest(
        repo_root=repo_root,
        manifest=manifest,
        entries=entries,
        business_doc_rels=business_doc_rels,
    )
    validate_docs(docs=docs, automated_map=automated_map)

    automated_count = len(automated_map)
    pending_count = len(docs) - automated_count
    print("Doc E2E doc consistency check passed.")
    print(f"- Business docs: {len(docs)}")
    print(f"- Automated docs: {automated_count}")
    print(f"- Pending docs: {pending_count}")
    print(f"- Unique specs: {unique_spec_count}")
    print(f"- Manifest: {manifest_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
