# PRD

- Task ID: `task-844208f36c-20260408T004044`
- Created: `2026-04-08T00:40:44`
- Workspace: `D:\ProjectPackage\RagflowAuth`
- User Request: `持续推进前后端重构，按系统重构计划实施审批域后端与高优先前端热点的局部重构，保持现有行为和契约稳定`

## Goal

在不破坏审批域 API、审批状态机语义和前端页面现有行为的前提下，继续推进审批相关前后端的局部重构，把审批后端服务进一步收敛为 facade，把审批前端页面/Hook 中的混合职责继续拆开，并用现有回归测试证明行为保持稳定。

## Scope

- 审批域后端：
  - `backend/services/operation_approval/service.py`
  - `backend/services/operation_approval/store.py`
  - `backend/services/operation_approval/repositories/*`
  - `backend/services/operation_approval/action_service.py`
  - `backend/services/operation_approval/query_service.py`
  - 审批域相关测试
- 审批相关前端：
  - `fronted/src/pages/ApprovalCenter.js`
  - `fronted/src/pages/ApprovalConfig.js`
  - `fronted/src/features/operationApproval/*`
  - 审批相关前端测试
- 任务工件与执行证据：
  - `docs/tasks/task-844208f36c-20260408T004044/*`

## Non-Goals

- 不改审批 API 路径、响应 envelope、错误码语义
- 不改审批操作类型、审批状态、事件类型的业务含义
- 不引入 fallback、mock 路径或静默降级
- 不扩散到 `data_security`、通知中心、文档预览、权限模型等其他阶段计划
- 不做样式重设计或交互改版

## Preconditions

- 本地 Python 与 `pytest` 可运行
- 前端 `react-scripts test` 可运行
- 审批域现有回归测试可作为行为基线
- 仓库已有审批相关前后端测试文件

如果上述前提缺失，必须停止并记录到 `task-state.json.blocking_prereqs`。

## Impacted Areas

- 后端依赖装配：
  - `backend/app/dependencies.py`
- 审批路由契约：
  - `backend/app/modules/operation_approvals/router.py`
- 审批状态推进、执行、迁移、通知协调：
  - `backend/services/operation_approval/*`
- 知识库/文档等调用审批服务的后端路由与测试
- 前端审批配置页与审批中心页
- 审批相关前端 Hook/页面测试

## Phase Plan

### P1: 审批后端服务收敛

- Objective:
  - 继续把 `OperationApprovalService` 收敛为 facade，拆出动作编排与查询读模型服务。
- Owned paths:
  - `backend/services/operation_approval/service.py`
  - `backend/services/operation_approval/action_service.py`
  - `backend/services/operation_approval/query_service.py`
  - `backend/services/operation_approval/store.py`
  - `backend/services/operation_approval/repositories/*`
  - `backend/tests/test_operation_approval_service_unit.py`
- Dependencies:
  - 现有 `decision_service.py`
  - 现有 `execution_service.py`
  - 现有 `migration_service.py`
  - 已完成的 store repository 拆分与创建链路事务收口
- Deliverables:
  - 新增 `action_service.py`
  - 新增 `query_service.py`
  - `service.py` 改为委托动作/查询实现
  - 审批域后端回归测试通过

### P2: 审批前端页面与 Hook 收敛

- Objective:
  - 把审批配置页和审批中心页中的常量、格式化、展示拼装和页面状态协调拆开，降低页面与 Hook 的混合职责。
- Owned paths:
  - `fronted/src/pages/ApprovalCenter.js`
  - `fronted/src/pages/ApprovalConfig.js`
  - `fronted/src/features/operationApproval/*`
  - `fronted/src/pages/ApprovalCenter.test.js`
  - `fronted/src/pages/ApprovalConfig.test.js`
  - `fronted/src/features/operationApproval/useApprovalCenterPage.test.js`
  - `fronted/src/features/operationApproval/useApprovalConfigPage.test.js`
- Dependencies:
  - 现有 `operationApprovalApi`
  - 现有审批页测试覆盖
- Deliverables:
  - 审批前端新增 helper/component 模块
  - 页面文件与 Hook 文件职责更单一
  - 审批前端测试通过

### P3: 验证与证据收口

- Objective:
  - 用后端与前端的定向回归命令验证本轮重构未破坏现有行为，并把证据写入任务工件。
- Owned paths:
  - `docs/tasks/task-844208f36c-20260408T004044/execution-log.md`
  - `docs/tasks/task-844208f36c-20260408T004044/test-report.md`
  - `docs/tasks/task-844208f36c-20260408T004044/task-state.json`
- Dependencies:
  - P1、P2 完成
- Deliverables:
  - 记录执行证据与测试结果
  - 状态文件同步到已执行/已验证状态

## Phase Acceptance Criteria

### P1

- P1-AC1:
  - `OperationApprovalService` 继续保持现有 public API，但 `approve/reject/withdraw` 与列表/详情/统计逻辑不再由 facade 直接实现主要细节。
- P1-AC2:
  - 新增专门的 action/query service，且现有审批路由、知识库/文档调用链和审批状态流转测试保持通过。
- P1-AC3:
  - 请求创建、审批、驳回、撤回、执行启动相关的事务回滚测试保持通过。
- Evidence expectation:
  - 代码 diff、后端 pytest 输出、`execution-log.md` 中的 P1 记录。

### P2

- P2-AC1:
  - 审批中心和审批配置相关的常量、格式化或展示拼装逻辑从页面主文件中抽离，页面文件更偏向 UI 壳层。
- P2-AC2:
  - Hook 中的非必要混合职责被进一步拆开，新增的 helper 或组件有对应测试覆盖或被现有测试覆盖。
- P2-AC3:
  - 审批前端页面与 Hook 的现有行为保持不变，相关前端测试通过。
- Evidence expectation:
  - 代码 diff、前端测试输出、`execution-log.md` 中的 P2 记录。

### P3

- P3-AC1:
  - 后端和前端定向验证命令全部通过。
- P3-AC2:
  - `execution-log.md` 记录每个 phase 的变更路径、验证命令、接受项覆盖和剩余风险。
- P3-AC3:
  - `test-report.md` 与 `task-state.json` 与最终执行结果一致。
- Evidence expectation:
  - `execution-log.md`、`test-report.md`、状态同步脚本输出。

## Done Definition

- P1、P2、P3 都完成
- P1-AC1 ~ P1-AC3、P2-AC1 ~ P2-AC3、P3-AC1 ~ P3-AC3 全部有证据
- 审批后端路由契约、审批状态机语义、前端审批页面现有行为保持稳定
- 本轮没有引入 fallback、mock 或静默降级

## Blocking Conditions

- 审批域现有测试无法运行或基线已失效
- 前端测试环境不可用且无法做同等可信替代验证
- 发现审批 API 契约必须变更才能继续拆分
- 发现新的跨域耦合导致必须扩散到非本轮范围模块
