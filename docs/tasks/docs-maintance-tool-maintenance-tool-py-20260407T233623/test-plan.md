# Test Plan

- Task ID: `docs-maintance-tool-maintenance-tool-py-20260407T233623`
- Created: `2026-04-07T23:36:23`
- Workspace: `D:\ProjectPackage\RagflowAuth`
- User Request: `将运维相关信息、测试服务器、正式服务器的信息补充到 docs/maintance/ 下，基于 tool/maintenance/tool.py 及相关发布实现写出真实的发布/回归/备份运维文档`

## Test Scope

验证三份新文档是否存在、是否围绕用户限定的三类主题、是否能映射到维护工具源码、以及是否避免复制敏感字面量。

不在本次测试范围内：

- 真实连接测试服或正式服执行发布
- 修复维护工具中的遗留路径问题
- 对维护工具源码做功能测试以外的行为变更

## Environment

- 平台：当前仓库工作区 `D:\ProjectPackage\RagflowAuth`
- 工具：`python`、PowerShell
- 数据面：仅检查仓库内源码、测试与新文档
- 不要求启动 UI，也不要求访问真实服务器

## Accounts and Fixtures

- 无需真实服务器账号
- 无需真实 SSH 连接
- 需要仓库中现有的维护源码和单元测试文件可读

## Commands

- `python - <<'PY' ... PY`
  目标：校验三份目标文档存在且非空，并且 `docs/maintance/` 下没有多余主题文档
  成功信号：输出 `maintance_docs_ok`
- `python - <<'PY' ... PY`
  目标：检查三份文档分别包含对应的关键事实锚点，例如测试服、正式服、`/opt/ragflowauth`、`D:\\datas\\RagflowAuth`、`doc/maintenance/release_history.md`
  成功信号：输出 `maintance_content_ok`
- `python - <<'PY' ... PY`
  目标：扫描三份新文档，确认未复制已知敏感字面量
  成功信号：输出 `maintance_no_secrets_ok`

## Test Cases

### T1: Three requested maintenance docs exist

- Covers: P1-AC1, P1-AC2
- Level: integration
- Command: existence and file-count check under `docs/maintance/`
- Expected: exactly `publish.md`, `regression.md`, `backup.md` exist and are non-empty

### T2: Publish doc matches release and rollback code anchors

- Covers: P2-AC1
- Level: manual
- Command: manual review against `tool/maintenance/ui/release_tab.py`, `tool/maintenance/features/release_publish.py`, `tool/maintenance/features/release_publish_local_to_test.py`, `tool/maintenance/features/release_publish_data_test_to_prod.py`, `tool/maintenance/features/release_rollback.py`
- Expected: document includes TEST and PROD server roles, release sequence, data-sync destructive warning, and rollback path

### T3: Regression doc matches smoke and base_url guard behavior

- Covers: P2-AC2
- Level: manual
- Command: manual review against `tool/maintenance/features/smoke_test.py`, `tool/maintenance/core/ragflow_base_url_guard.py`, `tool/maintenance/ui/smoke_tab.py`
- Expected: document describes read-only smoke checks, ports, endpoints, and base_url isolation guardrails truthfully

### T4: Backup doc matches backup and restore code anchors

- Covers: P2-AC3
- Level: manual
- Command: manual review against `tool/maintenance/ui/backup_files_tab.py`, `tool/maintenance/ui/replica_backups_tab.py`, `tool/maintenance/ui/restore_tab.py`, `tool/maintenance/controllers/release/sync_ops.py`, `tool/maintenance/controllers/release/sync_precheck_ops.py`, `tool/maintenance/controllers/release/sync_auth_upload_ops.py`, `tool/maintenance/controllers/release/sync_volumes_ops.py`
- Expected: document describes local backup root, server-local backup paths, restore-to-test-only rule, and `/mnt/replica` distinction truthfully

### T5: New docs do not copy secret literals

- Covers: P3-AC2
- Level: integration
- Command: scan `docs/maintance/*.md` for known secret literals from maintenance constants and deploy config
- Expected: none of the forbidden strings appear in the new docs

### T6: Evidence chain is complete

- Covers: P3-AC1, P3-AC3
- Level: manual
- Command: review `execution-log.md` and `test-report.md`
- Expected: all acceptance ids are referenced by execution or test evidence

## Coverage Matrix

| Case ID | Area | Scenario | Level | Acceptance IDs | Evidence |
| --- | --- | --- | --- | --- | --- |
| T1 | docs/maintance | three requested docs only | integration | P1-AC1, P1-AC2 | `test-report.md#Results` |
| T2 | publish | release and rollback documentation truthfulness | manual | P2-AC1 | `test-report.md#Results` |
| T3 | regression | smoke and base_url guard documentation truthfulness | manual | P2-AC2 | `test-report.md#Results` |
| T4 | backup | backup and restore documentation truthfulness | manual | P2-AC3 | `test-report.md#Results` |
| T5 | docs/maintance | secret omission | integration | P3-AC2 | `test-report.md#Results` |
| T6 | task artifacts | evidence completeness | manual | P3-AC1, P3-AC3 | `test-report.md#Results` |

## Evaluator Independence

- Mode: blind-first-pass
- Validation surface: real-runtime
- Required tools: python, powershell
- First-pass readable artifacts: prd.md, test-plan.md
- Withheld artifacts: execution-log.md, task-state.json
- Real environment expectation: validate against the live repository checkout and generated docs only
- Escalation rule: do not inspect withheld artifacts until an initial verdict exists

## Pass / Fail Criteria

- Pass when:
  - exactly three requested docs exist
  - the docs match maintenance code anchors
  - no known secret literals appear in the new docs
  - execution and test artifacts cover all acceptance ids
- Fail when:
  - a requested doc is missing or empty
  - a documented release, regression, or backup claim contradicts code
  - a secret literal is copied into the new docs
  - evidence is incomplete

## Regression Scope

- `tool/maintenance` source remains unchanged in this task, so regression scope is limited to documentation truthfulness and artifact completeness.

## Reporting Notes

Write results to `test-report.md`.
