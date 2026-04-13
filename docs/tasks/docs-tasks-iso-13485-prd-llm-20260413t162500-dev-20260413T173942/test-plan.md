# WS01 测试计划：受控文件基线与合规门禁

- Task ID: `docs-tasks-iso-13485-prd-llm-20260413t162500-dev-20260413T173942`
- Created: `2026-04-13T17:39:42`
- Workspace: `D:\ProjectPackage\RagflowAuth`
- User Request: `参考 docs/tasks/iso-13485-prd-llm-20260413T162500/development-docs/WS01-controlled-doc-baseline.md 开发 WS01 受控文件基线与合规门禁`

## Test Scope

本计划验证以下内容：

- 受控文件后端 schema、service、router 和生命周期规则。
- 单编号单现行版本约束、版本历史和元数据检索。
- 审核包导出与 `GBZ-02/04/05` 合规门禁是否共用同一受控根解析逻辑。
- 前端 `documentControl` 页面模块和 API 适配层的关键交互。

以下内容明确不在本轮测试范围：

- `WS02` 的导航接入、路由注册和 capability 快照扩展。
- 完整 Playwright 业务流，因为本任务不修改共享路由入口，页面保持可挂载但未注册。
- 其他质量工作流的完整业务闭环。

## Environment

- Windows PowerShell，工作目录：`D:\ProjectPackage\RagflowAuth`
- Python 环境可执行 `python -m pytest`
- Node 环境可在 `fronted/` 目录执行 `npm test`
- 测试数据库由现有单测使用的临时目录/临时 SQLite 文件创建
- 不要求真实 RAGFlow 服务在线；相关能力应通过单测 stub 或本地假实现隔离验证

## Accounts and Fixtures

- 后端单测使用仓库现有测试基建和临时用户/权限快照。
- 前端单测使用 jest + React Testing Library mock。
- 审核包/合规校验器测试使用 temp repo fixture，显式创建 `doc/compliance/*` 样本文件。

如果以下任一项缺失，测试必须 fail fast：

- `pytest` 不可运行
- `fronted/node_modules` 缺失导致 `npm test` 无法执行
- 受控文件 schema 无法初始化

## Commands

1. `python -m pytest backend/tests/test_document_control_service_unit.py backend/tests/test_document_control_api_unit.py backend/tests/test_compliance_review_package_api_unit.py backend/tests/test_gbz02_compliance_gate_unit.py backend/tests/test_gbz04_compliance_gate_unit.py backend/tests/test_gbz05_compliance_gate_unit.py`
   期望：全部通过，且能覆盖受控文件生命周期、审核包导出和统一受控根解析。
2. `python -m pytest backend/tests/test_document_versioning_unit.py backend/tests/test_knowledge_ingestion_manager_unit.py`
   期望：与 `kb_documents` 复用链路相关的既有行为不回归。
3. `npm test -- --runInBand --watch=false src/features/documentControl src/pages/DocumentControl.test.js`
   期望：前端 API 归一化、页面状态和关键交互测试通过。

如果命令 3 因 `react-scripts test` 参数差异失败，可改为：

4. `npm test -- --runInBand --watchAll=false src/features/documentControl src/pages/DocumentControl.test.js`
   期望：与命令 3 相同。

## Test Cases

### T1: 受控文件主档与修订创建

- Covers: P1-AC1
- Level: unit
- Command: `python -m pytest backend/tests/test_document_control_service_unit.py`
- Expected: 可创建主档与首版/后续修订，并持久化必需元数据字段。

### T2: 生命周期与单现行版本约束

- Covers: P1-AC2, P1-AC3
- Level: unit
- Command: `python -m pytest backend/tests/test_document_control_service_unit.py backend/tests/test_document_control_api_unit.py`
- Expected: 非法状态流转被拒绝；新修订生效时旧修订被作废；审计事件被记录。

### T3: 审核包与统一受控根

