# Test Plan Template

- Task ID: `gui-python-ip-20260408T102331`
- Created: `2026-04-08T10:23:31`
- Workspace: `D:\ProjectPackage\RagflowAuth`
- User Request: `做成一个单 GUI 的 Python 备份拉取程序，可下拉选择正式/测试服务器 IP，列出服务器备份，选择一个备份并拉取到本地自选目录`

## Test Scope

验证新增服务层能够正确列出远端备份并安全下载单个备份，验证独立 GUI 程序可以在本机启动并完成“选服务器 -> 载入备份 -> 选保存目录 -> 拉取”的基础交互链路。服务器端备份生成逻辑、SMB 挂载链路和现有多页签运维工具主窗口不在本次测试范围内。

## Environment

- 操作系统：Windows，本机可运行仓库内 Python。
- 工作目录：`D:\ProjectPackage\RagflowAuth`
- 服务器：`172.30.30.57`、`172.30.30.58`
- 远端路径：`/opt/ragflowauth/backups`
- 本机需要可用的 `ssh`、`scp`、`tkinter`
- 人工验证时需准备一个可写的本地目标目录

## Accounts and Fixtures

- SSH 账号：`root`
- 需要至少一台目标服务器上存在可识别备份目录，例如 `migration_pack_20260408_101343_362`
- 测试前不要求修改服务器数据；若目标服务器没有备份目录，测试应直接失败并记录缺失前提
- GUI 人工验证可选用临时目录作为本地拉取目标

If any required item is missing, the tester must fail fast and record the missing prerequisite.

## Commands

- `python -m unittest tool.maintenance.tests.test_server_backup_pull_unit`
  期望：服务层单测全部通过。
- `python -m unittest tool.maintenance.tests.test_server_backup_pull_tool_import_unit`
  期望：GUI 入口模块可导入，且关键类/入口函数存在。
- `python -m unittest tool.maintenance.tests.test_ui_backup_restore_tabs_import_unit`
  期望：现有备份/恢复相关 UI 导入不受本次新增功能影响。
- `python tool/maintenance/server_backup_pull_tool.py`
  期望：独立 GUI 成功打开，默认下拉框包含正式服务器与测试服务器，且可操作“加载备份列表”“选择保存路径”“拉取所选备份”。

For each command, note the expected success signal.

## Test Cases

Use stable test case ids. Every acceptance id from the PRD should appear in at least one `Covers` field.

### T1: 服务层列出远端备份

- Covers: P1-AC1
- Level: unit
- Command: `python -m unittest tool.maintenance.tests.test_server_backup_pull_unit`
- Expected: 远端输出被解析为稳定排序的备份列表，显示名称包含日期化文本，异常或无效目录名不会被当作可拉取备份。

### T2: 服务层执行单个备份拉取前校验

- Covers: P1-AC2
- Level: unit
- Command: `python -m unittest tool.maintenance.tests.test_server_backup_pull_unit`
- Expected: 非法目录名、已存在目标目录、缺失命令等场景会明确失败；合法输入会构造预期的 SCP 调用。

### T3: GUI 入口可导入并暴露主程序

- Covers: P2-AC1
- Level: unit
- Command: `python -m unittest tool.maintenance.tests.test_server_backup_pull_tool_import_unit`
- Expected: GUI 模块导入成功，主窗口类与 `main()` 入口存在。

### T4: GUI 手工拉取流程

- Covers: P2-AC1, P2-AC2, P3-AC1
- Level: manual
- Command: `python tool/maintenance/server_backup_pull_tool.py`
- Expected: GUI 打开后，下拉框默认提供正式/测试服务器；点击加载可显示备份列表；可选择本地保存路径；选中一个备份后可触发拉取，并在状态区或弹窗显示结果。

### T5: 现有备份相关 UI 不回归

- Covers: P3-AC2
- Level: unit
- Command: `python -m unittest tool.maintenance.tests.test_ui_backup_restore_tabs_import_unit`
- Expected: 现有备份/恢复页签仍可正常导入，说明新增独立 GUI 未破坏已有 UI 模块。

## Coverage Matrix

| Case ID | Area | Scenario | Level | Acceptance IDs | Evidence |
| --- | --- | --- | --- | --- | --- |
| T1 | 服务层 | 远端备份列表解析与日期化显示 | unit | P1-AC1 | `test-report.md` |
| T2 | 服务层 | 单个备份拉取前校验与 SCP 调用 | unit | P1-AC2 | `test-report.md` |
| T3 | GUI 入口 | 模块导入与入口暴露 | unit | P2-AC1 | `test-report.md` |
| T4 | GUI 运行时 | 服务器选择、加载、选路径、拉取交互 | manual | P2-AC1, P2-AC2, P3-AC1 | `test-report.md` |
| T5 | 回归 | 现有备份/恢复 UI 导入不受影响 | unit | P3-AC2 | `test-report.md` |

## Evaluator Independence

- Mode: blind-first-pass
- Validation surface: real-runtime
- Required tools: python, unittest, ssh, scp, tkinter
- First-pass readable artifacts: prd.md, test-plan.md
- Withheld artifacts: execution-log.md, task-state.json
- Real environment expectation: 在真实仓库与真实 Windows 运行环境中执行；GUI 路径需要真实启动 Tkinter 会话并记录实际运行结果。
- Escalation rule: 在 tester 产出首轮结论之前不得查看 `execution-log.md` 和 `task-state.json`；只有在需要对照偏差时才允许回看。

## Pass / Fail Criteria

- Pass when: 所有单测通过；GUI 可真实启动；正式/测试服务器下拉项存在；至少一条真实备份列表能够被加载并展示；可选择本地目录并完成一次单个备份拉取或在缺少服务器前提时明确报错。
- Fail when: 任一 acceptance id 没有对应验证；GUI 无法启动；服务器列表缺失默认项；拉取流程静默失败或覆盖已有目录；缺少 `ssh/scp/tkinter` 等前提却未明确报错。

## Regression Scope

- `tool/maintenance/core/ssh_executor.py` 的参数构建兼容性
- `tool/maintenance/features` 导出集合
- 现有备份/恢复相关 UI 模块导入
- 文档 `docs/maintance/backup.md` 的事实描述是否与当前实现一致

## Reporting Notes

Write results to `test-report.md`.

The tester must remain independent from the executor and should prefer blind-first-pass unless the task explicitly needs full-context evaluation.
