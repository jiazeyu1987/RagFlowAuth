# WS01 实施 PRD：受控文件基线与合规门禁

- Task ID: `docs-tasks-iso-13485-prd-llm-20260413t162500-dev-20260413T173942`
- Created: `2026-04-13T17:39:42`
- Workspace: `D:\ProjectPackage\RagflowAuth`
- User Request: `参考 docs/tasks/iso-13485-prd-llm-20260413T162500/development-docs/WS01-controlled-doc-baseline.md 开发 WS01 受控文件基线与合规门禁`

## Goal

基于现有知识库文档链路和 ISO 13485 拆解文档，落地一套最小可用的受控文件基线能力，使仓库内具备以下结果：

- 受控文件主档和版本记录有明确、可查询、可测试的数据模型。
- 文档生命周期按 `draft`、`in_review`、`approved`、`effective`、`obsolete` 管理，并强制同一文件编号只能有一个现行生效版本。
- 文档元数据至少覆盖文件编号、标题、类别、产品、注册证和目标知识库。
- 审核包导出和合规校验器使用同一受控文档根定义，不再在实现层散落硬编码路径。
- 前端提供一个可独立挂载的文控页面模块和 API 适配层，供 `WS02` 之后接入 `quality-system` 壳层。

## Scope

本次任务在以下范围内实现 `WS01` 基线：

- 新增受控文件后端域：
  - `backend/database/schema/document_control.py`
  - `backend/services/document_control/*`
  - `backend/app/modules/document_control/*`
- 将 `kb_documents` 现有文件记录与受控版本记录打通，复用本地文件、版本链、哈希和知识库字段。
- 为受控文件实现：
  - 创建主档与首版修订
  - 创建后续修订
  - 按状态流转
  - 版本历史查询
  - 按编号、标题、类别、产品、注册证、目标知识库过滤
- 为受控文件生效/作废写入标准化审计事件：
  - `controlled_revision_effective`
  - `controlled_revision_obsolete`
- 新增单一受控文档根工具，并让审核包导出与合规校验器通过该工具解析受控文档根。
- 新增 `doc/compliance/` 下的 WS01 基线文档与登记表，用作当前受控主根的仓库侧承载位置。
- 新增前端 `documentControl` 功能目录和 `DocumentControl.js` 页面，使其可以调用新后端 API 完成列表、筛选、详情和生命周期操作。

## Non-Goals

- 本次任务不实现 `WS02` 的导航、`quality-system` 路由壳层和 capability 资源冻结，不修改：
  - `fronted/src/routes/routeRegistry.js`
  - `fronted/src/components/layout/LayoutSidebar.js`
  - `fronted/src/shared/auth/capabilities.js`
  - `backend/app/core/permission_models.py`
- 本次任务不重写所有质量域文档内容，不承诺一次补齐 `GBZ/FDA/R7` 全部受控文档正文。
- 本次任务不引入 fallback 根路径，不保留“新旧根同时有效”的双写策略。
- 本次任务不把培训、变更、设备、投诉、通用审计 schema 等其他工作流业务逻辑并入 `WS01`。
- 本次任务不把未冻结的审批编排、站内信规则或质量工作台导航逻辑偷偷塞进实现。

## Preconditions

以下前提必须满足；缺失时需要阻断而不是猜测补齐：

- 仓库可读取，且以下模块可编辑：
  - `backend/app/main.py`
  - `backend/app/dependency_factory.py`
  - `backend/services/compliance/*`
  - `backend/services/documents/*`
  - `backend/services/kb/*`
  - `fronted/src/features/*`
  - `fronted/src/pages/*`
- SQLite 加性 schema 变更可执行，且 `backend/database/schema/ensure.py` 是当前统一 schema 入口。
- `WS02` 仍未接入质量域共享路由与 capability；因此本任务只交付可独立挂载页面和后端能力，不修改共享入口文件。
- 现有仓库根下缺少完整 `doc/compliance/` 受控语料；本任务只补 WS01 基线文档和根路径对齐能力，不把其他质量域缺文档伪装成已完成。

如果实际运行中发现：

- 数据库 schema 无法更新
- 受控文件本地落盘不可写
- 关键依赖模块出现与本任务冲突的用户改动

则必须停止执行，并记录到 `task-state.json.blocking_prereqs`。

## Impacted Areas

重点落点和下游影响如下：

- 后端入口与依赖：
  - `backend/app/main.py`
  - `backend/app/dependency_factory.py`
- 后端文控与知识库基础：
  - `backend/database/schema/ensure.py`
  - `backend/database/schema/kb_documents.py`
  - `backend/services/kb/store.py`
  - `backend/services/knowledge_ingestion/manager.py`
  - `backend/app/modules/knowledge/routes/documents.py`
  - `backend/app/modules/knowledge/routes/versions.py`
- 审核包和合规门禁：
  - `backend/services/compliance/review_package.py`
  - `backend/services/compliance/*_validator.py`
  - `backend/app/modules/audit/router.py`
- 前端：
  - `fronted/src/features/documentControl/*`
  - `fronted/src/pages/DocumentControl.js`
  - `fronted/src/features/knowledge/upload/*` 仅在需要复用上传辅助逻辑时最小修改
  - `fronted/src/features/knowledge/documentBrowser/*` 仅在需要复用文档展示工具时最小修改
- 测试：
  - `backend/tests/test_document_control_*`
  - `backend/tests/test_compliance_review_package_api_unit.py`
  - `backend/tests/test_gbz02_compliance_gate_unit.py`
  - `backend/tests/test_gbz04_compliance_gate_unit.py`
  - `backend/tests/test_gbz05_compliance_gate_unit.py`
  - `fronted/src/features/documentControl/*.test.js`
  - `fronted/src/pages/DocumentControl.test.js`
