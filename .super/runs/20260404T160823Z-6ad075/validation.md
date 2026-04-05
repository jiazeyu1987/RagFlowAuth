# Validation Contract

- Run ID: `20260404T160823Z-6ad075`
- Workspace: `D:/ProjectPackage/RagflowAuth`
- Source Type: `script`
- Source Path: `scripts/run_doc_e2e.py`
- Reason: Supervisor selected the repo-native doc/e2e manifest runner created in this run.

## Commands

- `python scripts/run_doc_e2e.py --repo-root D:/ProjectPackage/RagflowAuth`

## Alternate Candidates

- `script` `scripts/run_fullstack_tests.ps1` | score=84 | powershell -ExecutionPolicy Bypass -File scripts/run_fullstack_tests.ps1
- `package-json` `fronted/package.json` | supervisor override | npm run e2e:docs
- `script` `fronted/node_modules/.bin/esvalidate.cmd` | rejected | node_modules artifact, not project-native validation

## Validation Log

- Pending.
