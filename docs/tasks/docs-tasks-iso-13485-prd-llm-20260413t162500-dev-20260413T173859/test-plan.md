# WS05 编码测试计划

- Task ID: `docs-tasks-iso-13485-prd-llm-20260413t162500-dev-20260413T173859`
- Created: `2026-04-13T17:38:59`
- Workspace: `D:\ProjectPackage\RagflowAuth`
- User Request: `参考 docs/tasks/iso-13485-prd-llm-20260413T162500/development-docs/WS05-equipment-metrology-maintenance.md 开发设备全生命周期、计量与维护保养功能`

## Test Scope

本次验证覆盖：

- WS05 后端 schema、服务、路由、提醒、导出与审计。
- WS05 前端三张页面的列表加载、创建、状态/审批动作、错误提示。
- 任务工件的结构完整性与状态同步。

以下内容显式不在本次测试范围：

- `WS02` 拥有的路由接入与导航展示。
- `permission_models.py` 驱动的细粒度 capability 发放。
- 真实附件上传存储与外部文件服务。

## Environment

- OS: Windows PowerShell，工作目录 `D:\ProjectPackage\RagflowAuth`
- Python 测试命令在仓库根目录运行。
- 前端测试命令在 `fronted/` 目录运行。
- 后端使用临时 SQLite 数据库夹具，不依赖远端服务。
- 前端使用 Jest + React Testing Library 运行组件级真实渲染。

## Accounts and Fixtures

- 后端 API 测试需要至少 1 个 admin 用户和 1 个普通责任人/执行人夹具。
- 前端页面测试使用 mocked `useAuth()` 返回 admin 用户。
- 若缺少 `pytest`、Node 依赖或 `react-scripts`，测试必须直接失败并记录为阻断前提。

## Commands

1. `python "C:\Users\BJB110\.codex\skills\spec-driven-delivery\scripts\validate_artifacts.py" --cwd "D:\ProjectPackage\RagflowAuth" --tasks-root "docs/tasks" --task-id "docs-tasks-iso-13485-prd-llm-20260413t162500-dev-20260413T173859"`
   Expected success signal: 输出 `Artifacts validated successfully` 或等价成功信息并返回 0。

2. `python -m pytest backend/tests/test_equipment_api_unit.py backend/tests/test_metrology_api_unit.py backend/tests/test_maintenance_api_unit.py backend/tests/test_dependencies_unit.py`
   Expected success signal: 所有用例通过，返回 0，无 failed/error。

3. `npm test -- --watch=false --runInBand src/pages/EquipmentLifecycle.test.js src/pages/MetrologyManagement.test.js src/pages/MaintenanceManagement.test.js`
   Expected success signal: 三组页面测试全部通过，返回 0，无 failed/error。

4. `python "C:\Users\BJB110\.codex\skills\spec-driven-delivery\scripts\validate_test_report.py" --cwd "D:\ProjectPackage\RagflowAuth" --tasks-root "docs/tasks" --task-id "docs-tasks-iso-13485-prd-llm-20260413t162500-dev-20260413T173859"`
   Expected success signal: `test-report.md` 结构合法并返回 0。

## Test Cases

### T1: 后端设备生命周期闭环

- Covers: P1-AC1, P1-AC4
- Level: unit/integration
- Command: `python -m pytest backend/tests/test_equipment_api_unit.py`
- Expected: 能创建设备主档，完成验收/投用/报废等状态动作，并写入状态留痕与审计事件。

### T2: 后端计量记录、审批与导出

- Covers: P1-AC2, P1-AC4
- Level: unit/integration
- Command: `python -m pytest backend/tests/test_metrology_api_unit.py`
- Expected: 能创建计量记录、保存附件引用、完成确认/批准、导出记录，并在必要时回写设备状态。

### T3: 后端维护记录、审批与导出

- Covers: P1-AC2, P1-AC4
- Level: unit/integration
- Command: `python -m pytest backend/tests/test_maintenance_api_unit.py`
- Expected: 能创建维护计划/执行记录、完成批准、导出记录，并保留审计事件。

### T4: 提醒事件派发

- Covers: P1-AC3
- Level: unit/integration
- Command: `python -m pytest backend/tests/test_equipment_api_unit.py backend/tests/test_metrology_api_unit.py backend/tests/test_maintenance_api_unit.py`
- Expected: 到期窗口命中时会创建 `equipment_due_soon`、`metrology_due_soon`、`maintenance_due_soon` 站内信任务；recipient 或 channel 缺失时接口直接失败。

### T5: 前端设备页面交互