- Covers: P1-AC4, P1-AC5
- Level: integration
- Command: `python -m pytest backend/tests/test_compliance_review_package_api_unit.py backend/tests/test_gbz02_compliance_gate_unit.py backend/tests/test_gbz04_compliance_gate_unit.py backend/tests/test_gbz05_compliance_gate_unit.py`
- Expected: 审核包导出成功；相关合规校验器使用统一根路径并通过 temp repo 断言。

### T4: 既有文档版本链不回归

- Covers: P1-AC1, P1-AC2
- Level: regression
- Command: `python -m pytest backend/tests/test_document_versioning_unit.py backend/tests/test_knowledge_ingestion_manager_unit.py`
- Expected: `kb_documents` 现有版本链和上传链路继续按原语义工作。

### T5: 前端页面筛选与详情

- Covers: P2-AC1, P2-AC3
- Level: unit
- Command: `npm test -- --runInBand --watchAll=false src/features/documentControl src/pages/DocumentControl.test.js`
- Expected: 页面能渲染受控文件列表、应用筛选条件、展示版本历史与当前修订。

### T6: 前端状态操作与错误处理

- Covers: P2-AC2, P2-AC4
- Level: unit
- Command: `npm test -- --runInBand --watchAll=false src/features/documentControl src/pages/DocumentControl.test.js`
- Expected: 页面能调用创建/流转 API，并在成功和失败分支更新 UI 状态。

## Coverage Matrix

| Case ID | Area | Scenario | Level | Acceptance IDs | Evidence |
| --- | --- | --- | --- | --- | --- |
| T1 | document_control service | 创建主档与修订 | unit | P1-AC1 | `test_document_control_service_unit.py` |
| T2 | document_control lifecycle | 状态流转、单现行版本、审计事件 | unit | P1-AC2, P1-AC3 | `test_document_control_service_unit.py`, `test_document_control_api_unit.py` |
| T3 | compliance export/gates | 审核包与统一受控根 | integration | P1-AC4, P1-AC5 | `test_compliance_review_package_api_unit.py`, `test_gbz02/04/05_compliance_gate_unit.py` |
| T4 | kb reuse regression | 版本链与上传链路不回归 | regression | P1-AC1, P1-AC2 | `test_document_versioning_unit.py`, `test_knowledge_ingestion_manager_unit.py` |
| T5 | documentControl UI | 列表筛选与版本详情 | unit | P2-AC1, P2-AC3 | `DocumentControl.test.js`, `features/documentControl/*.test.js` |
| T6 | documentControl UI | 创建/流转动作与错误提示 | unit | P2-AC2, P2-AC4 | `DocumentControl.test.js`, `features/documentControl/*.test.js` |

## Evaluator Independence

- Mode: blind-first-pass
- Validation surface: real-runtime
- Required tools: pytest, npm, react-testing-library
- First-pass readable artifacts: prd.md, test-plan.md
- Withheld artifacts: execution-log.md, task-state.json
- Real environment expectation: 对后端在真实仓库和临时 SQLite 上运行；对前端在真实代码上执行单元测试，不读取执行日志先验信息。
- Escalation rule: 测试首轮不得查看 `execution-log.md` 或 `task-state.json`；只有在输出初判后，才允许做差异分析。

## Pass / Fail Criteria

- Pass when:
  - 所有计划命令通过，或记录了等价且通过的参数调整命令
  - 每个 acceptance id 至少有一个通过的测试用例
  - 没有未解释的失败、跳过或隐藏依赖
- Fail when:
  - 生命周期约束、统一受控根或前端关键交互任一测试失败
  - 需要依赖未落地的 `WS02` 共享文件改动才能让当前测试通过
  - 通过 fallback 或保留双主根才能让测试通过

## Regression Scope

- `kb_documents` 版本链
- 知识库上传本地落盘与 finalize 逻辑
- 审核包导出 API
- `GBZ-02/04/05` 合规校验器
- 前端新增 `documentControl` 模块对共享 HTTP 层的使用

## Reporting Notes

测试结果写入 `test-report.md`。

测试人需要分别记录：

- 环境与实际执行命令
- 每个测试用例的通过/失败
- 如果命令参数因本地工具行为需要微调，写出实际使用命令
- 最终 verdict 和仍存风险
