# Test Plan

- Task ID: `gui-20260408T112206`
- Created: `2026-04-08T11:22:06`
- Workspace: `D:\ProjectPackage\RagflowAuth`
- User Request: `修正服务器备份拉取 GUI：服务器列表仅用于拉取，本地列表仅用于恢复；支持先拉取到本地，再从本地备份列表中选择一个恢复到本地数据。`

## Test Scope

验证独立 GUI 的以下行为：
- 能同时展示远端备份列表与本地备份列表。
- 本地备份列表基于当前保存目录加载本地备份目录。
- 拉取动作只依赖远端列表选中项。
- 恢复动作只依赖本地列表选中项。
- 应用可以在真实运行环境启动成功。

本次不覆盖：
- 服务器端备份生成逻辑。
- 真实 Docker volume 恢复内容的端到端校验。
- CIFS/SMB 挂载链路。

## Environment

- Windows 工作站，仓库根目录：`D:\ProjectPackage\RagflowAuth`
- Python 可执行 `unittest` 与 `tkinter`
- 真实启动验证使用当前桌面会话
- 如需实际远端拉取验证，本机需安装并可执行 `ssh`、`scp`

## Accounts and Fixtures

- 单元测试使用临时目录构造本地备份目录。
- 真实启动验证不要求登录服务器。
- 如执行手工远端拉取验证，需要已有可用 SSH 认证。

If any required item is missing, the tester must fail fast and record the missing prerequisite.

## Commands

- `python -m unittest tool.maintenance.tests.test_local_backup_catalog_unit tool.maintenance.tests.test_local_backup_restore_unit tool.maintenance.tests.test_server_backup_pull_unit tool.maintenance.tests.test_server_backup_pull_tool_import_unit tool.maintenance.tests.test_server_backup_pull_tool_ui_unit tool.maintenance.tests.test_ui_backup_restore_tabs_import_unit`
  - 预期信号：全部测试通过。
- `python tool\\maintenance\\server_backup_pull_tool.py`
  - 预期信号：窗口成功启动且无立即异常退出。

## Test Cases

### T1: 本地备份目录枚举

- Covers: P1-AC2
- Level: unit
- Command: `python -m unittest tool.maintenance.tests.test_local_backup_catalog_unit`
- Expected: 仅列出包含 `auth.db` 的目录，且按最新时间排序。

### T2: GUI 关键流程绑定

- Covers: P1-AC1, P1-AC3, P1-AC4, P1-AC5, P2-AC1
- Level: unit
- Command: `python -m unittest tool.maintenance.tests.test_server_backup_pull_tool_ui_unit`
- Expected: GUI 存在服务器列表和本地列表；刷新本地列表有效；拉取成功后自动刷新本地列表；恢复动作只使用本地列表选中目录。

### T3: GUI 导入与模块回归

- Covers: P2-AC1
- Level: unit
- Command: `python -m unittest tool.maintenance.tests.test_server_backup_pull_tool_import_unit tool.maintenance.tests.test_ui_backup_restore_tabs_import_unit`
- Expected: GUI 入口模块可导入，现有维护工具页签导入不受影响。

### T4: 真实运行启动

- Covers: P2-AC3
- Level: manual
- Command: `python tool\\maintenance\\server_backup_pull_tool.py`
- Expected: GUI 成功启动，无启动即崩溃；可见服务器列表、本地列表与操作按钮。

### T5: 相关恢复逻辑回归

- Covers: P1-AC4
- Level: unit
- Command: `python -m unittest tool.maintenance.tests.test_local_backup_restore_unit tool.maintenance.tests.test_server_backup_pull_unit`
- Expected: 本地恢复与服务器拉取底层接口维持现有行为，未因 GUI 重构发生回归。

### T6: 文档流程说明校验

- Covers: P2-AC2
- Level: unit
- Command: `python -c "from pathlib import Path; text = Path(r'D:\\ProjectPackage\\RagflowAuth\\docs\\maintance\\backup.md').read_text(encoding='utf-8'); assert '先从服务器拉取到本地' in text; assert '本地备份列表' in text; assert '从本地列表' in text"`
- Expected: 维护文档明确说明先拉取到本地，再从本地列表恢复的流程。

## Coverage Matrix

| Case ID | Area | Scenario | Level | Acceptance IDs | Evidence |
| --- | --- | --- | --- | --- | --- |
| T1 | 本地备份目录枚举 | 只展示可恢复的本地备份并按时间排序 | unit | P1-AC2 | unittest 输出 |
| T2 | GUI 关键流程 | 拉取与恢复分别绑定不同列表 | unit | P1-AC1, P1-AC3, P1-AC4, P1-AC5, P2-AC1 | unittest 输出 |
| T3 | 导入回归 | GUI 和现有维护页签保持可导入 | unit | P2-AC1 | unittest 输出 |
| T4 | 真实运行 | GUI 可在本机成功启动 | manual | P2-AC3 | 运行记录 |
| T5 | 底层接口回归 | GUI 改造不破坏现有恢复与拉取能力 | unit | P1-AC4 | unittest 输出 |

## Evaluator Independence

- Mode: blind-first-pass
- Validation surface: real-runtime
- Required tools: `python`, `unittest`, `tkinter`
- First-pass readable artifacts: prd.md, test-plan.md
- Withheld artifacts: execution-log.md, task-state.json
- Real environment expectation: 在真实仓库与本机运行环境上执行测试与启动验证，不使用 mock 成功结果替代真实流程绑定校验。
- Escalation rule: Do not inspect withheld artifacts until the tester has written an initial verdict or the main agent explicitly asks for discrepancy analysis.

## Pass / Fail Criteria

- Pass when:
  - 所有自动化测试通过。
  - GUI 启动验证通过。
  - 恢复入口明确来自本地列表，且测试中有证据证明。
- Fail when:
  - 任一测试失败。
  - GUI 启动即报错或无法展示双列表。
  - 发现恢复逻辑仍然读取服务器列表或存在隐式回退。

## Regression Scope

- `tool/maintenance/features/local_backup_catalog.py`
- `tool/maintenance/features/local_backup_restore.py`
- `tool/maintenance/features/server_backup_pull.py`
- `tool/maintenance/ui/` 现有页签导入

## Reporting Notes

Write results to `test-report.md`.