- Covers: P2-AC1, P2-AC2, P2-AC3, P2-AC4
- Level: component
- Command: `npm test -- --watch=false --runInBand src/pages/EquipmentLifecycle.test.js`
- Expected: 页面能加载列表、提交新建设备、触发状态动作/提醒动作，并在失败时显示错误提示。

### T6: 前端计量页面交互

- Covers: P2-AC1, P2-AC2, P2-AC4
- Level: component
- Command: `npm test -- --watch=false --runInBand src/pages/MetrologyManagement.test.js`
- Expected: 页面能加载记录、创建计量记录、执行确认/批准动作，并显示成功或错误反馈。

### T7: 前端维护页面交互

- Covers: P2-AC1, P2-AC2, P2-AC4
- Level: component
- Command: `npm test -- --watch=false --runInBand src/pages/MaintenanceManagement.test.js`
- Expected: 页面能加载记录、创建维护记录、执行批准/提醒动作，并显示导出/错误反馈。

### T8: 工件与状态一致性

- Covers: P3-AC1, P3-AC2, P3-AC3
- Level: workflow
- Command: `python "C:\Users\BJB110\.codex\skills\spec-driven-delivery\scripts\validate_artifacts.py" --cwd "D:\ProjectPackage\RagflowAuth" --tasks-root "docs/tasks" --task-id "docs-tasks-iso-13485-prd-llm-20260413t162500-dev-20260413T173859"`
- Expected: PRD、test-plan、task-state、execution-log、test-report 结构完整且稳定 id 覆盖正确。

## Coverage Matrix

| Case ID | Area | Scenario | Level | Acceptance IDs | Evidence |
| --- | --- | --- | --- | --- | --- |
| T1 | equipment backend | 设备主档创建与生命周期流转 | unit/integration | P1-AC1, P1-AC4 | `test-report.md#T1` |
| T2 | metrology backend | 计量记录创建、确认、批准、导出 | unit/integration | P1-AC2, P1-AC4 | `test-report.md#T2` |
| T3 | maintenance backend | 维护记录创建、批准、导出 | unit/integration | P1-AC2, P1-AC4 | `test-report.md#T3` |
| T4 | notification backend | 临期提醒事件派发与失败条件 | unit/integration | P1-AC3 | `test-report.md#T4` |
| T5 | equipment frontend | 设备页面加载、提交、动作提示 | component | P2-AC1, P2-AC2, P2-AC3, P2-AC4 | `test-report.md#T5` |
| T6 | metrology frontend | 计量页面加载、提交、审批提示 | component | P2-AC1, P2-AC2, P2-AC4 | `test-report.md#T6` |
| T7 | maintenance frontend | 维护页面加载、提交、提醒/导出提示 | component | P2-AC1, P2-AC2, P2-AC4 | `test-report.md#T7` |
| T8 | workflow artifacts | 任务工件和状态一致性 | workflow | P3-AC1, P3-AC2, P3-AC3 | `test-report.md#T8` |

## Evaluator Independence

- Mode: blind-first-pass
- Validation surface: real-runtime
- Required tools: `python`, `pytest`, `npm`, `react-scripts`, `jest`
- First-pass readable artifacts: prd.md, test-plan.md
- Withheld artifacts: execution-log.md, task-state.json
- Real environment expectation: 在真实仓库和本地测试运行时中执行；后端走真实 FastAPI/TestClient + SQLite，前端走真实 React 渲染测试，不允许伪造接口成功。
- Escalation rule: 在 tester 写出首轮结论前，不查看 `execution-log.md` 与 `task-state.json`；若发现页面无法通过已定义入口访问，应按“路由接入属于 WS02 owner 范围”记录为上下文事实，而不是自行改路由。

## Pass / Fail Criteria

- Pass when:
  - `validate_artifacts.py` 通过。
  - 后端与前端全部指定命令返回 0。
  - `test-report.md` 能对应到每个 acceptance id 的证据。
- Fail when:
  - 任一命令失败、跳过或缺少先决条件。
  - 提醒、导出、审计、确认/批准任一关键路径未真正实现。
  - 页面靠 mock 成功值或后端靠静默降级通过测试。

## Regression Scope

- `backend/app/main.py` 路由注册未破坏现有公开路径。
- `backend/app/dependency_factory.py` 新增依赖不影响已有服务装配。
- `backend/database/schema/ensure.py` 反复执行保持幂等。
- 现有通知框架在新增 WS05 事件后，原有操作审批通知行为不回归。

## Reporting Notes

结果写入 `test-report.md`。

测试者必须独立于执行者，首轮只依赖 `prd.md` 与 `test-plan.md`。若发现 `WS02` 未接路由导致缺少浏览器入口，应如实记录为边界事实，而不是把该问题改成“测试通过”。
