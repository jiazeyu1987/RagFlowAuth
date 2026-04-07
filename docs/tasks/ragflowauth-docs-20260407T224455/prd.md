# PRD

- Task ID: `ragflowauth-docs-20260407T224455`
- Created: `2026-04-07T22:44:55`
- Workspace: `D:\ProjectPackage\RagflowAuth`
- User Request: `读取 RagflowAuth 前后端代码并按指定 docs 结构编写项目文档。`

## Goal

基于当前仓库中的真实前后端代码、配置和运维脚本，补齐一套可导航、可核对、可持续维护的项目文档体系，覆盖用户指定的根目录文档与 `docs/` 目录结构。

本次工作应让维护者能够快速回答以下问题：

- 系统入口在哪里，后端如何注册路由，前端如何组织页面与权限守卫。
- 权限模型如何从后端 `auth/me` 快照传递到前端 `useAuth` 与 `PermissionGuard`。
- 主要业务域有哪些，哪些能力依赖外部系统，如 RAGFlow、OnlyOffice、SMTP、Docker。
- 当前仓库对设计系统、Nixpacks、uv 等参考技术的采用状态是什么。
- 哪些风险已经在代码中显式处理，哪些仍是未验证或需人工确认的技术债。

## Scope

本任务只包含文档写作与验证，目标产物为：

- `ARCHITECTURE.md`
- `DESIGN.md`
- `FRONTEND.md`
- `PLANS.md`
- `PRODUCT_SENSE.md`
- `QUALITY_SCORE.md`
- `RELIABILITY.md`
- `SECURITY.md`
- `docs/design-docs/index.md`
- `docs/design-docs/core-beliefs.md`
- `docs/exec-plans/active/README.md`
- `docs/exec-plans/completed/README.md`
- `docs/exec-plans/tech-debt-tracker.md`
- `docs/generated/db-schema.md`
- `docs/product-specs/index.md`
- `docs/product-specs/new-user-onboarding.md`
- `docs/references/design-system-reference-llms.txt`
- `docs/references/nixpacks-llms.txt`
- `docs/references/uv-llms.txt`

文档内容必须以以下真实仓库锚点为依据：

- 后端应用入口与路由聚合：`backend/app/main.py`
- 后端依赖装配与多租户依赖：`backend/app/dependencies.py`
- 后端权限解析：`backend/app/core/auth.py`、`backend/app/core/authz.py`、`backend/app/core/permission_resolver.py`
- 后端 schema：`backend/database/schema/*.py`
- 前端应用入口：`fronted/src/App.js`
- 前端认证与权限：`fronted/src/hooks/useAuth.js`、`fronted/src/components/PermissionGuard.js`
- 前端布局与导航：`fronted/src/components/Layout.js`
- 前端 HTTP 层：`fronted/src/shared/http/httpClient.js`
- 运行与部署资料：`.env`、`backend/Dockerfile`、`fronted/Dockerfile`、`fronted/nginx.conf`、`VALIDATION.md`

## Non-Goals

- 不修改产品行为、接口契约、数据库结构、前后端页面逻辑或测试代码。
- 不迁移、恢复或重写当前已被删除的 `doc/` 历史文档体系。
- 不为缺失的外部依赖补充 mock、fallback、兼容分支或“假定成功”的说明。
- 不伪造执行计划历史，不把不存在的上线流程、设计系统或构建平台写成既成事实。

## Preconditions

- 能读取 `backend/`、`fronted/`、`tool/`、`.env`、`VALIDATION.md` 和 `data/auth.db`。
- 能写入用户要求的根目录文档与 `docs/` 目录。
- 能使用 `python` 执行结构验证脚本。
- 如果需要校验 `data/auth.db` 的实际表结构，文件必须可读；若不可读，则停止并记录为阻塞前提。
- 如果需要运行 `VALIDATION.md` 中的链路脚本，必须存在其声明的外部依赖；缺失时只能记录未验证风险，不能补 mock。

## Impacted Areas

- 仓库根目录的工程说明与维护入口。
- `docs/` 目录的设计文档、产品规格、执行计划、生成物和参考资料。
- `docs/tasks/ragflowauth-docs-20260407T224455/*` 中的执行证据与测试报告。
- 使用文档进行 onboarding、风险评审和后续规划的维护者。

## Phase Plan

### P1: Build The Requested Documentation Skeleton

- Objective:
  按用户指定结构创建根目录文档与 `docs/` 目录框架，并明确每份文档的职责边界。
- Owned paths:
  - `ARCHITECTURE.md`
  - `DESIGN.md`
  - `FRONTEND.md`
  - `PLANS.md`
  - `PRODUCT_SENSE.md`
  - `QUALITY_SCORE.md`
  - `RELIABILITY.md`
  - `SECURITY.md`
  - `docs/design-docs/index.md`
  - `docs/design-docs/core-beliefs.md`
  - `docs/exec-plans/active/README.md`
  - `docs/exec-plans/completed/README.md`
  - `docs/exec-plans/tech-debt-tracker.md`
  - `docs/generated/db-schema.md`
  - `docs/product-specs/index.md`
  - `docs/product-specs/new-user-onboarding.md`
  - `docs/references/design-system-reference-llms.txt`
  - `docs/references/nixpacks-llms.txt`
  - `docs/references/uv-llms.txt`
- Dependencies:
  - Current repository tree
  - User-requested target structure
- Deliverables:
  - All requested paths created
  - Structural index pages for `docs/design-docs` and `docs/product-specs`
  - Trackable `active/` and `completed/` plan directories

### P2: Document Backend, Frontend, And Product Semantics

- Objective:
  用真实代码锚点写清架构分层、前端导航与权限、主要业务域与新用户理解路径。
