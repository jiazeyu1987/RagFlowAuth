# 审批域重构一期执行计划

## 文档定位

本文档是 [系统重构修改计划](./system-refactor-plan-2026-04.md) 中“阶段 1：审批域重构”的细化执行版本。

放在 `docs/exec-plans/active/` 的原因：

- 它是跨 `service/store/router/tests` 的执行计划，不是单点技术债记录
- 它需要持续推进和回写状态，不适合放在 `docs/product-specs/` 或 `docs/design-docs/`
- 它的粒度高于 `docs/tasks/` 中的单次任务工件，适合作为后续拆分 PR 和任务的上位文档

## 背景与目标

当前审批域已经出现“初步分层已存在，但主服务和主 store 仍过厚”的典型阶段性问题：

- `backend/services/operation_approval/service.py` 约 987 行
- `backend/services/operation_approval/store.py` 约 1080 行
- `backend/services/operation_approval/migration_service.py` 约 487 行
- `backend/tests/test_operation_approval_service_unit.py` 约 1515 行

一期目标不是重写审批系统，而是在不破坏外部行为的前提下，把审批域收敛成“可继续维护、可继续验证、可继续拆分”的状态。

本期只解决以下问题：

- 把 `OperationApprovalService` 收敛为真正的 facade，而不是继续承载工作流构建、请求创建、查询聚合、签名动作、执行编排、迁移入口等多类职责
- 把 `OperationApprovalStore` 从“单类统管所有表读写”拆成更清晰的 repository 组合，同时保留稳定入口
- 收敛事务边界，尤其补上“创建请求时状态写入与事件写入分离”的一致性风险
- 把审批域测试从单个超大文件拆成按职责分层的测试集合，降低后续重构阻力

## 当前问题边界

### 1. `OperationApprovalService` 仍是事实上的超级服务

当前 `service.py` 同时承担了：

- 工作流步骤校验与标准化：`_build_workflow_steps()`
- 工作流展示组装：`_workflow_member_view()`、`_enrich_workflow()`
- 请求步骤物化与直属主管解析：`_resolve_direct_manager()`、`_materialize_request_steps()`
- 请求查询视图拼装：`_to_brief()`、`_enrich_request_steps()`、`_enrich_request_events()`
- 请求创建编排：`create_request()`
- 审批动作编排：`approve_request()`、`reject_request()`、`withdraw_request()`
- 执行、审计、通知和迁移入口协调：`_execute_request()`、`_audit_*()`、`_notify_*()`、`migrate_legacy_document_reviews()`

这说明虽然 `decision_service.py`、`execution_service.py`、`notification_service.py`、`migration_service.py` 已经存在，但主服务仍然是主要复杂度承载体。

### 2. `OperationApprovalStore` 混合了多种持久化职责

当前 `store.py` 同时覆盖：

- 工作流配置读写
- 请求聚合根创建与导入
- 请求详情查询与列表查询
- 步骤与审批人状态推进
- 事件写入
- 附件清理状态更新
- 统计查询
- 历史迁移记录读写

这使得后续任何一个需求只要涉及审批域持久化，几乎都会继续放大 `store.py`。

### 3. 事务边界仍不均匀

当前审批动作路径已经通过 `run_in_transaction()` 包裹关键状态推进，但创建路径仍然存在边界不一致：

- `create_request()` 先调用 `store.create_request()`
- 随后再分散写入 `request_submitted`、`step_activated`、`step_auto_skipped` 等事件

这意味着“请求已创建但初始事件未完整写入”的半完成状态仍然可能出现。

### 4. 测试覆盖存在，但结构不利于继续重构

当前测试不是缺失，而是过度集中：

- `test_operation_approval_service_unit.py` 同时覆盖工作流、创建、审批动作、执行、通知、迁移委托、异常回滚等多类主题
- router 契约测试和迁移/通知修复测试已经独立出来，但 service 主测试文件仍然承担过多上下文

这会导致后续只想改一小块时，也必须在一个超大测试夹具中定位和维护。

## 本期范围

### 纳入范围

