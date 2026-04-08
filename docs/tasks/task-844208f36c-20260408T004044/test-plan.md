# Test Plan

- Task ID: `task-844208f36c-20260408T004044`
- Created: `2026-04-08T00:40:44`
- Workspace: `D:\ProjectPackage\RagflowAuth`
- User Request: `持续推进前后端重构，按系统重构计划实施审批域后端与高优先前端热点的局部重构，保持现有行为和契约稳定`

## Test Scope

验证审批域后端服务收敛和审批相关前端页面/Hook 重构后，审批 API 契约、审批状态流转、创建链路回滚、审批动作、审批详情展示与审批配置编辑行为保持稳定。

不在本次测试范围：

- `data_security`
- 文档预览
- 通知中心整体重构
- 权限模型整体重构

## Environment

- Windows PowerShell
- Python 3.12
- 仓库根目录：`D:\ProjectPackage\RagflowAuth`
- 前端目录：`D:\ProjectPackage\RagflowAuth\fronted`
- 后端测试依赖已安装
- 前端 `react-scripts test` 可运行

## Accounts and Fixtures

- 后端审批单元测试自带 `admin_user`、`approver_1`、`approver_2`、`editor_user` 等夹具
- 前端审批测试自带 `useAuth`、`operationApprovalApi`、`electronicSignatureApi` mock
- 无需真实外部邮件、钉钉或数据库服务

如果上述测试夹具不可用，测试必须失败并记录阻塞前提。

## Commands

1. `python -m pytest backend/tests/test_operation_approval_service_unit.py`
   - 期望：36 个审批服务单测通过，无失败
2. `python -m pytest backend/tests/test_operation_approval_router_unit.py backend/tests/test_operation_approval_notification_migration_unit.py`
   - 期望：审批路由契约与通知迁移测试通过
3. `python -m pytest backend/tests/test_documents_unified_router_unit.py backend/tests/test_knowledge_admin_routes_unit.py backend/tests/test_knowledge_upload_route_permissions_unit.py backend/tests/test_route_request_models_unit.py backend/tests/test_tenant_db_isolation_unit.py`
   - 期望：调用审批服务的相关后端链路测试通过
4. `npm test -- --runInBand --watch=false src/features/operationApproval/useApprovalConfigPage.test.js src/features/operationApproval/useApprovalCenterPage.test.js src/pages/ApprovalConfig.test.js src/pages/ApprovalCenter.test.js`
   - 期望：审批相关前端 Hook 与页面测试通过

## Test Cases

### T1: 审批后端动作与查询回归

- Covers: P1-AC1, P1-AC2, P1-AC3
- Level: unit/integration
- Command: `python -m pytest backend/tests/test_operation_approval_service_unit.py`
- Expected: 审批创建、审批通过、驳回、撤回、执行、回滚、迁移委托全部通过。

### T2: 审批后端契约与调用链回归

- Covers: P1-AC2
- Level: unit/integration
- Command: `python -m pytest backend/tests/test_operation_approval_router_unit.py backend/tests/test_operation_approval_notification_migration_unit.py backend/tests/test_documents_unified_router_unit.py backend/tests/test_knowledge_admin_routes_unit.py backend/tests/test_knowledge_upload_route_permissions_unit.py backend/tests/test_route_request_models_unit.py backend/tests/test_tenant_db_isolation_unit.py`
- Expected: 路由 envelope、知识库/文档调用链、租户隔离行为不变。

### T3: 审批前端 Hook 与页面回归

- Covers: P2-AC1, P2-AC2, P2-AC3
- Level: component/unit
- Command: `npm test -- --runInBand --watch=false src/features/operationApproval/useApprovalConfigPage.test.js src/features/operationApproval/useApprovalCenterPage.test.js src/pages/ApprovalConfig.test.js src/pages/ApprovalCenter.test.js`
- Expected: 审批配置编辑、审批中心签名操作、培训门禁提示、显示过滤等行为保持通过。

### T4: 任务证据一致性检查

- Covers: P3-AC1, P3-AC2, P3-AC3
- Level: manual
- Command: `人工核对 execution-log.md / test-report.md / task-state.json`
- Expected: 三份工件对 phase 状态、命令与结果描述一致。

## Coverage Matrix

| Case ID | Area | Scenario | Level | Acceptance IDs | Evidence |
| --- | --- | --- | --- | --- | --- |
| T1 | 审批后端 | 动作、查询、回滚、执行、迁移回归 | unit/integration | P1-AC1, P1-AC2, P1-AC3 | `test-report.md` |
| T2 | 审批后端调用链 | 路由契约、知识库/文档调用链、租户隔离 | unit/integration | P1-AC2 | `test-report.md` |
| T3 | 审批前端 | Hook 与页面行为回归 | component/unit | P2-AC1, P2-AC2, P2-AC3 | `test-report.md` |
| T4 | 任务工件 | 证据与状态一致性 | manual | P3-AC1, P3-AC2, P3-AC3 | `execution-log.md`, `test-report.md` |

## Evaluator Independence

- Mode: blind-first-pass
- Validation surface: real-runtime
- Required tools: `pytest`, `react-scripts test`
- First-pass readable artifacts: prd.md, test-plan.md
- Withheld artifacts: execution-log.md, task-state.json
- Real environment expectation: 在真实仓库中运行后端 pytest 和前端 React 测试，不使用额外 mock 替代现有测试夹具。
- Escalation rule: 在初次测试结论产出前，不查看 `execution-log.md` 和 `task-state.json`。

## Pass / Fail Criteria

- Pass when:
  - T1、T2、T3 命令全部通过
  - T4 人工核对无冲突
  - 没有新增 fallback、mock、静默降级路径
- Fail when:
  - 任一命令失败
  - 审批契约、审批状态机语义、前端页面行为出现回归
  - 工件记录与实际执行结果不一致

## Regression Scope

- 审批域路由层
- 调用审批服务的知识库/文档后端路径
- 审批前端页面与 Hook
- 租户控制库与租户执行库隔离行为

## Reporting Notes

把命令、结果、失败信息和最终结论写入 `test-report.md`。
