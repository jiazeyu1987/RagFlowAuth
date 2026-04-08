# PRD Template

- Task ID: `gui-data-auth-db-docker-ragflow-volumes-20260408T110205`
- Created: `2026-04-08T11:02:05`
- Workspace: `D:\ProjectPackage\RagflowAuth`
- User Request: `在服务器备份拉取 GUI 中增加本地还原功能，可将已下载备份恢复到本机 data/auth.db 与本机 Docker RAGFlow volumes`

## Goal

在现有服务器备份拉取 GUI 中增加“还原到本地”功能，使用户可以基于已下载到本机的备份目录，把 `auth.db` 恢复到当前仓库的本地运行数据目录，并把备份中的 RAGFlow volume 归档恢复到本机对应的 Docker volumes。

## Scope

- 新增本地恢复服务层，负责本地备份目录校验、`auth.db` 覆盖、本机 Docker volume 映射与恢复。
- 在 `tool/maintenance/server_backup_pull_tool.py` 中加入“还原到本地”交互。
- 复用当前单独 GUI 中的“服务器备份选择 + 本地保存目录”上下文，直接针对已下载备份执行本地恢复。
- 补充单测与运行验证。
- 更新备份维护文档，说明本地恢复前提和限制。

## Non-Goals

- 不修改服务器端恢复逻辑。
- 不把本地恢复功能塞回旧的多页签运维工具恢复页。
- 不自动重启本地 RagflowAuth Python 后端。
- 不实现模糊或多选 volume 映射；映射不唯一时必须直接失败。
- 不为缺失 Docker、本地后端正在运行等前提提供静默降级路径。

## Preconditions

- 用户已通过当前 GUI 把目标备份下载到本机保存目录。
- 备份目录中存在 `auth.db`；若存在 `volumes/`，其内为可恢复的 `*.tar.gz` 归档。
- 当前仓库本地数据目录 `data/auth.db` 存在且可写。
- 本机安装可用的 `docker` CLI，并能访问本机 Docker Engine。
- 本机 Docker volume 中存在与备份 volume 语义后缀可唯一匹配的目标 volume。
- 本地 RagflowAuth 后端未在 `127.0.0.1:8001` 运行。

If any item is missing, stop and record it in `task-state.json.blocking_prereqs`.

## Impacted Areas

- 新增 `tool/maintenance/features/local_backup_restore.py`
- `tool/maintenance/server_backup_pull_tool.py`
- `tool/maintenance/tests/test_local_backup_restore_unit.py`
- `tool/maintenance/tests/test_server_backup_pull_tool_import_unit.py`
- `docs/maintance/backup.md`
- `docs/tasks/gui-data-auth-db-docker-ragflow-volumes-20260408T110205/*`

## Phase Plan

Use stable phase ids. Do not renumber ids after execution has started.

### P1: 实现本地恢复服务层

- Objective: 提供一个可单测的本地恢复服务层，负责本地备份目录校验、目标 `auth.db` 路径校验、本机后端运行态检查、Docker volume 映射、停止容器、恢复 volume 和重启被停止容器。
- Owned paths: tool/maintenance/features/local_backup_restore.py; tool/maintenance/tests/test_local_backup_restore_unit.py
- Dependencies: 当前单独 GUI 下载目录结构；本地 `data/auth.db`；本机 Docker 环境
- Deliverables: 本地恢复 feature API；volume 映射与恢复逻辑；失败前提覆盖单测

### P2: 接入单独 GUI

- Objective: 在服务器备份拉取 GUI 中增加“还原到本地”按钮、确认提示与状态反馈，并让它以当前已选备份和本地保存目录为输入运行本地恢复。
- Owned paths: tool/maintenance/server_backup_pull_tool.py; tool/maintenance/tests/test_server_backup_pull_tool_import_unit.py
- Dependencies: P1 服务层
- Deliverables: GUI 恢复按钮；确认提示；成功/失败反馈；导入与运行验证

### P3: 文档与验证收口

- Objective: 更新备份文档并完成本地恢复的验证记录与任务闭环。
- Owned paths: docs/maintance/backup.md; docs/tasks/gui-data-auth-db-docker-ragflow-volumes-20260408T110205/execution-log.md; docs/tasks/gui-data-auth-db-docker-ragflow-volumes-20260408T110205/test-report.md
- Dependencies: P1; P2
- Deliverables: 文档更新；测试报告；状态闭环


## Phase Acceptance Criteria

List criteria under the matching phase id. Every criterion must use a stable acceptance id.

### P1

- P1-AC1: 服务层可以对已下载本地备份目录做严格校验，至少覆盖 `auth.db` 存在、本地 `data/auth.db` 目标可写、`127.0.0.1:8001` 未运行、Docker 可用，以及 volume 归档到本机 volume 的映射唯一性。
- P1-AC2: 服务层可以把备份中的 `auth.db` 覆盖恢复到仓库 `data/auth.db`，并把 `volumes/*.tar.gz` 恢复到映射到的本机 Docker volumes；恢复过程中需要先停止占用目标 volume 的本机容器，再在完成后重启它们。
- Evidence expectation: 单测覆盖前提失败和 volume 映射；真实运行验证覆盖至少一次本地 `auth.db` 与 volume 恢复。

### P2

- P2-AC1: GUI 在当前已选备份和本地保存目录上下文下提供“还原到本地”操作，并在本地未下载该备份时明确报错而不是静默创建空恢复。
- P2-AC2: GUI 在执行本地恢复前展示明确确认信息，执行过程中显示状态，完成后给出清晰成功或失败原因。
- Evidence expectation: GUI 初始化校验与脚本化 GUI 运行路径验证。

### P3

- P3-AC1: `docs/maintance/backup.md` 明确说明本地恢复会覆盖仓库 `data/auth.db`、恢复本机 Docker volumes、要求本地后端先停止，以及可能操作本机 Docker 容器。
- P3-AC2: 本任务涉及的新增单测、GUI 初始化验证和真实本机恢复验证都已记录在任务工件中并通过。
- Evidence expectation: 文档更新与 `test-report.md` 的最终通过记录。

## Done Definition

- 三个 phase 全部完成。
- GUI 可用当前已下载备份执行本地恢复。
- 本地恢复不会在前提缺失时静默跳过 volume 或后台服务处理。
- 所有 acceptance id 都在 `execution-log.md` 和 `test-report.md` 中有证据。

At minimum, completion requires all phases completed and evidence for each acceptance id in `execution-log.md` or `test-report.md`.

## Blocking Conditions

- 本地备份目录不存在或缺少 `auth.db`。
- `data/auth.db` 不存在或不可写。
- 本地 `127.0.0.1:8001` 端口仍有 RagflowAuth 后端运行。
- 本机 Docker CLI 不可用或 Docker Engine 不可访问。
- 任何备份 volume 归档无法唯一映射到一个本机 Docker volume。