- `backend/services/operation_approval/service.py`
- `backend/services/operation_approval/store.py`
- `backend/services/operation_approval/decision_service.py`
- `backend/services/operation_approval/migration_service.py`
- `backend/services/operation_approval/execution_service.py`
- `backend/services/operation_approval/notification_service.py`
- `backend/services/operation_approval/__init__.py`
- `backend/app/modules/operation_approvals/router.py`
- 审批域相关后端单元测试

### 明确不在本期范围

- 不改审批 API 路径和返回 envelope
- 不改审批状态枚举、事件类型、操作类型的对外语义
- 不引入新的 fallback、兼容分支或静默降级
- 不改知识库上传/删除/新建/删除等 handler 的业务规则
- 不做数据库技术栈替换，不做跨模块目录重命名
- 不把审批域重构扩散到前端页面结构

## 不可破坏的外部契约

### 1. 路由契约必须保持稳定

`backend/app/modules/operation_approvals/router.py` 中以下接口路径与语义本期不得改动：

- `GET /operation-approvals/workflows`
- `PUT /operation-approvals/workflows/{operation_type}`
- `GET /operation-approvals/requests`
- `GET /operation-approvals/requests/{request_id}`
- `GET /operation-approvals/stats`
- `POST /operation-approvals/requests/{request_id}/approve`
- `POST /operation-approvals/requests/{request_id}/reject`
- `POST /operation-approvals/requests/{request_id}/withdraw`
- `GET /operation-approvals/todos`

以下 envelope 结构也必须保持稳定：

- 工作流修改返回 `{"result": {"message", "operation_type"}}`
- 动作类接口返回 `{"result": {"message", "request_id", "status"}}`

### 2. 服务公开入口必须保持稳定

本期允许内部拆分，但以下公开入口保持可用：

- `OperationApprovalService`
- `OperationApprovalStore`
- `OperationApprovalServiceError`
- `OPERATION_TYPE_LABELS`
- `SUPPORTED_OPERATION_TYPES`

原因是这些符号已通过 `backend/services/operation_approval/__init__.py` 暴露，并被依赖注入和测试引用。

### 3. 跨模块调用语义保持稳定

以下调用方不应因本期重构而感知结构变化：

- `backend/app/dependencies.py` 中的服务装配
- 调用 `create_request()` 的文档与知识库相关路由
- 已存在的 router 单元测试
- 已存在的审批状态流转测试

### 4. 持久化语义保持稳定

以下内容本期只允许“重组写法”，不允许“修改业务含义”：

- `operation_approval_*` 表的主业务语义
- 审批状态流转规则
- 事件类型字符串
- 审批动作对签名、审计、通知、执行的时序语义

## 目标结构

一期结束后，审批域目标结构如下：

```text
backend/services/operation_approval/
  __init__.py
  service.py                      # 对外 facade 和依赖装配
  decision_service.py             # 保留，继续作为状态推进核心
  execution_service.py            # 保留
  notification_service.py         # 保留
  migration_service.py            # 保留，但边界更清晰
  workflow_builder.py             # 新增，负责工作流入参标准化与展示投影
  request_materializer.py         # 新增，负责步骤物化与直属主管解析
  query_service.py                # 新增，负责 brief/detail/stats 读模型
  action_service.py               # 新增，负责 approve/reject/withdraw 编排
  repositories/
    workflow_repository.py
    request_repository.py
    step_repository.py
    event_repository.py
    artifact_repository.py
    migration_repository.py
```

补充说明：

- `OperationApprovalService` 保留为 facade，不直接删除
- `OperationApprovalStore` 保留为稳定入口，但内部降级为“连接工厂 + 事务入口 + repository 聚合器”
- `decision_service.py` 不重写，继续作为审批状态机的核心 seam
- `execution_service.py` 和 `notification_service.py` 本期只做配合性调整，不做职责扩张

## 拆分步骤

### 1. 先冻结契约与补齐表征测试

目的：

- 把本期“不能改坏什么”固化成测试，再开始拆分

具体动作：

