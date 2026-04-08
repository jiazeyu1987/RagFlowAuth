# PRD

- Task ID: `windows-20260408T124743`
- Created: `2026-04-08T12:47:43`
- Workspace: `D:\ProjectPackage\RagflowAuth`
- User Request: `将正式备份链路改为只做服务器本机备份，不再检查、不再执行也不再提示 Windows 副本状态；清理对应测试与状态文案。`

## Goal

让正式备份链路只依赖服务器本机备份目录，不再把 Windows 副本当作正式备份流程的一部分。

用户可见结果：
- 正式备份任务完成与失败仅由服务器本机备份结果决定。
- 正式备份运行过程与结果页不再出现 Windows 备份状态、路径、错误或设置提示。
- Windows 侧只保留独立手动拉取工具，不再属于正式自动备份流程。

## Scope

- `backend/services/data_security/backup_service.py`
- `backend/app/modules/data_security/support.py`
- `backend/services/data_security/settings_policy.py`
- `backend/tests/test_backup_restore_audit_unit.py`
- 数据安全前端页与相关组件、hooks、helpers、tests
- 受影响的 E2E 备份页用例
- 相关维护文档

## Non-Goals

- 不删除独立的服务器备份拉取 GUI。
- 不重做本地恢复演练逻辑。
- 不删除数据库 schema 中现有的 replica 相关字段。
- 不迁移旧数据，只调整当前正式逻辑与页面展示。

## Preconditions

- 后端与前端源码可读写。
- 后端单元测试可运行。
- 前端单元测试运行环境可用。
- 如运行页面相关回归，前端测试依赖与脚本可执行。

If any item is missing, stop and record it in `task-state.json.blocking_prereqs`.

## Impacted Areas

- 备份任务状态聚合与最终消息
- 设置页返回结构与统计信息
- 数据安全页高级设置与任务展示
- 本地恢复演练可用任务筛选
- 后端/前端/端到端测试快照与断言

## Phase Plan

### P1: 收敛后端正式备份链路为本机单份

- Objective: 移除正式备份服务中的 Windows 副本执行与状态聚合，让正式结果仅取决于服务器本机备份。
- Owned paths:
  - `backend/services/data_security/backup_service.py`
  - `backend/app/modules/data_security/support.py`
  - `backend/services/data_security/settings_policy.py`
- Dependencies:
  - `backend/services/data_security/store.py`
  - `backend/services/data_security/models.py`
- Deliverables:
  - 不再执行 `BackupReplicaService`
  - 不再生成 Windows 相关状态消息
  - 设置响应不再触发 Windows 挂载统计检查

### P2: 清理前端展示与测试

- Objective: 移除数据安全页中的 Windows 备份状态、路径和设置提示，并同步更新单元/E2E 测试。
- Owned paths:
  - `fronted/src/pages/DataSecurity.js`
  - `fronted/src/features/dataSecurity/`
  - `fronted/e2e/tests/`
  - `backend/tests/test_backup_restore_audit_unit.py`
  - `docs/maintance/backup.md`
- Dependencies:
  - P1 的后端状态与响应收敛
- Deliverables:
  - 前端页面仅展示本机备份相关信息
  - 测试改为断言本机单份备份行为
  - 文档说明正式逻辑只做服务器本机备份

## Phase Acceptance Criteria

### P1

- P1-AC1: 正式备份服务运行时不再调用 Windows 副本执行路径，最终成功/失败仅由本机备份结果决定。
- P1-AC2: 正式备份任务状态消息不再出现 `waiting_windows`、`local_and_windows`、`windows_only`、`windows_backup_*` 等 Windows 语义。
- P1-AC3: 获取数据安全设置时不再因为正式逻辑而检查 Windows 挂载状态或统计 Windows 副本目录。
- Evidence expectation:
  - `execution-log.md` 记录后端变更点与测试命令。
  - 对应后端测试证明 Windows 副本分支不再影响正式结果。

### P2

- P2-AC1: 数据安全页不再展示 Windows 备份路径、Windows 备份状态或 Windows 备份设置。
- P2-AC2: 相关前端单元测试与 E2E 用例改为断言本机单份备份行为。
- P2-AC3: 文档明确说明正式逻辑只要求服务器本机备份，Windows 端如需副本使用独立手动拉取工具。
- Evidence expectation:
  - `test-report.md` 记录前后端测试结果。
  - `execution-log.md` 记录页面改动和文档更新。

## Done Definition

- P1 和 P2 全部完成。
- 正式备份链路不再检查、不再执行、不再提示 Windows 副本。
- 前端页面不再暴露 Windows 正式备份入口或状态。
- 相关单元测试通过。
- 如可运行，页面相关回归测试通过。

## Blocking Conditions

- 后端备份服务存在其他硬依赖强制要求 replica 状态。
- 前端页面仍有未清除的 Windows 断言导致回归无法收口。
- 测试环境不可用且缺少可替代证据路径。
