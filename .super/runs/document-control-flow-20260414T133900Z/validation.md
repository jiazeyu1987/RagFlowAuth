# Validation Contract

- Run ID: `document-control-flow-20260414T133900Z`
- Workspace: `D:/ProjectPackage/RagflowAuth`
- Source Type: `task-doc`
- Source Path: `docs/tasks/document-control-flow-parallel-20260414T151500/ws01-approval-workflow-contract.md`
- Reason: Wave 1 targets WS01 only; use the workstream's narrow backend validation commands instead of unrelated generic discovery results.

## Commands

- `python -m pytest backend/tests/test_document_control_service_unit.py backend/tests/test_document_control_api_unit.py -q`

## Alternate Candidates

- `script` `fronted/node_modules/.bin/esvalidate.cmd` | score=95 | fronted/node_modules/.bin/esvalidate.cmd
- `script` `fronted/node_modules/.bin/esvalidate.ps1` | score=95 | powershell -ExecutionPolicy Bypass -File fronted/node_modules/.bin/esvalidate.ps1
- `script` `fronted/node_modules/jsonpath/node_modules/.bin/esvalidate.cmd` | score=95 | fronted/node_modules/jsonpath/node_modules/.bin/esvalidate.cmd
- `script` `fronted/node_modules/jsonpath/node_modules/.bin/esvalidate.ps1` | score=95 | powershell -ExecutionPolicy Bypass -File fronted/node_modules/jsonpath/node_modules/.bin/esvalidate.ps1
- `document` `VALIDATION.md` | score=91 | python scripts\check_doc_e2e_docs.py --repo-root .; python scripts\run_doc_e2e.py --repo-root . --list
- `script` `tool/scripts/check-backup.bat` | score=88 | tool/scripts/check-backup.bat
- `script` `tool/scripts/check-portainer.bat` | score=88 | tool/scripts/check-portainer.bat
- `script` `tool/maintenance/scripts/check-mount-status.ps1` | score=88 | powershell -ExecutionPolicy Bypass -File tool/maintenance/scripts/check-mount-status.ps1
- `script` `scripts/run_fullstack_tests.bat` | score=84 | scripts/run_fullstack_tests.bat
- `script` `scripts/run_fullstack_tests.ps1` | score=84 | powershell -ExecutionPolicy Bypass -File scripts/run_fullstack_tests.ps1

## Validation Log

- 2026-04-14T13:48:10Z Supervisor overrode the auto-discovered `esvalidate` contract because it is unrelated to the active document-control workstream.
- Pending.