- 保持 `test_operation_approval_router_unit.py` 作为 API 契约基线
- 为 `create_request()` 增加一组表征测试，覆盖初始事件写入与自动进入下一步/自动执行场景
- 保持 `approve/reject/withdraw` 的回滚测试作为事务基线
- 补一组服务装配测试，确保 facade 拆分后公开入口仍可被依赖注入创建

交付结果：

- 后续每一步拆分都有最小回归网

### 2. 先拆 `store.py`，但保留 `OperationApprovalStore` 外壳

目的：

- 在不一次性改动所有调用方的前提下，把持久化职责拆出清晰边界

具体动作：

- 新增 `repositories/workflow_repository.py`
  - 负责 `get_workflow()`、`list_workflows()`、`upsert_workflow()`
- 新增 `repositories/request_repository.py`
  - 负责 `create_request()`、`import_request()`、`get_request()`、`list_requests()`、统计相关查询
- 新增 `repositories/step_repository.py`
  - 负责 `get_active_step()`、`get_step_approver()`、`mark_step_approver_action()`、`mark_remaining_step_approvers()`、`set_step_status()`
- 新增 `repositories/event_repository.py`
  - 负责 `add_event()`
- 新增 `repositories/artifact_repository.py`
  - 负责 `mark_artifact_cleanup()`
- 新增 `repositories/migration_repository.py`
  - 负责 `get_legacy_migration()`、`record_legacy_migration()`
- `OperationApprovalStore` 保留 `db_path`、`_conn()`、`run_in_transaction()`，并作为 repository 聚合入口

本步原则：

- 先抽数据访问职责，不同步改业务语义
- 能通过代理保持兼容的方法先保留，避免一次性大改调用点
- 所有 repository 优先接受显式 `conn`，沿用现有事务模型

### 3. 拆出“请求创建与步骤物化”链路

目的：

- 先解决 `create_request()` 复杂度和事务边界不一致问题

具体动作：

- 新增 `workflow_builder.py`
  - 承接 `_build_workflow_steps()`、`_workflow_member_view()`、`_enrich_workflow()`
- 新增 `request_materializer.py`
  - 承接 `_resolve_direct_manager()`、`_snapshot_workflow_steps()`、`_materialize_request_steps()`
- 将 `create_request()` 中以下 DB 写入收敛为单次事务
  - 请求主体写入
  - 初始步骤写入
  - `request_submitted` 事件写入
  - `step_member_auto_skipped` / `step_auto_skipped` 事件写入
  - 初始 `step_activated` 事件写入

关键要求：

- 事务提交前不做通知、不做审计、不做外部执行
- 事务提交后再触发 `_audit_submit()`、`_notify_submission()`、自动执行路径

这是本期最优先的实质性改进点，因为它直接降低“创建成功但事件缺失”的一致性风险。

### 4. 把审批动作从 facade 中抽成 action 编排层

目的：

- 让 `approve/reject/withdraw` 的复杂度不再继续堆在 `service.py`

具体动作：

- 新增 `action_service.py`
  - 封装签名校验与签名创建
  - 调用 `decision_service.py` 执行状态推进
  - 在事务提交后统一协调审计、通知、执行、清理
- `OperationApprovalService.approve_request()`、`reject_request()`、`withdraw_request()` 改为薄转发

注意：

- `decision_service.py` 保持为状态推进真相源，不把规则重新搬进 action service
- action service 负责“编排”，decision service 负责“状态机”

### 5. 把查询读模型从 facade 中抽离

目的：

- 避免 brief/detail/stats 与写路径继续耦合

具体动作：

- 新增 `query_service.py`
  - 承接 `_request_visible_to_user()`、`_to_brief()`、`_enrich_request_steps()`、`_enrich_request_events()`、`get_stats_for_user()`
- `OperationApprovalService` 保留原 public method，但内部直接委托给 query service

收益：

- 读路径以后新增字段时，不必继续触碰动作服务
- 测试可以按读模型独立组织

### 6. 收紧迁移边界，但不在本期重写迁移逻辑

目的：

- 防止 `migration_service.py` 继续把遗留兼容逻辑反向污染主服务

具体动作：