- Owned paths:
  - `ARCHITECTURE.md`
  - `FRONTEND.md`
  - `DESIGN.md`
  - `PRODUCT_SENSE.md`
  - `docs/design-docs/index.md`
  - `docs/design-docs/core-beliefs.md`
  - `docs/product-specs/index.md`
  - `docs/product-specs/new-user-onboarding.md`
- Dependencies:
  - `backend/app/main.py`
  - `backend/app/dependencies.py`
  - `backend/app/core/auth.py`
  - `backend/app/core/authz.py`
  - `backend/app/core/permission_resolver.py`
  - `backend/services/auth_me_service.py`
  - `fronted/src/App.js`
  - `fronted/src/components/Layout.js`
  - `fronted/src/components/PermissionGuard.js`
  - `fronted/src/hooks/useAuth.js`
  - Representative feature hooks under `fronted/src/features/*`
- Deliverables:
  - Backend + frontend architecture overview
  - Role and permission model explanation
  - Product-domain and onboarding documentation

### P3: Document Reliability, Security, Quality, And Data Model

- Objective:
  将运行约束、外部依赖、验证命令、风险点和 SQLite 数据模型沉淀为维护文档。
- Owned paths:
  - `QUALITY_SCORE.md`
  - `RELIABILITY.md`
  - `SECURITY.md`
  - `PLANS.md`
  - `docs/exec-plans/tech-debt-tracker.md`
  - `docs/generated/db-schema.md`
  - `docs/references/design-system-reference-llms.txt`
  - `docs/references/nixpacks-llms.txt`
  - `docs/references/uv-llms.txt`
- Dependencies:
  - `.env`
  - `backend/app/core/config.py`
  - `backend/database/paths.py`
  - `backend/database/tenant_paths.py`
  - `backend/services/data_security_scheduler_v2.py`
  - `backend/database/schema/*.py`
  - `data/auth.db`
  - `backend/Dockerfile`
  - `fronted/Dockerfile`
  - `fronted/nginx.conf`
  - `VALIDATION.md`
- Deliverables:
  - Security model and operational guardrails
  - Reliability and validation guidance
  - Schema documentation grouped by business domain
  - Reference notes that truthfully state current adoption or non-adoption

### P4: Validate, Record Evidence, And Hand Off

- Objective:
  执行结构校验、内容锚点校验、schema 覆盖校验，记录完成证据与未验证风险。
- Owned paths:
  - `docs/tasks/ragflowauth-docs-20260407T224455/execution-log.md`
  - `docs/tasks/ragflowauth-docs-20260407T224455/test-report.md`
- Dependencies:
  - All documents from P1-P3
  - Validation commands defined in `test-plan.md`
- Deliverables:
  - Reviewed execution evidence
  - Independent validation report
  - Final completion check readiness

## Phase Acceptance Criteria

### P1

- P1-AC1: 所有用户要求的根目录文档、`docs/` 目录和关键文件均已创建。
- P1-AC2: `docs/design-docs/index.md` 与 `docs/product-specs/index.md` 能清楚说明各自目录中的文档职责与入口。
- P1-AC3: `docs/exec-plans/active/README.md` 和 `docs/exec-plans/completed/README.md` 明确说明目录用途，从而使目录在仓库中可跟踪。
- Evidence expectation:
  通过文件存在性检查与目录结构检查，并在 `execution-log.md` 中记录。

### P2

- P2-AC1: `ARCHITECTURE.md` 明确描述 FastAPI 路由聚合、依赖装配、多租户依赖解析和核心业务模块分层。
- P2-AC2: `FRONTEND.md` 明确描述前端路由壳、`AuthProvider`、`PermissionGuard`、布局导航与主要 feature 分组。
- P2-AC3: `DESIGN.md`、`PRODUCT_SENSE.md` 和 `docs/product-specs/new-user-onboarding.md` 能帮助新维护者理解角色、权限、关键页面和核心任务流。
- Evidence expectation:
  文档中包含真实代码路径锚点，并经内容锚点校验命令验证。

### P3

- P3-AC1: `SECURITY.md`、`RELIABILITY.md`、`QUALITY_SCORE.md` 明确区分“代码事实”“推断”“未验证风险”。
- P3-AC2: `docs/generated/db-schema.md` 覆盖核心表族，包括用户、权限、知识库目录、操作审批、通知和数据安全。
- P3-AC3: `docs/references/design-system-reference-llms.txt`、`docs/references/nixpacks-llms.txt`、`docs/references/uv-llms.txt` 如实写明当前仓库是否采用相关技术，以及判断依据。
- Evidence expectation:
  运行 schema 校验脚本与内容检查，并将结果记录到 `execution-log.md`。

### P4

- P4-AC1: `execution-log.md` 记录每个阶段的改动路径、已运行验证和覆盖的 acceptance ids。
- P4-AC2: `test-report.md` 记录独立的结构验证、内容验证、schema 验证结果和最终 verdict。
- P4-AC3: 所有 acceptance ids 都能在 `execution-log.md` 或 `test-report.md` 中找到对应证据引用。
- Evidence expectation:
  `record_phase_review.py`、`record_test_review.py` 和最终 completion check 全部通过。

## Done Definition

- P1-P4 全部完成。
- 所有验收项均有证据。
- 生成的文档没有模板残留、伪造采用状态或未说明依据的断言。
- 若某些外部集成无法在当前环境中验证，文档中已明确标记为“未验证”并写明原因。

## Blocking Conditions

- 无法读取关键源代码、配置或 `data/auth.db`。
- 无法写入用户要求的目标文档路径。
- 结构校验或 schema 校验持续失败，且失败原因无法在仓库内定位。
- 只有通过 mock、fallback 或假定成功才能完成文档结论。
