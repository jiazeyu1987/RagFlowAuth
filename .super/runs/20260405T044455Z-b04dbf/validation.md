# Validation Contract

- Run ID: `20260405T044455Z-b04dbf`
- Workspace: `D:/ProjectPackage/RagflowAuth`
- Source Type: `document`
- Source Path: `VALIDATION.md`
- Reason: Supervisor override because auto-discovery falsely preferred `node_modules` validation shims over the repository's explicit doc/e2e full-real-chain contract.

## Commands

- `python scripts\check_doc_e2e_docs.py --repo-root .`
- `python scripts\run_doc_e2e.py --repo-root . --list`
- `python scripts\run_doc_e2e.py --repo-root .`

## Alternate Candidates

- `document` `VALIDATION.md` | score=91 | python scripts\check_doc_e2e_docs.py --repo-root .; python scripts\run_doc_e2e.py --repo-root . --list
- `script` `fronted/node_modules/.bin/esvalidate.cmd` | score=95 | fronted/node_modules/.bin/esvalidate.cmd
- `script` `fronted/node_modules/.bin/esvalidate.ps1` | score=95 | powershell -ExecutionPolicy Bypass -File fronted/node_modules/.bin/esvalidate.ps1
- `script` `fronted/node_modules/jsonpath/node_modules/.bin/esvalidate.cmd` | score=95 | fronted/node_modules/jsonpath/node_modules/.bin/esvalidate.cmd
- `script` `fronted/node_modules/jsonpath/node_modules/.bin/esvalidate.ps1` | score=95 | powershell -ExecutionPolicy Bypass -File fronted/node_modules/jsonpath/node_modules/.bin/esvalidate.ps1
- `script` `tool/scripts/check-backup.bat` | score=88 | tool/scripts/check-backup.bat
- `script` `tool/scripts/check-portainer.bat` | score=88 | tool/scripts/check-portainer.bat
- `script` `tool/maintenance/scripts/check-mount-status.ps1` | score=88 | powershell -ExecutionPolicy Bypass -File tool/maintenance/scripts/check-mount-status.ps1
- `script` `scripts/run_fullstack_tests.bat` | score=84 | scripts/run_fullstack_tests.bat
- `script` `scripts/run_fullstack_tests.ps1` | score=84 | powershell -ExecutionPolicy Bypass -File scripts/run_fullstack_tests.ps1

## Validation Log

- 2026-04-05T04:46:43Z Supervisor override: use `VALIDATION.md` as the authoritative validation contract for this run.
- 2026-04-05T05:04:11Z Worker-02 validation failed under shared parallel Playwright runtime state. Supervisor added isolated per-worker env guidance and shared auth-dir support before requesting rework.
- 2026-04-05T07:54:48Z `python scripts\check_doc_e2e_docs.py --repo-root .` => passed (`Business docs: 30`, `Automated docs: 30`, `Pending docs: 0`, `Unique specs: 24`).
- 2026-04-05T07:54:48Z `python scripts\run_doc_e2e.py --repo-root . --list` => passed and enumerated 30 docs mapped to 24 unique Playwright specs.
- 2026-04-05T07:54:48Z `python scripts\run_doc_e2e.py --repo-root .` => passed. Full real-chain manifest run completed and wrote `doc/test/reports/doc_e2e_report_20260405_155253.md` plus `doc/test/reports/doc_e2e_report_latest.md`.
- 2026-04-05T07:54:48Z Supervisor final decision: validation passed; run can be marked completed.