- 保持 `migrate_legacy_document_reviews()` 作为独立入口
- `migration_service.py` 只依赖明确注入的 repository、user resolver、deps
- 不再新增从 facade 借用私有 helper 的路径
- 若需要补能力，优先在迁移服务内部或显式协作者中完成

本步强调：

- 一期不追求消灭历史迁移逻辑
- 一期只要求把迁移逻辑限制在迁移边界内

### 7. 最后拆测试文件，而不是边拆边散

目的：

- 在结构基本稳定后再拆测试，避免重复搬运测试夹具

建议拆分结果：

- `backend/tests/test_operation_approval_workflow_unit.py`
- `backend/tests/test_operation_approval_submission_unit.py`
- `backend/tests/test_operation_approval_actions_unit.py`
- `backend/tests/test_operation_approval_query_unit.py`
- `backend/tests/test_operation_approval_execution_unit.py`
- 保留 `test_operation_approval_router_unit.py`
- 保留 `test_operation_approval_notification_migration_unit.py`

拆分原则：

- 一个测试文件只覆盖一个主要职责面
- 公共夹具下沉到本地 helper，而不是继续复制超大 stub 集合
- 不为了拆文件而改变业务断言

## 事务边界策略

一期统一采用以下原则：

### 事务内

- 请求状态推进
- 步骤状态推进
- 审批人状态更新
- 事件写入
- 结果字段写入

### 事务外

- 审计日志写入
- 外部通知发送与分发
- 业务执行 handler 调用
- 工件清理

### 明确禁止

- 不在事务中做网络调用或外部系统调用
- 不用新的 fallback 掩盖事务失败
- 不把“事件写入失败但主状态已提交”视为可接受默认行为

## 测试与验证计划

### 单元测试

- workflow builder 输入标准化与非法成员校验
- request materializer 对直属主管、去重、自动跳过的物化逻辑
- action service 对 approve/reject/withdraw 三条路径的编排
- repository 级 focused tests，尤其是步骤推进和事件写入
- query service 对 brief/detail/stats 的投影结果

### 集成回归

- 创建申请
- 审批通过
- 审批驳回
- 申请撤回
- 自动跳过所有审批层后直接执行
- 执行成功
- 执行失败
- 迁移入口委托

### 契约验证

- router response envelope 不变
- `OperationApprovalService` public method 名称与行为保持兼容
- `OperationApprovalStore` 仍可作为依赖注入入口使用

## 风险与回滚

### 主要风险

- repository 拆分后若事务连接传递不一致，容易出现“读到旧状态”或“部分提交”
- 创建链路事务收口时，若遗漏初始事件写入，容易破坏通知与审计时序
- 过早拆测试可能让回归网短时间变弱
- 迁移服务若误吸收主服务新抽象，可能形成新的隐式耦合

### 回滚点

- 每一步按 PR 粒度推进，避免跨多个职责面一次性落地
- 在 facade 和 store 外壳仍保留的前提下，可以逐步回退内部委托实现
- 若创建链路事务收口出现问题，优先回滚 submission 相关改动，不影响 query 与 workflow 拆分

## 完成标准

满足以下条件即可认定一期完成：

1. `service.py` 明显缩小，并以 facade/委托为主，不再承载大段工作流构建、物化、查询与动作细节。
2. `store.py` 不再直接承载全部表级读写逻辑，主要职责收敛为连接、事务和 repository 聚合。
3. 创建请求链路中的主状态写入与初始事件写入进入统一事务边界。
4. `decision_service.py` 继续作为状态推进真相源，未被 action 编排层绕开。
5. router 路径、返回 envelope、服务公开入口保持兼容。
6. 审批域测试按职责拆分完成，核心状态流转和回滚测试维持通过。

## 后续建议

如果要把一期计划继续落实到实际开发任务，下一步建议按 PR 粒度再拆成 4 到 6 个执行单：

1. repository 拆分 PR
2. submission 事务收口 PR
3. action service 抽离 PR
4. query service 抽离 PR
5. migration 边界收紧 PR
6. 测试文件拆分 PR
