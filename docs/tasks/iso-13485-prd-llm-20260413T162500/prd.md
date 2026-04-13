# ISO 13485 开发拆解 PRD（多 LLM 并行开发包）

- Task ID: `iso-13485-prd-llm-20260413T162500`
- Created: `2026-04-13T16:25:00`
- Workspace: `D:\ProjectPackage\RagflowAuth`
- User Request: `基于现有 ISO 13485 整改 PRD，将其拆解成若干份可以独立开发、可分别分配给不同 LLM 的开发文档包，明确每个工作流的目标、边界、依赖、接口、验收标准与交接约束`

## Goal

基于已有整改总纲 [source-prd](D:/ProjectPackage/RagflowAuth/docs/tasks/iso-13485-20260413T153016/prd.md)，输出一组可以直接分配给不同 LLM 独立推进的开发文档，使后续开发具备以下特征：

- 每个工作流都有清晰的业务目标和源需求归属。
- 每个工作流都有尽量不重叠的代码写入边界。
- 共享接口、共享枚举、共享事件和共享提醒能力有唯一 owner。
- 不同 LLM 可以并行开发，而不会在 `routeRegistry.js`、`permission_models.py`、审计事件模型等关键共享文件上反复冲突。
- 源 PRD 中尚未冻结、尚未足够开发化的事项会被显式标为“上游需求缺口”，而不是被不同 LLM 各自猜测。

## Scope

本次任务只交付“开发文档包”，范围包括：

- 读取现有 ISO 13485 整改 PRD，并将其拆解成若干个独立工作流。
- 输出工作流总览、共享契约文档和每个工作流的独立开发文档。
- 为每个工作流明确：
  - 目标
  - 来源需求
  - 负责边界
  - 不负责范围
  - 代码写入边界
  - 共享接口
  - 依赖关系
  - 验收标准
  - 交接给 LLM 的执行约束
- 标记当前源 PRD 中尚未足够开发化的事项，避免误拆解。

## Non-Goals

- 本次任务不实现任何产品代码。
- 本次任务不重写旧的整改总纲，只在拆解文档中引用它。
- 本次任务不把会议纪要中未冻结的外部集成或对标研究伪装成可直接编码的开发需求。
- 本次任务不把多个工作流重新合并为一个“大而全”的实现文档。
- 本次任务不引入 fallback、双 owner 或“谁都能改”的共享边界。

## Preconditions

以下前提必须满足；缺失时应阻断拆解，而不是靠猜测补齐：

- 源 PRD [source-prd](D:/ProjectPackage/RagflowAuth/docs/tasks/iso-13485-20260413T153016/prd.md) 可读取。
- 当前仓库真实结构可读取，尤其是导航、权限、文档、培训、审计、审批、通知相关模块。
- 允许在新的任务目录中新增拆解文档。
- 拆解文档必须如实继承源 PRD 的边界；若源 PRD 未写清某事项，只能记录为“上游缺口”，不能擅自补成已确认需求。

## Impacted Areas

本次任务是文档拆解任务，但文档必须锚定真实代码落点。重点参考区域如下：

- 源整改文档：
  - `docs/tasks/iso-13485-20260413T153016/prd.md`
- 新开发文档包：
  - `docs/tasks/iso-13485-prd-llm-20260413T162500/development-docs/*`
- 文控与合规基线：
  - `backend/services/compliance/*`
  - `backend/app/modules/documents/*`
  - `backend/services/documents/*`
  - `backend/database/schema/training_compliance.py`
- 体系入口与权限：
  - `fronted/src/routes/routeRegistry.js`
  - `fronted/src/components/layout/LayoutSidebar.js`
  - `fronted/src/shared/auth/capabilities.js`
  - `backend/app/core/permission_models.py`
- 培训、审批、站内信：
  - `backend/app/modules/training_compliance/*`
  - `backend/services/training_compliance.py`
  - `backend/app/modules/inbox/*`
  - `backend/services/notification/*`
  - `fronted/src/features/trainingCompliance/*`
  - `fronted/src/features/notification/*`
  - `fronted/src/features/operationApproval/*`
- 变更控制：
  - `backend/app/modules/emergency_changes/*`
  - `backend/services/emergency_change.py`
- 审计与导出：
  - `backend/app/modules/audit/*`
  - `backend/services/audit*`
  - `backend/database/schema/audit_logs.py`
  - `fronted/src/features/audit/*`
  - `fronted/src/pages/AuditLogs.js`
  - `fronted/src/pages/DocumentAudit.js`
- 尚不存在、但应在拆解文档中预留的新增域：
  - `equipment`
  - `metrology`
  - `maintenance`
  - `batch_records`
  - `quality_system`
  - `change_control`
  - `complaints`
  - `management_review`

