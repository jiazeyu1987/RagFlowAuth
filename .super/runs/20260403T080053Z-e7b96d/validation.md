# Validation Contract

- Run ID: `20260403T080053Z-e7b96d`
- Workspace: `D:/ProjectPackage/RagflowAuth`
- Source Type: `script`
- Source Path: `fronted/node_modules/.bin/esvalidate.cmd`
- Reason: Validation-like script name: esvalidate.cmd

## Commands

- `fronted/node_modules/.bin/esvalidate.cmd`

## Alternate Candidates

- `script` `fronted/node_modules/.bin/esvalidate.cmd` | score=95 | fronted/node_modules/.bin/esvalidate.cmd
- `script` `fronted/node_modules/.bin/esvalidate.ps1` | score=95 | powershell -ExecutionPolicy Bypass -File fronted/node_modules/.bin/esvalidate.ps1
- `script` `fronted/node_modules/jsonpath/node_modules/.bin/esvalidate.cmd` | score=95 | fronted/node_modules/jsonpath/node_modules/.bin/esvalidate.cmd
- `script` `fronted/node_modules/jsonpath/node_modules/.bin/esvalidate.ps1` | score=95 | powershell -ExecutionPolicy Bypass -File fronted/node_modules/jsonpath/node_modules/.bin/esvalidate.ps1
- `script` `tool/scripts/check-backup.bat` | score=88 | tool/scripts/check-backup.bat
- `script` `tool/scripts/check-portainer.bat` | score=88 | tool/scripts/check-portainer.bat
- `script` `tool/maintenance/scripts/check-mount-status.ps1` | score=88 | powershell -ExecutionPolicy Bypass -File tool/maintenance/scripts/check-mount-status.ps1
- `script` `scripts/run_fullstack_tests.bat` | score=84 | scripts/run_fullstack_tests.bat
- `script` `scripts/run_fullstack_tests.ps1` | score=84 | powershell -ExecutionPolicy Bypass -File scripts/run_fullstack_tests.ps1
- `script` `tool/scripts/test-deploy.ps1` | score=84 | powershell -ExecutionPolicy Bypass -File tool/scripts/test-deploy.ps1

## Validation Log

- 2026-04-03T08:12:02Z `worker-02` accepted: frontend report reviewed; `npm run build` passed (worker run).
- 2026-04-03T08:19:42Z Supervisor replayed backend contract from `worker-01`:
  `python -m unittest backend.tests.test_notification_dispatch_unit backend.tests.test_admin_notifications_api_unit backend.tests.test_me_messages_api_unit backend.tests.test_review_notification_integration_unit` -> `Ran 10 tests`, `OK`.
- 2026-04-03T08:20:20Z Supervisor replayed frontend build: `npm run build` (cwd=`fronted`) -> success.
- 2026-04-03T08:20:50Z Supervisor reviewed `worker-03` code evidence and accepted verdict `partially independent`.
- 2026-04-03T08:21:09Z Wave 1 validation complete: all workers marked `passed`; run marked `completed`.