- 仓库侧受控文档根：
- `doc/compliance/*`

## Phase Plan

### P1: 后端受控文件基线与单一受控根对齐

- Objective: 新增受控文件主档/修订模型、生命周期服务与 API，并让审核包与合规校验器通过单一受控根解析仓库文档。
- Owned paths:
  - `backend/database/schema/document_control.py`
  - `backend/database/schema/ensure.py`
  - `backend/services/document_control/*`
  - `backend/app/modules/document_control/*`
  - `backend/app/dependency_factory.py`
  - `backend/app/main.py`
  - `backend/services/kb/store.py`
  - `backend/services/compliance/review_package.py`
  - `backend/services/compliance/*_validator.py`
  - `backend/app/modules/audit/router.py`
  - `doc/compliance/*`
  - `backend/tests/test_document_control_*`
  - `backend/tests/test_compliance_review_package_api_unit.py`
  - `backend/tests/test_gbz02_compliance_gate_unit.py`
  - `backend/tests/test_gbz04_compliance_gate_unit.py`
  - `backend/tests/test_gbz05_compliance_gate_unit.py`
- Dependencies:
  - 现有 `kb_documents` 版本链字段可复用
  - 依赖注入仍由 `dependency_factory.py` 统一装配
  - 审核包与校验器当前可按单测 temp repo 独立验证
- Deliverables:
  - 受控文件 schema、store/service、FastAPI router
  - 生命周期流转规则与单一现行版本约束
  - 标准化审计事件
  - 统一受控根解析工具
  - 基线 `docs/compliance/controlled_document_register.md` 与 WS01 相关文档
  - 后端与合规回归单测

### P2: 前端文控页面与 API 适配层

- Objective: 提供一个不依赖 `WS02` 导航改造的文控页面模块，支持受控文件列表、筛选、详情和状态操作。
- Owned paths:
  - `fronted/src/features/documentControl/*`
  - `fronted/src/pages/DocumentControl.js`
  - `fronted/src/pages/DocumentControl.test.js`
  - `fronted/src/features/documentControl/*.test.js`
- Dependencies:
  - P1 的后端 API 已稳定
  - `WS02` 共享路由/权限壳层仍未接入，因此页面保持“可挂载、未注册”状态
- Deliverables:
  - 前端文控 API 适配层
  - 受控文件列表/筛选/详情/操作页面
  - 聚焦于页面逻辑和 API 交互的前端测试

## Phase Acceptance Criteria

### P1

- P1-AC1: 受控文件主档与修订记录可以持久化，并且至少包含 `doc_code`、`title`、`document_type`、`product`、`registration_ref`、`target_kb`、`revision_no`、`status`。
- P1-AC2: 生命周期只能沿 `draft -> in_review -> approved -> effective -> obsolete` 受控流转，并强制同一 `doc_code` 同时只有一个 `effective` 修订。
- P1-AC3: 新修订生效时会显式作废上一现行修订，并写入 `controlled_revision_effective` 与 `controlled_revision_obsolete` 审计事件证据。
- P1-AC4: 审核包导出和 `GBZ-02/04/05` 合规校验器通过同一受控根工具解析仓库文档，不再各自硬编码旧主根。
- P1-AC5: `doc/compliance/controlled_document_register.md` 由同一文控数据生成或校验，导出内容中的路径、版本、状态、分组与当前实现一致。
- Evidence expectation: `execution-log.md#Phase-P1`、相关后端测试输出和审核包/校验器单测可以证明后端能力、根路径对齐和审计事件都已落地。

### P2

- P2-AC1: 前端文控页面可以按编号、标题、类别、产品和注册证过滤受控文件列表，并展示当前修订状态。
- P2-AC2: 页面可以创建受控文件或新增修订，并能触发至少 `in_review`、`approved`、`effective`、`obsolete` 的状态操作。
- P2-AC3: 页面可以查看版本历史和当前现行修订，不依赖修改 `routeRegistry.js`、`LayoutSidebar.js` 或 capability 共享文件。
- P2-AC4: 前端测试覆盖 API 归一化、页面状态管理和关键用户动作的成功/失败分支。
- Evidence expectation: `execution-log.md#Phase-P2`、前端测试输出和页面逻辑测试能证明页面模块可独立挂载并正确调用后端 API。

## Done Definition

本任务完成必须同时满足：

- `P1` 与 `P2` 都完成并记录执行证据。
- 受控文件基线能力可以在隔离测试数据库中完成创建、流转、查询和导出。
- 审核包导出与指定合规校验器已改用统一受控根解析逻辑，并通过回归单测。
- 前端文控页面模块和 API 适配层已可运行并有测试覆盖。
- `execution-log.md` 或 `test-report.md` 中每个 acceptance id 都有可追溯证据。

## Blocking Conditions

以下情况必须中止，而不是通过 fallback、占位实现或双写兜底继续推进：

- 需要同时保留 `doc/compliance/` 和 `docs/compliance/` 作为长期有效主根才能让实现通过。
- `WS02` 未落地导致必须修改其禁止写入的共享文件才能完成本任务。
- 受控文件状态流转无法在数据层强制“单编号单现行有效”约束。
- 当前工作树中出现直接冲突于 `WS01` 归属文件的未提交用户改动，且无法安全协同。
- 关键验证命令依赖的测试基建、Node/Python 环境或数据库 schema 初始化失败。
