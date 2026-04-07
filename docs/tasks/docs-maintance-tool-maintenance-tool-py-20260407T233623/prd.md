# PRD

- Task ID: `docs-maintance-tool-maintenance-tool-py-20260407T233623`
- Created: `2026-04-07T23:36:23`
- Workspace: `D:\ProjectPackage\RagflowAuth`
- User Request: `将运维相关信息、测试服务器、正式服务器的信息补充到 docs/maintance/ 下，基于 tool/maintenance/tool.py 及相关发布实现写出真实的发布/回归/备份运维文档`

## Goal

在 `docs/maintance/` 下新增且仅新增三份维护文档：

- `publish.md`
- `regression.md`
- `backup.md`

三份文档都必须基于当前仓库里的 `tool/maintenance/` 真实实现来写，覆盖测试服务器与正式服务器角色、固定目录、发布链路、只读验证和备份或恢复边界，并且不要把密码、API key、JWT secret 等敏感字面量复制进新文档。

## Scope

- 新增文档：
  - `docs/maintance/publish.md`
  - `docs/maintance/regression.md`
  - `docs/maintance/backup.md`
- 作为事实来源读取的代码与测试：
  - `tool/maintenance/tool.py`
  - `tool/maintenance/core/constants.py`
  - `tool/maintenance/core/server_config.py`
  - `tool/maintenance/core/ragflow_base_url_guard.py`
  - `tool/maintenance/features/release_publish.py`
  - `tool/maintenance/features/release_publish_local_to_test.py`
  - `tool/maintenance/features/release_publish_data_test_to_prod.py`
  - `tool/maintenance/features/release_rollback.py`
  - `tool/maintenance/features/smoke_test.py`
  - `tool/maintenance/controllers/release/*.py`
  - `tool/maintenance/controllers/release/sync_*.py`
  - `tool/maintenance/ui/release_tab.py`
  - `tool/maintenance/ui/restore_tab.py`
  - `tool/maintenance/ui/backup_files_tab.py`
  - `tool/maintenance/ui/replica_backups_tab.py`
  - `tool/maintenance/ui/smoke_tab.py`
  - `tool/maintenance/tests/test_release_publish_local_to_test_unit.py`
  - `tool/maintenance/tests/test_release_publish_data_test_to_prod_unit.py`
  - `tool/maintenance/tests/test_release_publish_unit.py`
  - `tool/maintenance/tests/test_release_rollback_unit.py`
  - `tool/maintenance/tests/test_ragflow_base_url_guard_unit.py`
  - `tool/maintenance/tests/test_release_history_unit.py`

## Non-Goals

- 不修改维护工具源码、脚本、服务器配置或发布行为。
- 不修复工具当前仍写入 `doc/maintenance/release_history.md` 的遗留路径。
- 不新增超出“发布、回归、备份”三类主题之外的维护文档。
- 不把仓库中的密码、共享凭据、API key、JWT secret 复制到 `docs/maintance/`。

## Preconditions

- 能读取 `tool/maintenance/` 相关源码和测试。
- 能写入 `docs/maintance/*.md`。
- 能运行本地 `python` 做聚焦校验。
- 如缺失关键维护源码或文档目标路径不可写，必须停止并记录为阻塞前提。

## Impacted Areas

- `docs/maintance/` 作为本次新增运维文档目录。
- `docs/tasks/docs-maintance-tool-maintenance-tool-py-20260407T233623/` 作为执行与验收证据目录。
- 文档会直接影响维护者对以下固定事实的理解：
  - 测试服务器 `172.30.30.58`
  - 正式服务器 `172.30.30.57`
  - 默认 SSH 用户 `root`
  - 远端应用目录 `/opt/ragflowauth`
  - 本地备份目录 `D:\datas\RagflowAuth`
  - 工具仍写入 `doc/maintenance/release_history.md`

## Phase Plan

### P1: Create The Three Requested Maintenance Docs

- Objective:
  在 `docs/maintance/` 下创建且仅创建三份目标文档。
- Owned paths:
  - `docs/maintance/publish.md`
  - `docs/maintance/regression.md`
  - `docs/maintance/backup.md`
- Dependencies:
  - 用户确认后的收窄范围
  - 当前 `docs/` 树
- Deliverables:
  - 三份空白模板之外的真实文档落盘

### P2: Write Publish, Regression, And Backup Docs From Code

- Objective:
  用维护工具真实代码写出发布、回归验证、备份文档，并把测试服与正式服信息嵌入到对应文档中。
- Owned paths:
  - `docs/maintance/publish.md`
  - `docs/maintance/regression.md`
  - `docs/maintance/backup.md`
- Dependencies:
  - 维护常量与环境定义
  - 发布、回滚、同步、恢复、冒烟实现
  - 对应 UI 文案和单元测试
- Deliverables:
  - 发布文档
  - 回归验证文档
  - 备份文档

### P3: Validate Truthfulness And Hand Off

- Objective:
  验证三份文档存在、非空、内容与源码一致，并确认新文档没有复制敏感字面量。
- Owned paths:
  - `docs/tasks/docs-maintance-tool-maintenance-tool-py-20260407T233623/execution-log.md`
  - `docs/tasks/docs-maintance-tool-maintenance-tool-py-20260407T233623/test-report.md`
- Dependencies:
  - P1-P2 产物
  - 本地聚焦校验命令
- Deliverables:
  - 执行证据
  - 测试报告
  - 可完成的任务状态

## Phase Acceptance Criteria

### P1

- P1-AC1: `docs/maintance/publish.md`、`docs/maintance/regression.md`、`docs/maintance/backup.md` 都已创建。
- P1-AC2: 本次任务没有在 `docs/maintance/` 下额外新增第四类主题文档。
- Evidence expectation:
  文件存在性检查记录到 `execution-log.md`

### P2

- P2-AC1: `docs/maintance/publish.md` 如实说明了本机到测试、测试到正式（镜像）、测试到正式（数据）以及正式环境回滚入口。
- P2-AC2: `docs/maintance/regression.md` 如实说明了基于 `smoke_test.py` 与 base_url guard 的回归或冒烟检查、关键端口和只读验证边界。
- P2-AC3: `docs/maintance/backup.md` 如实说明了本地备份目录、服务器本地备份目录、恢复只允许到测试服务器，以及 `/mnt/replica` 与服务器本地备份的区别。
- Evidence expectation:
  针对源码锚点的内容校验和人工复核记录到任务工件

### P3

- P3-AC1: 聚焦校验确认三份文档非空，且都包含测试服或正式服、固定路径、对应主题锚点。
- P3-AC2: 聚焦校验确认新文档没有复制维护工具中的已知密码、共享凭据、API key 或 JWT secret 字面量。
- P3-AC3: `execution-log.md` 与 `test-report.md` 能为所有 acceptance ids 提供证据引用。
- Evidence expectation:
  验证命令结果与最终 verdict 记录到任务工件

## Done Definition

- P1-P3 全部完成。
- `docs/maintance/` 下只新增本次要求的三份文档。
- 每个 acceptance id 都能在 `execution-log.md` 或 `test-report.md` 中找到证据。
- 三份文档都基于当前仓库代码与测试，而不是凭空补写。
- 敏感值没有被复制进新文档。

## Blocking Conditions

- 关键维护源码不可读。
- 无法写入 `docs/maintance/*.md`。
- 校验发现文档中的核心说法与当前源码不一致。
- 完成文档必须依赖复制敏感值。
