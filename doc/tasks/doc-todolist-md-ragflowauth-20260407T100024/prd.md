# Approval Domain Refactor PRD

## Goal

把 `backend/services/operation_approval/service.py` 从高风险的多职责热点收敛成可维护的审批编排层，优先消除一次审批动作被拆成多次独立提交的状态不一致风险，并把执行、通知、审计、历史迁移、审批决策逐步拆成边界清晰的协作者。

## Scope

- `backend/services/operation_approval/service.py`
- `backend/services/operation_approval/store.py`
- `backend/services/operation_approval/*.py` 新增协作者模块
- `backend/tests/test_operation_approval_service_unit.py`
- `backend/tests/test_operation_approval_router_unit.py`

## Non-Goals

- 不修改审批 HTTP 路由契约和 URL。
- 不改知识库、通知中心、电子签名模块的对外接口。
- 不做全仓库级别的依赖装配重写。
- 不引入 fallback、兼容分支、mock 数据或 silent downgrade。

## Preconditions

- 本地 Python 环境可运行 `python -m unittest`。
- `backend.database.schema.ensure.ensure_schema` 可初始化测试库。
- 审批相关单测夹具可在当前仓库下创建受管 `data/` 路径。
- 若以上任一条件失效，必须停止并记录到 `task-state.json.blocking_prereqs`。

## Impacted Areas

- 审批请求创建、审批通过、驳回、撤回、执行开始、执行结束。
- 审批事件日志、审计日志、通知分发、legacy document review 迁移。
- 审批相关后端单测和路由单测。

## Phase Plan

### P1: 收敛审批流事务边界

- Objective: 让批准、驳回、撤回、执行开始/结束等关键状态切换拥有显式事务边界，避免半提交状态。
- Owned paths: `backend/services/operation_approval/service.py`, `backend/services/operation_approval/store.py`, `backend/tests/test_operation_approval_service_unit.py`
- Dependencies: 现有 `OperationApprovalStore` 读写接口、审批单测夹具
- Deliverables: store 显式事务入口；核心写入支持复用同一连接；事务回滚测试

### P2: 拆分执行、通知、审计、迁移协作者

- Objective: 把主 service 中边界清晰且副作用重的职责抽成独立协作者，保留主 service 为编排层。
- Owned paths: `backend/services/operation_approval/service.py`, `backend/services/operation_approval/audit_service.py`, `backend/services/operation_approval/notification_service.py`, `backend/services/operation_approval/execution_service.py`, `backend/services/operation_approval/migration_service.py`, `backend/tests/test_operation_approval_service_unit.py`
- Dependencies: P1 完成后的事务边界；现有通知/审计/执行/迁移行为回归
- Deliverables: 新协作者模块；service 委托接线；迁移委托测试；审批回归通过

### P3: 拆分审批决策协作者

- Objective: 从主 service 中抽出 approve/reject/withdraw 的决策与状态推进逻辑，减少主类对 step/request/approver 的直接操作密度。
- Owned paths: `backend/services/operation_approval/service.py`, `backend/services/operation_approval/decision_service.py`, `backend/tests/test_operation_approval_service_unit.py`
- Dependencies: P1、P2 完成；现有审批状态流转测试
- Deliverables: `ApprovalDecisionService` 或等价协作者；主 service 改为调用决策协作者；现有行为保持不变

### P4: 为 request/step/workflow/event 引入显式数据模型

- Objective: 用稳定的数据模型替代审批域关键路径中的大面积裸 `dict` 透传，降低字段漂移风险。
- Owned paths: `backend/services/operation_approval/types.py`, `backend/services/operation_approval/service.py`, `backend/services/operation_approval/decision_service.py`, `backend/tests/test_operation_approval_service_unit.py`
- Dependencies: P3 完成；审批决策职责已分离
- Deliverables: 新的数据模型类型；关键状态机路径改用显式模型；必要单测

## Phase Acceptance Criteria

### P1

- P1-AC1: 审批通过、驳回、撤回、执行开始/完成的状态写入不再依赖多个独立 `commit()` 串接。
- P1-AC2: 当事件写入失败时，请求、步骤、审批人状态会整体回滚。
- P1-AC3: 审批相关后端单测通过，且执行路径仍保持原行为。
- Evidence expectation: `execution-log.md` 记录改动路径、回滚场景和验证命令。

### P2

- P2-AC1: 执行、通知、审计、legacy 迁移逻辑已从主 service 提取到独立协作者。
- P2-AC2: `OperationApprovalService` 保留审批编排职责，不再直接实现上述四类细节逻辑。
- P2-AC3: 协作者拆分后审批相关单测和路由单测全部通过。
- Evidence expectation: `execution-log.md` 记录新增模块、委托关系和测试结果。

### P3

- P3-AC1: approve/reject/withdraw 的决策逻辑迁入独立协作者，主 service 仅保留输入校验、签名编排和后置副作用触发。
- P3-AC2: 审批决策协作者可在不依赖通知/审计实现细节的前提下独立测试。
- P3-AC3: approve/reject/withdraw 的现有回归测试继续通过。
- Evidence expectation: `execution-log.md` 记录决策协作者边界、覆盖的 acceptance id 和回归结果。

### P4

- P4-AC1: request/step/workflow/event 的关键字段不再主要靠裸字符串 key 在主流程中传播。
- P4-AC2: 至少关键审批路径中的模型字段变更可由类型或构造函数集中约束。
- P4-AC3: 新模型引入后，审批核心单测继续通过。
- Evidence expectation: `execution-log.md` 记录模型引入范围和回归结果。

## Done Definition

- P1-P4 全部完成并各自拥有可追溯证据。
- `backend.tests.test_operation_approval_service_unit` 与 `backend.tests.test_operation_approval_router_unit` 全部通过。
- 主 service 不再同时承载事务边界、执行、通知、审计、迁移和审批决策的全部实现细节。
- 每个 acceptance id 都能在 `execution-log.md` 或 `test-report.md` 中找到证据。

## Blocking Conditions

- 审批相关单测无法运行。
- 迁移或执行路径需要隐藏前提但本地无法发现。
- 为了维持旧行为必须引入 fallback、mock 或兼容分支。
- 改动发现与现有路由契约或持久化 schema 不兼容且无法在本阶段安全处理。
