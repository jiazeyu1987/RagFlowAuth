# Validation

This repository uses the following pass/fail contract for the `doc/e2e` full-real-chain rollout.

## Authority Boundary

- `docs/` is the main engineering documentation tree.
- `doc/e2e/` is the authoritative location for document E2E business docs and manifest entries used by the validation scripts.

## Required Commands

```powershell
python scripts\check_doc_e2e_docs.py --repo-root .
python scripts\run_doc_e2e.py --repo-root . --list
python scripts\run_doc_e2e.py --repo-root .
```

## Pass Criteria

- `doc/e2e` business docs, manifest, and mapped specs stay consistent.
- The full `doc/e2e` manifest runs through the real Playwright chain without mock or fallback.
- Any backend or frontend support code added for missing scenarios must fail fast when prerequisites are absent.

## Notes

- Do not replace external dependencies with mock responses.
- If a scenario still depends on unavailable real credentials or unavailable real services, fail the validation and report the exact missing prerequisite.
