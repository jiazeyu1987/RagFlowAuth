# Test Plan Template

- Task ID: `gui-data-auth-db-docker-ragflow-volumes-20260408T110205`
- Created: `2026-04-08T11:02:05`
- Workspace: `D:\ProjectPackage\RagflowAuth`
- User Request: `在服务器备份拉取 GUI 中增加本地还原功能，可将已下载备份恢复到本机 data/auth.db 与本机 Docker RAGFlow volumes`

## Test Scope

验证本地恢复服务层能够对本地备份目录执行严格前提校验、唯一映射 volume、恢复 `data/auth.db` 和本机 Docker volumes；验证单独 GUI 可以对已下载备份触发本地恢复并显示明确结果。服务器端恢复链路和旧运维工具恢复页不在本次范围内。

## Environment

- 操作系统：Windows
- 工作目录：`D:\ProjectPackage\RagflowAuth`
- 本地目标数据库：`D:\ProjectPackage\RagflowAuth\data\auth.db`
- 本机 Docker 可用，且存在本地 RAGFlow 相关 volumes
- 真实验证时需准备一个已下载的备份目录，例如 `migration_pack_20260408_095407_544`
- 本地 RagflowAuth 后端需保持停止状态，避免锁定 `data/auth.db`

## Accounts and Fixtures

- 已下载的本地备份目录，包含 `auth.db` 与 `volumes/*.tar.gz`
- 本机 Docker volume 列表中存在可匹配的本地目标 volumes
- GUI 运行环境包含 `tkinter`
- 若任一前提缺失，测试必须失败并记录

If any required item is missing, the tester must fail fast and record the missing prerequisite.

## Commands

- `python -m unittest tool.maintenance.tests.test_local_backup_restore_unit`
  期望：本地恢复服务层单测通过。
- `python -m unittest tool.maintenance.tests.test_server_backup_pull_tool_import_unit`
  期望：GUI 模块仍可导入，且新增恢复入口不破坏模块初始化。
- `python -m unittest tool.maintenance.tests.test_server_backup_pull_unit`
  期望：原有下载服务层单测保持通过。
- `python - <<'PY'` 创建 Tk 根窗口并实例化 `ServerBackupPullTool`
  期望：GUI 初始化成功。
- `python - <<'PY'` 使用一个真实已下载备份目录执行本地恢复
  期望：`data/auth.db` 被恢复，目标 Docker volumes 恢复成功，相关容器按预期停止/重启。

For each command, note the expected success signal.

## Test Cases

Use stable test case ids. Every acceptance id from the PRD should appear in at least one `Covers` field.

### T1: 服务层前提校验与 volume 映射

- Covers: P1-AC1
- Level: unit
- Command: `python -m unittest tool.maintenance.tests.test_local_backup_restore_unit`
- Expected: 缺失备份目录、缺失 `auth.db`、本地后端运行中、Docker 不可用、volume 映射不唯一等场景都会明确失败；合法 volume 名可映射到唯一的本机 volume。

### T2: 服务层执行本地恢复

- Covers: P1-AC2
- Level: unit
- Command: `python -m unittest tool.maintenance.tests.test_local_backup_restore_unit`
- Expected: 单测确认会复制 `auth.db`、调用 Docker volume 恢复命令，并对需要的本机容器执行停止/重启。

### T3: GUI 模块导入与初始化

- Covers: P2-AC1
- Level: unit
- Command: `python -m unittest tool.maintenance.tests.test_server_backup_pull_tool_import_unit`
- Expected: GUI 模块可导入，主窗口类与入口函数存在。

### T4: GUI 真实本地恢复路径

- Covers: P2-AC1, P2-AC2, P3-AC2
- Level: manual
- Command: `python - <<'PY'` 脚本化驱动 `ServerBackupPullTool`，设置本地保存目录和已选备份并调用本地恢复动作
- Expected: GUI 在本地缺失备份时会明确报错；对真实已下载备份会弹出确认、执行恢复并给出成功状态。

### T5: 文档与既有下载功能回归

- Covers: P3-AC1
- Level: unit
- Command: `python -m unittest tool.maintenance.tests.test_server_backup_pull_unit`
- Expected: 原有下载链路单测继续通过，说明 GUI 新增本地恢复没有破坏现有下载功能。

## Coverage Matrix

| Case ID | Area | Scenario | Level | Acceptance IDs | Evidence |
| --- | --- | --- | --- | --- | --- |
| T1 | 本地恢复服务层 | 前提校验与 volume 唯一映射 | unit | P1-AC1 | `test-report.md` |
| T2 | 本地恢复服务层 | `auth.db` 与 Docker volumes 恢复 | unit | P1-AC2 | `test-report.md` |
| T3 | GUI | 模块导入与窗口初始化 | unit | P2-AC1 | `test-report.md` |
| T4 | GUI 运行时 | 基于已下载备份执行本地恢复 | manual | P2-AC1, P2-AC2, P3-AC2 | `test-report.md` |
| T5 | 回归/文档 | 原下载功能不回归，文档已更新 | unit | P3-AC1 | `test-report.md` |

## Evaluator Independence

- Mode: blind-first-pass
- Validation surface: real-runtime
- Required tools: python, unittest, tkinter, docker
- First-pass readable artifacts: prd.md, test-plan.md
- Withheld artifacts: execution-log.md, task-state.json
- Real environment expectation: 在真实 Windows 环境、真实仓库数据目录和真实 Docker 环境中执行验证；GUI 需要真实初始化 Tk 会话，恢复路径需要操作真实本地备份与真实本机 Docker volume。
- Escalation rule: 在 tester 先给出初步结论之前，不查看 `execution-log.md` 和 `task-state.json`。

## Pass / Fail Criteria

- Pass when: 服务层单测通过；GUI 初始化成功；真实本地恢复至少成功执行一次；失败前提都以明确错误呈现；文档已说明覆盖风险和前提。
- Fail when: `auth.db` 或 Docker volume 恢复存在静默跳过；本地后端运行中仍继续恢复；volume 映射不唯一却继续写入；GUI 缺少明确确认或结果提示。

## Regression Scope

- `tool/maintenance/features/server_backup_pull.py`
- `tool/maintenance/server_backup_pull_tool.py`
- `docs/maintance/backup.md`
- 本机 `data/auth.db` 与 Docker volume 之间的恢复顺序

## Reporting Notes

Write results to `test-report.md`.

The tester must remain independent from the executor and should prefer blind-first-pass unless the task explicitly needs full-context evaluation.
