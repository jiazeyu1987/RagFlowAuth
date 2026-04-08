# PRD

- Task ID: `gui-20260408T112206`
- Created: `2026-04-08T11:22:06`
- Workspace: `D:\ProjectPackage\RagflowAuth`
- User Request: `修正服务器备份拉取 GUI：服务器列表仅用于拉取，本地列表仅用于恢复；支持先拉取到本地，再从本地备份列表中选择一个恢复到本地数据。`

## Goal

让独立的服务器备份拉取 GUI 与实际使用流程一致：
- 服务器备份列表只负责查看远端备份并拉取到本地目录。
- 本地备份列表只负责展示当前本地目录中已经下载完成的备份，并从该列表选择一个执行本地恢复。
- 所有界面文案和状态提示都以可读中文展示，不再出现乱码。

## Scope

- `tool/maintenance/server_backup_pull_tool.py` 的界面结构、按钮行为、选择状态与文案。
- `tool/maintenance/features/local_backup_catalog.py` 在 GUI 中的集成，用于枚举当前本地目录下可恢复的备份。
- 备份拉取成功后自动刷新本地备份列表的流程。
- 针对 GUI 新流程的单元测试与导入测试。
- 相关备份说明文档中对该单独 GUI 工具流程的更新。

## Non-Goals

- 不修改服务器端备份生成逻辑。
- 不重做 `restore_downloaded_backup_to_local` 的底层恢复实现。
- 不恢复 CIFS/SMB 自动挂载或服务器主动推送到 Windows 的旧方案。
- 不引入“如果本地列表没选中就回退到服务器列表恢复”之类的兼容分支。

## Preconditions

- 本机 Python 环境可运行 `tkinter`。
- 仓库工作区可读写。
- 运行真实拉取时，本机需要可用的 `ssh` 与 `scp`，并具备目标服务器的 SSH 认证。
- 运行真实本地恢复时，当前仓库 `data/auth.db` 必须存在；如备份包含 `volumes/*.tar.gz`，则本机 Docker 必须可用。
- 用于展示本地恢复列表的保存目录必须存在或可创建。

If any item is missing, stop and record it in `task-state.json.blocking_prereqs`.

## Impacted Areas

- GUI 入口：`tool/maintenance/server_backup_pull_tool.py`
- 本地备份目录枚举：`tool/maintenance/features/local_backup_catalog.py`
- 本地恢复调用面：`tool/maintenance/features/local_backup_restore.py`
- 服务器拉取调用面：`tool/maintenance/features/server_backup_pull.py`
- 测试：`tool/maintenance/tests/test_server_backup_pull_tool_import_unit.py`
- 新增或调整的 GUI 行为测试：`tool/maintenance/tests/`
- 文档：`docs/maintance/backup.md`

## Phase Plan

Use stable phase ids. Do not renumber ids after execution has started.

### P1: 修正 GUI 双列表与恢复来源

- Objective: 把 GUI 改为“服务器列表拉取 + 本地列表恢复”的双列表模式，并清理当前乱码文案。
- Owned paths:
  - `tool/maintenance/server_backup_pull_tool.py`
- Dependencies:
  - `tool/maintenance/features/server_backup_pull.py`
  - `tool/maintenance/features/local_backup_catalog.py`
  - `tool/maintenance/features/local_backup_restore.py`
- Deliverables:
  - 双列表 GUI
  - 独立的服务器/本地选择状态
  - 拉取成功后自动刷新本地列表
  - 恢复只读取本地列表选中项
  - 可读中文文案

### P2: 补充验证与文档

- Objective: 为新流程补齐自动化验证，并把操作说明更新到维护文档。
- Owned paths:
  - `tool/maintenance/tests/test_server_backup_pull_tool_import_unit.py`
  - `tool/maintenance/tests/test_server_backup_pull_tool_ui_unit.py`
  - `docs/maintance/backup.md`
- Dependencies:
  - P1 完成后的 GUI 结构与公开类
- Deliverables:
  - GUI 行为测试
  - 运行时导入验证
  - 文档中明确的“先拉取、再从本地列表恢复”说明

## Phase Acceptance Criteria

List criteria under the matching phase id. Every criterion must use a stable acceptance id.

### P1

- P1-AC1: 窗口同时展示“服务器备份列表”和“本地备份列表”两个独立区域，并分别维护各自的选中状态。
- P1-AC2: 本地列表通过 `list_local_backups` 基于当前保存目录展示仅包含 `auth.db` 的本地备份，且支持手动刷新。
- P1-AC3: 成功拉取远端备份后，GUI 会自动刷新本地列表，并让状态提示明确显示本地落盘位置。
- P1-AC4: “拉取”动作只接受服务器列表选中项；“恢复”动作只接受本地列表选中项；两者之间不存在隐式回退或混用。
- P1-AC5: 工具内标题、按钮、提示框和状态栏文案以可读中文显示，不再保留当前乱码字符串。
- Evidence expectation:
  - `execution-log.md` 记录 GUI 结构变化、所改路径和本地列表恢复绑定关系。
  - 对应测试或运行验证能证明恢复使用的是本地目录路径而不是服务器条目。

### P2

- P2-AC1: 自动化测试覆盖 GUI 的导入以及“拉取使用服务器列表 / 恢复使用本地列表”的关键流程。
- P2-AC2: 文档明确描述单独 GUI 的正确操作顺序为“从服务器拉取到本地，再从本地列表选择一个进行恢复”。
- P2-AC3: 工具可以在本机真实运行环境中成功启动，且无启动即崩溃问题。
- Evidence expectation:
  - `execution-log.md` 记录测试命令与启动验证。
  - `test-report.md` 记录独立测试结果和最终结论。

## Done Definition

- P1 与 P2 均完成。
- 所有验收项均有对应证据。
- GUI 恢复入口只来自本地列表。
- 自动化测试通过。
- 工具已做一次真实启动验证。
- 文档与当前实现一致。

At minimum, completion requires all phases completed and evidence for each acceptance id in `execution-log.md` or `test-report.md`.

## Blocking Conditions

- 无法读取或写入目标 GUI 文件与测试文件。
- 本机 Python 环境缺少 `tkinter`，导致 GUI 无法运行。
- 新流程无法在不引入 fallback 的前提下明确区分服务器选择与本地选择。
- 自动化测试或真实启动验证无法执行且缺少可替代的真实证据路径。
