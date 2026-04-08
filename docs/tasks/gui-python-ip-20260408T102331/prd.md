# PRD Template

- Task ID: `gui-python-ip-20260408T102331`
- Created: `2026-04-08T10:23:31`
- Workspace: `D:\ProjectPackage\RagflowAuth`
- User Request: `做成一个单 GUI 的 Python 备份拉取程序，可下拉选择正式/测试服务器 IP，列出服务器备份，选择一个备份并拉取到本地自选目录`

## Goal

提供一个独立的 Python GUI 备份拉取工具，用户可以在正式服务器与测试服务器之间切换，查看服务器上的可用备份目录，以日期化名称选择单个备份，并将其拉取到本机指定目录。

## Scope

- 新增独立 Tkinter GUI 程序，入口位于 `tool/maintenance/` 下。
- 复用 `tool/maintenance/core/ssh_executor.py` 中已有的 SSH / SCP 参数构建能力。
- 新增一个面向“列服务器备份 + 拉取单个备份到本地”的 feature 模块。
- 默认服务器下拉选项固定包含正式服务器 `172.30.30.57` 与测试服务器 `172.30.30.58`。
- 本地保存目录由 GUI 选择，不再依赖服务器挂载 Windows 共享。
- 为新 feature 和 GUI 增加最小必要单测，并更新备份维护文档。

## Non-Goals

- 不修改服务器端已有备份生成逻辑。
- 不恢复或重建 `/mnt/replica`、CIFS、SMB 挂载链路。
- 不把本功能塞回现有多页签运维工具主窗口。
- 不新增自动同步全部备份、定时任务或覆盖式下载逻辑。
- 不对正式服务器或测试服务器做部署脚本改造。

## Preconditions

- 本机已安装可用的 `ssh` 与 `scp` 命令，且当前 Windows 会话可直接调用。
- 本机已具备到 `root@172.30.30.57` 和 `root@172.30.30.58` 的 SSH 免密或可批处理认证能力。
- 远端备份目录 `/opt/ragflowauth/backups` 存在且包含 `migration_pack_*` 或 `full_backup_pack_*` 目录。
- 本机 Python 运行环境包含 `tkinter`。
- 用户选择的本地保存目录可写。

If any item is missing, stop and record it in `task-state.json.blocking_prereqs`.

## Impacted Areas

- `tool/maintenance/core/constants.py`
- `tool/maintenance/core/ssh_executor.py`
- `tool/maintenance/features/__init__.py`
- `tool/maintenance/exports/features.py`
- 新增 `tool/maintenance/features/server_backup_pull.py`
- 新增 `tool/maintenance/server_backup_pull_tool.py`
- 新增启动脚本，例如仓库根目录批处理入口
- `tool/maintenance/tests/`
- `docs/maintance/backup.md`

## Phase Plan

Use stable phase ids. Do not renumber ids after execution has started.

### P1: 实现备份拉取服务层

- Objective: 提供一个可复用的 Python 服务层，负责远端备份目录枚举、备份名称解析、安全校验和单个备份目录下载。
- Owned paths: tool/maintenance/features/server_backup_pull.py; tool/maintenance/features/__init__.py; tool/maintenance/exports/features.py; tool/maintenance/tests/test_server_backup_pull_unit.py
- Dependencies: tool/maintenance/core/ssh_executor.py; tool/maintenance/core/constants.py
- Deliverables: 可列出远端备份的 feature API；可把单个备份拉取到本机目录的 feature API；服务层单测

### P2: 实现独立 GUI 程序

- Objective: 提供单窗口 Tkinter 工具，支持选择服务器、加载备份列表、选择本地保存路径、拉取所选备份，并给出明确状态提示。
- Owned paths: tool/maintenance/server_backup_pull_tool.py; tool/maintenance/tests/test_server_backup_pull_tool_import_unit.py
- Dependencies: P1 服务层；tool/maintenance/core/constants.py；tool/maintenance/core/logging_setup.py
- Deliverables: 可直接运行的 GUI 入口；默认服务器下拉框；备份列表交互；本地目录选择；拉取动作与状态展示

### P3: 启动入口、文档与验证收口

- Objective: 提供便于本机启动的入口，补充备份文档，并完成本任务所需验证闭环。
- Owned paths: docs/maintance/backup.md; 服务器备份拉取工具.bat; docs/tasks/gui-python-ip-20260408T102331/execution-log.md; docs/tasks/gui-python-ip-20260408T102331/test-report.md
- Dependencies: P1; P2
- Deliverables: 启动批处理入口；备份文档更新；测试结果与任务证据

## Phase Acceptance Criteria

List criteria under the matching phase id. Every criterion must use a stable acceptance id.

### P1

- P1-AC1: 服务层可以通过 SSH 枚举 `/opt/ragflowauth/backups` 下符合命名规则的备份目录，并返回稳定排序的原始目录名与日期化显示名。
- P1-AC2: 服务层可以对用户选中的单个备份执行安全校验后通过 SCP 拉取到本机指定目录；若目标目录已存在、目录名非法或 `ssh/scp` 缺失，必须明确失败而不是静默覆盖。
- Evidence expectation: 单测覆盖远端列表解析、名称格式化、安全校验与下载命令构造，执行记录写入 `execution-log.md`。

### P2

- P2-AC1: GUI 默认提供正式服务器 `172.30.30.57` 和测试服务器 `172.30.30.58` 的下拉选项，支持点击按钮加载该服务器的备份列表。
- P2-AC2: GUI 中的备份列表以日期化名称供用户选择，并提供“选择保存路径”和“拉取所选备份”操作；状态区或弹窗需要展示明确成功/失败原因。
- Evidence expectation: 运行截图或手动运行结果证明 GUI 可启动，且能从服务层加载展示数据。

### P3

- P3-AC1: 仓库提供一个面向 Windows 的本地启动入口，用户无需手工拼接命令即可启动该 GUI 程序。
- P3-AC2: `docs/maintance/backup.md` 补充该拉取工具的定位、使用方式与前提条件，并且本任务涉及的新增测试命令全部通过。
- Evidence expectation: 文档更新、启动入口文件、测试命令输出与任务工件中的测试记录。

## Done Definition

- 三个 phase 全部完成并同步到 `task-state.json`。
- 每个 acceptance id 都有实现证据和测试证据。
- 独立 GUI 可在本机 Python 环境中启动。
- 用户可以选择服务器、读取备份列表、选择本地目录并发起单个备份拉取。
- 文档说明与启动入口可支持后续本机使用。

At minimum, completion requires all phases completed and evidence for each acceptance id in `execution-log.md` or `test-report.md`.

## Blocking Conditions

- 本机没有 `ssh` 或 `scp` 命令。
- 当前环境无法连接任何目标服务器。
- 远端备份目录不存在或无可识别备份目录。
- 本机 Python 缺少 `tkinter`，导致 GUI 无法启动。
- 用户选择的保存路径不可写。
