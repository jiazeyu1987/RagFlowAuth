# PRD

- Task ID: `data-security-20260408T013422`
- Created: `2026-04-08T01:34:22`
- Workspace: `D:\ProjectPackage\RagflowAuth`
- User Request: `继续推进系统重构，完成 data_security 模块前后端第一期局部重构，保持现有行为与接口稳定`

## Goal

在不改变数据安全模块后端 API、`DataSecurityStore` 对外接口、备份/恢复演练核心行为以及前端现有页面交互语义的前提下，完成 `data_security` 第一批前后端局部重构：后端把超大 `store.py` 收敛为 facade + 仓储组合，前端把超大页面与 Hook 拆成更明确的状态单元和展示组件，并用现有回归测试证明行为稳定。

## Scope

- 后端数据安全模块：
  - `backend/services/data_security/store.py`
  - `backend/services/data_security/models.py`
  - `backend/services/data_security/*`
  - `backend/app/modules/data_security/runner.py`
  - 数据安全相关后端测试
- 前端数据安全模块：
  - `fronted/src/features/dataSecurity/*`
  - `fronted/src/pages/DataSecurity.js`
  - 数据安全相关前端测试
- 执行工件与阶段记录：
  - `docs/exec-plans/active/data-security-refactor-phase-1.md`
  - `docs/tasks/data-security-20260408T013422/*`

## Non-Goals

- 不改数据安全 API 路径和返回 envelope
- 不改 `DataSecurityStore` 公开方法名和主要参数
- 不改备份任务状态枚举、恢复演练结果语义和审计字段
- 不改调度策略、备份业务规则和 Docker/备份步骤实现语义
- 不扩散到通知中心、权限模型、文档预览等其他系统重构阶段
- 不引入 fallback、mock 路径或静默降级

## Preconditions

- 本地 Python/pytest 可运行
- 前端 `react-scripts test` 可运行
- 现有数据安全模块后端测试可作为行为基线
- 现有数据安全页面/Hook 测试可作为行为基线

如果上述前提缺失，必须停止并记录到 `task-state.json.blocking_prereqs`。

## Impacted Areas

- 依赖注入与运行时调用：
  - `backend/app/dependencies.py`
  - `backend/app/modules/data_security/runner.py`
  - `backend/services/data_security_scheduler_v2.py`
- 数据安全路由契约：
  - `backend/app/modules/data_security/router.py`
- 备份/复制/恢复演练相关实现：
  - `backend/services/data_security/backup_service.py`
  - `backend/services/data_security/restore_service.py`
  - `backend/services/data_security/replica_service.py`
- 前端数据安全页面：
  - `fronted/src/pages/DataSecurity.js`
  - `fronted/src/features/dataSecurity/useDataSecurityPage.js`
  - `fronted/src/features/dataSecurity/api.js`

## Phase Plan

### P1: 后端数据安全存储职责拆分

- Objective:
  - 将 `DataSecurityStore` 收敛为稳定 facade，拆出锁、设置、任务、恢复演练四类仓储，并把标准挂载环境策略移出持久化实现。
- Owned paths:
  - `backend/services/data_security/store.py`
  - `backend/services/data_security/settings_policy.py`
  - `backend/services/data_security/repositories/*`
  - `backend/app/modules/data_security/runner.py`
  - 数据安全相关后端测试
- Dependencies:
  - 现有 `DataSecuritySettings` / `BackupJob` / `RestoreDrill` 模型
  - 现有 router、scheduler、backup/restore service 对 `DataSecurityStore` 的调用保持稳定
- Deliverables:
  - 新增 settings policy 和 repositories
  - `store.py` 改为 facade/委托实现
  - 锁释放语义收紧且有测试覆盖

### P2: 前端数据安全页面与 Hook 拆分

- Objective:
  - 将 `useDataSecurityPage` 拆成更单一的状态单元，把 `DataSecurity.js` 拆成按卡片分区的展示组件，并把变更原因提示从 Hook 移到页面层。
- Owned paths:
  - `fronted/src/features/dataSecurity/*`
  - `fronted/src/features/dataSecurity/components/*`
  - `fronted/src/pages/DataSecurity.js`
  - `fronted/src/features/dataSecurity/useDataSecurityPage.test.js`
  - `fronted/src/pages/DataSecurity.test.js`
- Dependencies:
  - 现有 `dataSecurityApi`
  - 现有页面测试中的 `data-testid` 和交互契约保持稳定
- Deliverables:
  - 新增 data security helpers / sub-hooks / section components
  - `useDataSecurityPage.js` 缩小并聚焦组合职责
  - `DataSecurity.js` 缩小并仅保留页面层交互编排

### P3: 回归验证与任务工件收口

- Objective:
  - 使用数据安全模块前后端定向回归测试验证本轮重构未破坏行为，并将证据写入任务工件。
- Owned paths:
  - `docs/tasks/data-security-20260408T013422/execution-log.md`
  - `docs/tasks/data-security-20260408T013422/test-report.md`
  - `docs/tasks/data-security-20260408T013422/task-state.json`
- Dependencies:
  - P1、P2 完成
- Deliverables:
  - 完整的执行日志和测试报告
  - 同步为已验证完成的任务状态

## Phase Acceptance Criteria

### P1

- P1-AC1:
  - `DataSecurityStore` 继续保留现有 public API，但内部主要通过 settings policy 与专门 repositories 实现，不再直接承载大段持久化逻辑。
- P1-AC2:
  - 标准挂载场景下的路径/设置收敛逻辑已移入独立策略对象，`store.py` 不再直接嵌入环境策略细节。
- P1-AC3:
  - backup lock 支持正常释放与 stale recovery 区分，活动任务查询失败不再被静默吞掉，相关后端回归测试通过。
- Evidence expectation:
  - 代码 diff、后端 pytest 输出、`execution-log.md` 中的 P1 记录。

### P2

- P2-AC1:
  - `useDataSecurityPage.js` 不再同时承载设置编辑、任务轮询、恢复演练和页面交互确认的所有细节，至少拆出独立 helper 或 sub-hook 组合。
- P2-AC2:
  - `DataSecurity.js` 明显缩小，页面展示按区域拆成独立组件，同时保持现有 `data-testid` 和关键交互契约稳定。
- P2-AC3:
  - 变更原因确认从 Hook 移回页面层，数据安全页面和 Hook 相关前端测试通过。
- Evidence expectation:
  - 代码 diff、前端测试输出、`execution-log.md` 中的 P2 记录。

### P3

- P3-AC1:
  - 后端与前端定向回归命令全部通过。
- P3-AC2:
  - `execution-log.md` 记录每个 phase 的改动路径、验证命令、覆盖的 acceptance ids 和剩余风险。
- P3-AC3:
  - `test-report.md` 与 `task-state.json` 中的最终状态一致，并通过完成检查。
- Evidence expectation:
  - `execution-log.md`、`test-report.md`、`task-state.json`、完成检查脚本输出。

## Done Definition

- P1、P2、P3 全部完成
- P1-AC1 ~ P1-AC3、P2-AC1 ~ P2-AC3、P3-AC1 ~ P3-AC3 全部有证据
- 数据安全后端 API、`DataSecurityStore` 公开接口和前端页面核心行为保持稳定
- 本轮没有引入 fallback、mock 路径或静默降级

## Blocking Conditions

- 数据安全相关 pytest 或前端 Jest 基线无法运行
- 发现必须改动数据安全路由契约才能继续拆分
- 发现 `DataSecurityStore` 的外部依赖面比当前识别结果更广，且无法通过 facade 保持兼容
- 发现测试环境缺少必要依赖，无法完成最小可信验证