## 源 PRD 约束与拆解原则

本任务必须遵守以下拆解原则：

1. 以“写入边界”而不是以“会议话题”拆分。
2. 共享文件必须指定唯一 owner。
3. 交叉领域只能通过共享契约协作，不允许不同 LLM 各自发明字段名、事件名和状态机。
4. 前期重点仍保持与源 PRD 一致：
   - 文控基线
   - `体系文件`入口与权限
   - 设备相关台账
5. 源 PRD 中未真正冻结的事项只做缺口提示，包括：
   - 钉钉审批流程平移
   - Windchill / Teamcenter / 冠骋对标研究
   - 设备负责人“李欣”的组织确认
   - 培训方式分类细则
   - 投诉流程的完整闭环细则

## Phase Plan

### P1: 交付多 LLM 独立开发文档包

- Objective: 将现有 ISO 13485 整改 PRD 拆成一组可以独立开发的工作流文档，并配套工作流总览、共享契约和独立评审测试计划。
- Owned paths: docs/tasks/iso-13485-prd-llm-20260413T162500/prd.md; docs/tasks/iso-13485-prd-llm-20260413T162500/test-plan.md; docs/tasks/iso-13485-prd-llm-20260413T162500/development-docs/00-overview.md; docs/tasks/iso-13485-prd-llm-20260413T162500/development-docs/01-shared-interfaces.md; docs/tasks/iso-13485-prd-llm-20260413T162500/development-docs/WS01-controlled-doc-baseline.md; docs/tasks/iso-13485-prd-llm-20260413T162500/development-docs/WS02-quality-system-hub-and-auth.md; docs/tasks/iso-13485-prd-llm-20260413T162500/development-docs/WS03-training-and-inbox-loop.md; docs/tasks/iso-13485-prd-llm-20260413T162500/development-docs/WS04-change-control-ledger.md; docs/tasks/iso-13485-prd-llm-20260413T162500/development-docs/WS05-equipment-metrology-maintenance.md; docs/tasks/iso-13485-prd-llm-20260413T162500/development-docs/WS06-batch-records-and-signature.md; docs/tasks/iso-13485-prd-llm-20260413T162500/development-docs/WS07-audit-and-evidence-export.md; docs/tasks/iso-13485-prd-llm-20260413T162500/development-docs/WS08-complaints-and-governance-closure.md
- Dependencies: 源整改 PRD 可读取; 仓库结构可读取; 现有导航/权限/文档/培训/审计代码可定位
- Deliverables: 多工作流总览文档; 共享接口契约文档; 8 份可独立开发的工作流文档; 独立评审测试计划

## Phase Acceptance Criteria

### P1

- P1-AC1: 文档包把源整改 PRD 拆成一组有限、清晰、可命名的工作流，而不是继续保留一份大总纲。
- P1-AC2: 每个工作流文档都至少包含目标、来源需求、负责边界、不负责范围、代码写入边界、共享接口、依赖关系、验收标准和 LLM 交接约束。
- P1-AC3: 总览文档明确给出并行开发顺序、冲突风险、共享文件 owner 和建议的 LLM 分配方式。
- P1-AC4: 共享契约文档明确冻结通用实体名、能力名、路由前缀、通知载荷和审计事件结构，避免不同 LLM 自行发明。
- P1-AC5: 文档包如实记录源 PRD 尚未足够开发化的事项，明确这些内容不能直接分配为编码任务。
- P1-AC6: `test-plan.md` 能让独立评审人仅通过阅读文档与检查路径，即可确认拆解包是否完整、可并行、可落地。
- Evidence expectation: 评审人阅读 `prd.md`、`test-plan.md` 和 `development-docs/*` 后，可以知道每个工作流该由谁做、能改哪里、依赖什么、何时合并。

## Done Definition

本任务完成的标准是：

- 新任务的 `prd.md` 与 `test-plan.md` 完整可校验。
- `development-docs/` 下的总览、共享契约和 8 份工作流文档均已生成。
- 每份工作流文档都具备独立交接给不同 LLM 的最小信息闭环。
- `validate_artifacts.py` 通过。
- 文档中对上游缺口、共享边界和不可并行点都有明确标记。

## Blocking Conditions

以下情况必须阻断，而不能靠猜测填充：

- 源整改 PRD 不存在或不可读。
- 当前仓库结构无法定位到导航、权限、文档、培训、审计、变更等关键模块。
- 拆解时发现两个工作流必须长期共享同一批核心文件且无法指定唯一 owner。
- 需要把会议纪要中的未冻结事项强行写成可编码任务才能完成拆解。
