# ISO 13485 整改文档 PRD（体系文件治理中枢）

- Task ID: `iso-13485-20260413T153016`
- Created: `2026-04-13T15:30:16`
- Workspace: `D:\ProjectPackage\RagflowAuth`
- User Request: `根据已识别的 ISO 13485 不符合项、会议纪要关于文控/设备/变更/批记录/体系文件入口的讨论，以及新增体系文件页签的设想，整理一份详尽的整改文档与验收工件`

## Goal

基于当前仓库真实现状与会议纪要，形成一份可直接用于立项、评审和排期的 ISO 13485 整改文档，明确以下内容：

- 当前系统为什么还不能宣称满足 ISO 13485 的关键原因。
- 哪些问题是文控基线问题，哪些问题是后续产品能力问题。
- 如何新增独立的`体系文件`入口，并把它设计成质量部子管理员可执行全部合规动作的治理中枢。
- 如何分阶段推进文控、培训、变更控制、设备全生命周期、计量、维护保养、电子批记录、审计追踪等能力，而不引入静默兼容或伪合规。

## Scope

本次任务交付整改文档与验收工件，并在同一任务内完成部分关键能力的最小落地（见 Phase Plan，P1-P5），范围包括：

- 对当前仓库中的 ISO 13485 差距进行证据化梳理。
- 结合会议纪要，整理`体系文件`页签的目标定位、信息架构、权限模型和核心流程。
- 把文控、培训、变更、设备、计量、维护、批记录、审计日志、投诉待定等要求整理成可执行的整改清单。
- 冻结质量 capability 合同并保证前后端常量对齐、`auth/me` capability 快照稳定可消费（P2）。
- 将质量域相关 API 的鉴权收敛到 capability（fail-fast 403，无角色名兜底），并用后端单测固化（P3）。
- 落地批记录最小闭环：后端模型/API/签名复用/审计留痕 + 前端工作区 + Jest/Playwright 证据（P4-P5）。
- 给出推荐优先级、前置条件、阻断条件和后续实施路线图。
- 提供独立评审可复用的测试计划与测试报告。

## Non-Goals

- 本次任务不实现除批记录之外的设备/变更/计量/维护/投诉/内审/管评等业务域的完整流程闭环与页面交互（本任务仅覆盖其 capability 合同与后端鉴权收敛）。
- 本次任务不做历史文档迁移，也不对现有受控文件做批量“内容改写”；仅以当前仓库事实为准整理证据与门禁一致性。
- 本次任务不把 `tobedeleted/compliance/*` 直接认定为当前有效受控文件。
- 本次任务不宣称系统已经符合 ISO 13485；即使 P2-P5 有代码交付，也只代表按本任务范围完成最小落地与证据化验证。
- 批记录不在本任务内覆盖所有产品/工艺/检验场景模板，也不替代质量负责人对“手签/口令”等效电子签名策略的最终确认。
- 不允许为了“先跑通”而引入双文档根、占位文件、静默降级或兼容分支。

## Preconditions

以下前提在后续实施阶段必须明确；缺失时应阻断实施，而不是用 fallback 顶过去：

- 质量负责人确认唯一受控体系文件主根，以及文件编号规则、文件分类规则。
- 质量负责人确认文件二维分类口径：
  - 维度一：文件类别。
  - 维度二：从属产品及注册证映射。
- 质量负责人确认质量部子管理员的授权边界，以及审批、复核、批准、作废、培训分派的角色矩阵。
- 质量负责人确认电子签名策略，包括手签、口令、审批留痕和证据保留规则。
- 质量负责人确认培训规则，包括阅读时长、确认动作、提问闭环、逾期规则。
- 设备业务口确认设备部对接人、设备台账字段、计量与维护保养规则。
- 仓库环境可运行 `rg` 和 `python scripts/validate_*_repo_compliance.py`，用于整改前后基线核验。

## Impacted Areas

以下区域是后续整改实施最可能改动的真实入口：

- 文控与合规校验：
  - `backend/services/compliance/review_package.py`
  - `backend/services/compliance/*_validator.py`
  - `backend/database/schema/training_compliance.py`
- 导航与页面入口：
  - `fronted/src/routes/routeRegistry.js`
  - `fronted/src/components/layout/LayoutSidebar.js`
- 权限与能力快照：
  - `fronted/src/shared/auth/capabilities.js`
  - `backend/app/core/permission_models.py`
- 审计、站内信、电子签名等现有可复用基础能力：
  - `backend/app/modules/audit/router.py`
  - `backend/database/schema/audit_logs.py`
  - `backend/services/notification/inbox_service.py`
  - `backend/app/modules/electronic_signature/routes/manage.py`
- 后续新增或扩展的业务域：
  - 文档控制
  - 培训确认
  - 变更控制
  - 设备全生命周期
  - 计量管理
  - 维护保养
  - 批记录管理
  - 投诉、内审、管理评审

## 仓库现状与证据

以下是本整改文档建立的事实基础，只写当前仓库真实情况，不做历史推断：

| 事实 | 仓库证据 | 影响 |
| --- | --- | --- |
| 当前唯一受控合规文档主根已切到 `docs/compliance/`，合规门禁脚本与导出路径已对齐并通过。 | `backend/services/document_control/compliance_root.py`；`backend/services/compliance/review_package.py`；`scripts/validate_*_repo_compliance.py` | 文控主根断裂已消除，独立评审应以 `docs/compliance/` 为准。 |
| `tobedeleted/compliance/*` 仍保留历史副本，可作为迁移来源，但不能直接当作当前生效受控文件。 | `tobedeleted/compliance/*`；`docs/compliance/*` | 评审时必须区分“历史副本”与“现行受控文档”。 |
| 培训数据种子、培训矩阵和培训确认链路已经统一引用 `docs/compliance/training_matrix.md#...`。 | `backend/database/schema/training_compliance.py`；`docs/compliance/training_matrix.md` | 培训受控源已恢复，但后续仍需补强培训审计导出。 |
| 前端导航通过 `routeRegistry.js` 的 `showInNav` 生成，侧边栏通过 `LayoutSidebar.js` + `PermissionGuard` 做展示与权限控制。 | `fronted/src/routes/routeRegistry.js`；`fronted/src/components/layout/LayoutSidebar.js` | 新增`体系文件`页签在技术上可行，但必须接入现有路由与权限模型。 |
| 当前 capability snapshot 已覆盖质量体系域资源，`auth/me` 可向非 `admin` 的质量子管理员返回真实质量 action。 | `backend/app/core/permission_models.py`；`backend/services/auth_me_service.py`；`fronted/src/shared/auth/capabilities.js` | 质量域权限合同已建立，可用于后端鉴权与前端显隐。 |
| 审计日志、站内信、电子签名、培训读时、批记录图片证据等基础能力已接入质量域关键流程，但培训读时审计导出仍可继续补强。 | `backend/app/modules/audit/router.py`；`backend/database/schema/audit_logs.py`；`backend/app/modules/training_compliance/router.py`；`backend/services/batch_records/service.py` | 质量域基础闭环已形成，但仍存在可继续深化的审计细项。 |
| 合规校验器、受控文档根和后端现行结构已收敛一致；当前 9 个门禁脚本全部通过。 | `backend/services/compliance/*_validator.py`；`scripts/validate_*_repo_compliance.py` | 门禁误报风险已显著下降，当前剩余风险主要在环境与非仓库证据。 |

## 整改问题清单

以下问题把 ISO 13485 关注点、会议纪要诉求与仓库证据统一到一张整改表中。

| 编号 | 关注点 | 当前不符合/不足 | 证据 | 风险 | 整改要求 | 优先级 |
| --- | --- | --- | --- | --- | --- | --- |
| DC-01 | 4.2.4 文档控制 | 受控体系文件主根已统一到 `docs/compliance/`，原 `doc/compliance/*` 断裂问题已修复。 | `backend/services/document_control/compliance_root.py`；合规门禁脚本 | 当前主要风险转为“评审误读历史副本”而非系统主根断裂。 | 保持 `docs/compliance/` 作为唯一受控主根，并在文档与脚本中持续禁止回退到双路径。 | 已完成 |
| DC-02 | 4.2.4/4.2.5 文档与记录控制 | 文件上传、上一版确认、审核、批准、生效、作废、下发、培训尚未形成统一闭环。 | 会议纪要 | 受控状态、版本关系、作废留痕与发布责任无法证明。 | 建立完整文控状态机和留痕记录，禁止同编号双“现行有效”。 | 第一优先级 |
| DC-03 | 文件检索与分类 | 文件无法从“文件编号 + 文件名”快速定位，且缺少“文件类别 + 从属产品/注册证”二维治理。 | 会议纪要 | 审核、培训、下发、变更影响分析无法精准检索。 | 文控模型必须补齐编号、名称、类别、产品、注册证、知识库目标等元数据。 | 第一优先级 |
| DD-01 | 7.3 设计开发文件 | `URS/SRS/追溯矩阵/验证计划/验证报告` 已迁入 `docs/compliance/*` 并纳入受控登记表。 | `docs/compliance/urs.md`；`docs/compliance/srs.md`；`docs/compliance/traceability_matrix.md`；`docs/compliance/validation_plan.md`；`docs/compliance/validation_report.md` | 当前剩余风险主要在独立评审文档是否同步更新，而非设计开发证据缺失。 | 保持受控登记表、验证文档和门禁脚本的一致性。 | 已完成 |
| TR-01 | 6.2 培训 | 培训矩阵引用已修复；培训确认已支持读时持久化、已知晓/有疑问和定向疑问闭环。 | `backend/database/schema/training_compliance.py`；`backend/app/modules/training_compliance/router.py`；`fronted/src/features/qualitySystem/training/*` | 当前剩余风险在于培训读时的审计导出能力仍可继续补强。 | 保持“生效触发培训 + 持久化阅读时长 + 定向提问闭环”，并补训练审计导出。 | 部分完成 |
| GOV-01 | 治理入口与授权 | `体系文件`治理中枢与质量域 capability 已落地，非 `admin` 的质量子管理员可使用真实质量 action。 | `fronted/src/routes/routeRegistry.js`；`fronted/src/components/layout/LayoutSidebar.js`；`backend/app/core/permission_models.py` | 当前主要风险不再是入口缺失，而是后续模块深度与测试覆盖需持续补强。 | 继续按 capability 合同扩展质量域模块，禁止回退到角色名硬编码。 | 已完成 |
| CC-01 | 7.3.9 变更控制 | 变更台账、评估、计划、审批、执行、跨部门确认、回归台账、文控联动尚未闭环。 | 会议纪要；`backend/services/compliance/gbz02_validator.py` | 变更完成后无法自动回归清单，也无法确保文件同步更新。 | 建立变更台账与计划闭环，强制挂接受控文件更新与确认。 | 第二优先级 |
| EQ-01 | 设备全生命周期 | 设备从采购到报废的全过程未形成统一台账、提醒和审批。 | 会议纪要 | 设备验收、使用、维护、计量、报废的记录链断裂。 | 建立设备资产主档与生命周期台账，按节点提醒责任人。 | 第一优先级 |
| MT-01 | 计量管理 | 计量附件、计量结果确认审批、到期提醒缺失。 | 会议纪要 | 设备合规状态与使用许可不可追溯。 | 计量记录、附件、审批、提醒与设备资产联动。 | 第二优先级 |
| MA-01 | 维护保养 | 维护计划、执行记录、到期提醒、确认审批缺失。 | 会议纪要 | 维护保养无法形成可审计台账。 | 维护计划与执行、审批、提醒能力与设备台账联动。 | 第二优先级 |
| BR-01 | 批记录管理 | 模板版控、实时填写、现场拍照、电子签名与导出能力已落地；后续仍需确认手签等效策略和更完整的生产/检验模板覆盖。 | `backend/app/modules/batch_records/router.py`；`backend/services/batch_records/service.py`；`fronted/src/features/batchRecords/BatchRecordsWorkspace.js` | 批记录基础链路已可用，但合规策略细化和业务模板覆盖仍有扩展空间。 | 保持模板版控、实时记录、照片证据、签名与导出能力，并补细化合规策略。 | 部分完成 |
| AUD-01 | 审计追踪 | 全局搜索、智能对话、文档调用记录没有纳入质量体系审计口径。 | 会议纪要；`backend/app/modules/audit/router.py`；`backend/database/schema/audit_logs.py` | 关键操作缺证据，不满足审计追踪要求。 | 扩展质量事件 taxonomy，记录搜索、对话、文档调用、审批、确认、作废、导出。 | 第二优先级 |
| VAL-01 | 合规校验器一致性 | 合规校验器已与现行代码结构和 `docs/compliance/` 收敛一致。 | `backend/services/compliance/*_validator.py`；`scripts/validate_*_repo_compliance.py` | 当前门禁误报已不再是主要风险。 | 继续把新增流程能力同步纳入门禁与单测。 | 已完成 |
| PMS-01 | 投诉/反馈/内审/管理评审 | 投诉待定，内审与管理评审尚无明确体系对象和记录出口。 | 会议纪要；仓库中未见对应受控域 | ISO 13485 后续闭环缺口仍在。 | 在路线图中预留独立工作流与受控记录域。 | 第三优先级 |

## `体系文件`治理中枢方案

### 1. 入口定位

`体系文件`不应只是一个文件列表页，而应是质量部子管理员执行全部体系动作的统一入口，承担以下职责：

- 作为所有受控文件、变更、培训、设备、计量、维护、批记录、证据导出的统一治理入口。
- 集中呈现待办审批、待确认培训、临期提醒、变更确认、设备到期、作废通知等任务。
- 作为质量审计和内部复核时的证据汇聚面板。

### 2. 导航与接入方式

基于当前仓库现状，新增方式应遵循现有模式：

- 在 `fronted/src/routes/routeRegistry.js` 新增独立路由，例如 `/quality-system`。
- 路由必须 `showInNav: true`，并通过现有 `guard.permission` 接入权限控制。
- `fronted/src/components/layout/LayoutSidebar.js` 继续通过 `NAVIGATION_ROUTES` 渲染，不新造第二套路由菜单系统。

### 3. 目标用户

- 质量管理员：拥有质量全域配置、审批、导出权限。
- 质量部子管理员：拥有质量域的日常执行权限，但不必拥有系统全局管理员权限。
- 文控专员：偏向文档控制、培训分派、作废下发。
- 设备管理员：偏向设备、计量、维护台账。
- 生产/检验用户：只在批记录、培训确认、指定确认环节拥有有限动作权限。

### 4. 页面信息架构

建议把`体系文件`治理中枢拆为以下一级模块：

1. 质量工作台
   - 待审核、待批准、待培训确认、待回复问题、临期提醒、最近作废、最近导出。
2. 文件控制
   - 文件上传、版本关系、审批、生效、作废、下发、查找、导出。
3. 培训与知晓
   - 培训分派、阅读确认、疑问闭环、逾期催办、培训记录。
4. 变更控制
   - 变更台账、评估、计划、执行、跨部门确认、关闭。
5. 设备全生命周期
   - 采购、验收、投用、维护、计量、报废。
6. 计量与维护
   - 计量计划、结果确认、附件、维护计划、执行记录。
7. 批记录
   - 模板、执行、签名、审阅、导出。
8. 审计与证据
   - 搜索日志、智能对话日志、文档调用日志、审批日志、导出记录。
9. 投诉与持续改进
   - 先保留入口，后续承接投诉、反馈、CAPA、内审、管理评审。

### 5. 质量子管理员权限模型

不应单独再造一套质量权限系统，而应扩展当前 capability/resource/action 模型。

建议新增的资源族如下：

| Resource | Actions | 说明 |
| --- | --- | --- |
| `quality_system` | `view`, `manage` | `体系文件`工作台访问与配置入口。 |
| `document_control` | `create`, `review`, `approve`, `effective`, `obsolete`, `publish`, `export` | 文档控制主动作。 |
| `training_ack` | `assign`, `acknowledge`, `review_questions` | 培训分派、知晓确认、疑问处理。 |
| `change_control` | `create`, `evaluate`, `approve`, `plan`, `confirm`, `close` | 变更台账与计划闭环。 |
| `equipment_lifecycle` | `create`, `accept`, `maintain`, `meter`, `retire` | 设备全生命周期。 |
| `metrology` | `record`, `confirm`, `approve` | 计量记录与审批。 |
| `maintenance` | `plan`, `record`, `approve` | 维护保养计划和执行。 |
| `batch_records` | `template_manage`, `execute`, `sign`, `review`, `export` | 批记录模板与执行。 |
| `audit_events` | `view`, `export` | 质量审计事件浏览与导出。 |

落点要求：

- 后端在 `backend/app/core/permission_models.py` 扩展 snapshot 结构。
- 前端在 `fronted/src/shared/auth/capabilities.js` 扩展 capability 判断。
- 页面与操作都通过 `PermissionGuard` 或 `canWithCapabilities` 接入，禁止角色名硬编码绕过。

## 关键流程整改要求

### A. 文控管理

文控管理是本次整改的核心起点，应先于其他域落地。

必须具备的流程和规则：

1. 文件上传
   - 上传时必须确认是否继承上一版。
   - 必填元数据包括：文件编号、文件名、文件类别、所属产品、注册证映射、版本、目标知识库、起草人。
2. 审核与批准
   - 审核、批准角色必须分离并留痕。
   - 生效前必须确认审批完成，禁止跳过审批直接生效。
3. 生效与作废
   - 生效后自动纳入受控文件登记表。
   - 作废必须由文控手动触发并留痕。
   - 作废下发必须通知指定人员；若策略要求确认或审批，则流程不能直接结束。
4. 文件检索
   - 至少支持按文件编号、文件名查找。
   - 必须支持按“文件类别”和“从属产品/注册证”两个维度筛选。
5. 知识库下发
   - 文控在生效时选择目标知识库。
   - 系统需保留文件下发和调用记录。

### B. 培训与知晓确认

针对会议纪要中的培训要求，必须形成显式流程：

1. 生效文件可触发培训任务。
2. 培训页面应显示阅读倒计时或累计阅读时长，默认规则为至少 15 分钟。
3. 被培训人必须做出明确动作：
   - `已知晓`
   - `有疑问`
4. 若选择`有疑问`，系统应通过站内信把问题发给发起人或文控责任人，并保留问答记录。
5. 培训完成不能只记录“看过了”，必须记录人、时间、状态、关联文件版本、处理结果。

### C. 变更控制

变更控制应采用台账化管理，而不是散点审批。

必须具备的台账字段和流程：

- 发起信息：发起人、变更内容、原因、影响对象、紧急程度。
- 评估信息：风险评估、影响分析、关联文件、关联设备、关联批记录。
- 计划信息：计划任务、责任人、计划节点、预计完成时间。
- 审批信息：评估审批、计划审批、完成确认审批。
- 执行信息：执行记录、附件、偏差说明、补充措施。
- 关闭信息：跨部门确认、关闭结论、是否触发文件更新。

规则要求：

- 节点到期前应自动提醒责任人。
- 计划完成后应流转至相关部门确认。
- 变更完成后自动回到变更台账，不依赖人工统计。
- 因变更产生的文件更新必须和文控关联，不能停留在口头状态。

### D. 设备、计量、维护保养

设备是会议纪要中明确的前期重点，应作为独立整改流。

设备全生命周期应覆盖：

- 采购
- 验收
- 投用
- 使用过程
- 维护保养
- 计量
- 报废

补充要求：

- 设备资产必须有主档和状态机。
- 计量记录必须支持附件、结果确认、审批。
- 维护计划和执行记录应与设备资产关联。
- 计量与维护应共享临期提醒能力。
- 设备类记录同样应具备导出和审计日志。

### E. 批记录管理

批记录管理要同时覆盖生产和检验两类场景。

最低整改要求：

- 模板管理：模板版本受控，可按产品/工艺/检验项目归档。
- 执行实时性：记录必须支持实时填写，不能事后批量补录后冒充实时。
- 证据采集：支持现场拍照上传。
- 签名要求：支持手签加口令或经质量确认的等效电子签名策略。
- 审计追踪：记录谁何时录入、修改、确认、复核。

### F. 审计追踪与导出

会议纪要里提到的“智能对话、全局搜索要有记录，文档有调用记录”，应纳入质量事件体系。

必须补齐：

- 全局搜索关键词、发起人、时间、结果范围。
- 智能对话的提问、使用人、时间、关联文档。
- 文档查看、下载、调用、导出、作废通知、培训确认等关键事件。
- 审计事件导出能力，便于内部审查和外部检查。

## 建议的核心台账/实体

为避免后续功能零散建设，建议至少规划以下实体：

| 实体 | 作用 |
| --- | --- |
| `ControlledDocument` | 文件主档，保存编号、名称、类别、产品、注册证、现行状态。 |
| `ControlledRevision` | 文件版本记录，保存版本、上一版关系、审批、生效、作废信息。 |
| `TrainingAssignment` | 培训分派记录，关联文件版本、人员、阅读时长、确认状态。 |
| `QualityQuestionThread` | 培训或文控中的疑问闭环消息线程。 |
| `ChangeRequest` | 变更台账主单。 |
| `ChangePlanItem` | 变更计划和节点责任拆解。 |
| `EquipmentAsset` | 设备资产主档。 |
| `MetrologyRecord` | 计量记录与附件。 |
| `MaintenanceRecord` | 维护计划和执行记录。 |
| `BatchRecordTemplate` | 批记录模板版本。 |
| `BatchRecordExecution` | 批记录执行实例。 |
| `QualityAuditEvent` | 质量域统一审计事件。 |

## 整改实施路线图（非本任务执行 Phase）

以下路线图用于后续立项和排期，不作为本次任务的执行 phase。

### R1. 文控基线恢复

- 目标：确定唯一受控主根，恢复受控文件登记表、设计开发文件和培训矩阵的有效链路。
- 重点：保持 `docs/compliance/` 作为唯一受控主根，并防止回退到双路径或历史副本混用。
- 结果：文控和校验器能基于真实受控文件工作。

### R2. `体系文件`入口与质量权限落地

- 目标：让质量部子管理员可以在非全局管理员前提下完成体系操作。
- 重点：新增路由、治理中枢页面和 capability 扩展。
- 结果：文控、培训、审批和站内信在同一入口运行。

### R3. 设备全生命周期先行

- 目标：以设备为前期第二重点，完成设备、计量、维护的台账与提醒。
- 重点：采购到报废全流程、临期提醒、确认审批、附件留痕。
- 结果：设备部和质量部共享可审计台账。

### R4. 变更控制闭环

- 目标：把变更从单点审批变成台账 + 计划 + 关闭确认闭环。
- 重点：计划审批、跨部门确认、自动回台账、文控联动。
- 结果：变更不再依赖人工汇总，且必然驱动文件更新。

### R5. 批记录电子化

- 目标：完成生产/检验批记录模板、实时记录、拍照、签名和导出。
- 重点：记录实时性和签名合规性。
- 结果：批记录从纸面或散落电子文件升级为可追溯电子记录。

### R6. 投诉、内审、管理评审与持续改进

- 目标：补齐 ISO 13485 后续闭环域。
- 重点：投诉待定事项、内部审核、管理评审、CAPA 关联。
- 结果：质量体系从“文件合规”扩展到“运行闭环合规”。

## Phase Plan

### P1: 交付 ISO 13485 整改文档包

- Objective: 产出一份基于当前仓库证据和会议纪要的详细整改文档，明确`体系文件`治理中枢方案、问题清单、关键流程和实施路线图，并配套可独立复核的测试计划。
- Owned paths: docs/tasks/iso-13485-20260413T153016/prd.md; docs/tasks/iso-13485-20260413T153016/test-plan.md; docs/tasks/iso-13485-20260413T153016/execution-log.md; docs/tasks/iso-13485-20260413T153016/test-report.md
- Dependencies: 可读取当前仓库结构与相关证据文件; 会议纪要和用户补充诉求完整可用
- Deliverables: 证据化整改文档; `体系文件`治理中枢方案; 文控、培训、变更、设备、计量、维护、批记录、审计等整改要求; 后续实施路线图; 独立评审测试计划

### P2: 冻结质量 capability 合同（对应工作包 P0）

- Objective: 以 `docs/tasks/iso-13485-20260413T153016/p0-p1-quality-permission-api.md` 为权威，冻结质量域 capability 的资源集合、action 集、`auth/me` capability 快照结构与拒绝语义，并保证前后端常量一致、前端可无二义性消费。
- Owned paths: backend/app/core/permission_models.py; backend/services/auth_me_service.py; fronted/src/shared/auth/capabilities.js; backend/tests/test_auth_me_service_unit.py; docs/tasks/iso-13485-20260413T153016/execution-log.md
- Dependencies: PermissionSnapshot 仍是后端 capability 计算的唯一入口; 前端 normalizeCapabilities 逻辑保持不变
- Deliverables: 稳定的质量 capability 合同（资源与 action 集）; `auth/me` 对质量子管理员返回真实质量 action; 明确的 403 拒绝语义（无角色名 fallback）

### P3: 质量域 API 鉴权收敛到 capability（对应工作包 P1）

- Objective: 将质量域相关后端 API 从 `AdminOnly` 或零散判断收敛到统一 capability 校验（fail-fast 403），并补齐/更新后端单测覆盖成功、拒绝与快照输出三类路径。
- Owned paths: backend/app/core/authz.py; backend/app/core/permission_resolver.py; backend/app/core/permission_models.py; backend/app/modules/document_control/router.py; backend/app/modules/training_compliance/router.py; backend/app/modules/change_control/router.py; backend/app/modules/equipment/router.py; backend/app/modules/metrology/router.py; backend/app/modules/maintenance/router.py; backend/app/modules/complaints/router.py; backend/app/modules/capa/router.py; backend/app/modules/internal_audit/router.py; backend/app/modules/management_review/router.py; backend/app/modules/audit/router.py; backend/tests/test_document_control_api_unit.py; backend/tests/test_training_compliance_api_unit.py; backend/tests/test_change_control_api_unit.py; backend/tests/test_equipment_api_unit.py; backend/tests/test_metrology_api_unit.py; backend/tests/test_maintenance_api_unit.py; backend/tests/test_audit_events_api_unit.py; docs/tasks/iso-13485-20260413T153016/execution-log.md; docs/tasks/iso-13485-20260413T153016/test-report.md
- Dependencies: `python -m pytest` 可用; 质量域相关服务可在单测中用临时 sqlite db 验证
- Deliverables: capability 合同摘要; 被替换掉的 `AdminOnly` 路由清单; 通过的 pytest 命令与结果

### P4: 批记录后端闭环

- Objective: 实现批记录后端数据模型、模板/执行/步骤写入/签名/复核/导出 API，并复用现有电子签名能力与审计日志。
- Owned paths: backend/database/schema/batch_records.py; backend/database/schema/ensure.py; backend/services/batch_records/service.py; backend/app/modules/batch_records/router.py; backend/app/main.py; backend/app/dependency_factory.py; backend/tests/test_batch_records_api_unit.py; docs/tasks/iso-13485-20260413T153016/execution-log.md; docs/tasks/iso-13485-20260413T153016/test-report.md
- Dependencies: P2 capability 合同已冻结并包含 `batch_records.*`; 现有电子签名服务可复用
- Deliverables: 批记录 schema/service/router; 电子签名与审计集成; 后端单测证据

### P5: 批记录前端工作区与浏览器验证

- Objective: 实现 `/quality-system/batch-records` 前端真实工作区，并补齐 capability 守卫、前端测试与浏览器验证证据。
- Owned paths: fronted/src/features/batchRecords/api.js; fronted/src/features/batchRecords/BatchRecordsWorkspace.js; fronted/src/pages/QualitySystemBatchRecords.js; fronted/src/pages/QualitySystemBatchRecords.test.js; fronted/e2e/tests/docs.quality-system.batch-records.spec.js; docs/tasks/iso-13485-20260413T153016/execution-log.md; docs/tasks/iso-13485-20260413T153016/test-report.md
- Dependencies: P4 批记录 API 已可用; 质量体系路由与 module catalog 已挂接
- Deliverables: 批记录前端工作区; Jest 测试证据; Playwright 浏览器证据

## Phase Acceptance Criteria

### P1

- P1-AC1: PRD 明确记录当前仓库的关键现实，包括文档主根冲突、`tobedeleted/compliance/*` 现状、导航接入方式、现有权限模型边界和审计/站内信/电子签名基础能力。
- P1-AC2: PRD 提供覆盖文控、设计开发文件、培训、`体系文件`入口、变更、设备、计量、维护、批记录、审计日志、投诉待定等事项的整改问题清单，并且每项都能追溯到仓库证据或会议纪要。
- P1-AC3: PRD 对`体系文件`治理中枢给出清晰方案，至少包含入口定位、一级模块、目标用户、接入方式以及基于现有 capability 模型的扩展建议。
- P1-AC4: PRD 把会议纪要中的关键流程要求细化为可执行规则，至少覆盖文件上传与上一版确认、审核/批准、生效/作废、培训 15 分钟知晓与提问闭环、知识库下发、变更台账与计划、设备与计量、批记录实时性与签名、搜索和智能对话留痕。
- P1-AC5: PRD 给出明确的整改优先级与路线图，并明确“文控 + 设备”是前期重点，同时强调单一受控主根和禁止 fallback 的实施原则。
- P1-AC6: `test-plan.md` 能让独立评审人在不依赖隐藏上下文的前提下，通过明确命令和人工检查步骤验证上述文档内容。
- Evidence expectation:
  - 评审人仅阅读 `prd.md` 与 `test-plan.md`，即可定位仓库证据、核对整改逻辑、判断文档是否完整可执行。

### P2

- P2-AC1: `backend/app/core/permission_models.py` 与 `fronted/src/shared/auth/capabilities.js` 中的 `QUALITY_CAPABILITY_ACTIONS` 资源集合与 action 集一致，并覆盖本工作包定义的质量资源。
- P2-AC2: `auth/me` 的 capability 快照结构稳定且可被前端 `normalizeCapabilities` 无二义性消费；质量子管理员（非 `admin`）至少具备一个非 `quality_system` 的质量 action。
- P2-AC3: capability 缺失或未授权时，后端拒绝语义为明确 `403`，detail 不回退到角色名硬编码（不出现 `admin_required` 作为兼容兜底）。
- Evidence expectation:
  - 代码常量对齐 + 单测断言（`test_auth_me_service_unit.py`）。

### P3

- P3-AC1: 文控、培训、变更、设备、计量、维保、投诉、CAPA、内审、管评、质量审计相关 API 以 capability 作为主鉴权入口，且不再使用 `AdminOnly` 作为质量域默认门。
- P3-AC2: 非 `admin` 用户在具备对应 capability 时可成功调用被授权的质量域 API；未授权访问明确返回 `403`。
- P3-AC3: 后端测试覆盖成功、拒绝、快照输出三类路径，并在建议的 pytest 命令下通过。
- Evidence expectation:
  - 更新后的 API 单测与 pytest 运行记录。

### P4

- P4-AC1: 后端存在批记录模板、执行实例、步骤写入、复核与导出基础模型和 API。
- P4-AC2: 批记录签名复用现有电子签名能力，不另建第二套签名体系。
- P4-AC3: 批记录关键动作写入审计日志，且未授权用户无法执行模板管理、签名或复核动作。
- P4-AC4: 后端单测覆盖模板创建、执行填写、签名/复核、导出与拒绝路径。

### P5

- P5-AC1: `/quality-system/batch-records` 存在真实前端工作区，可完成模板查看、执行记录填写、签名/复核入口与导出触发。
- P5-AC2: 批记录前端入口遵循质量 capability 守卫，并与质量系统模块目录一致。
- P5-AC3: 前端单测覆盖批记录页面渲染、能力守卫与主要交互。
- P5-AC4: Playwright 用例在真实浏览器中验证质量系统入口、批记录工作区与至少一个能力受限场景，并产生截图或等效证据文件。

## Done Definition

本次任务完成的标准是：

- `prd.md` 与 `test-plan.md` 均已完成，且内容符合模板要求。
- `validate_artifacts.py` 通过。
- P1-P5 的验收标准具备可复核性（文档 + capability 合同 + API 鉴权 + 批记录后端/前端与测试证据）。
- 文档阶段（P1）明确说明仅交付整改方案；本任务范围内的代码交付（P2-P5）不等同于“系统已满足 ISO 13485”。

## Blocking Conditions

以下情况会阻断后续实施，不应通过占位文件、双写兼容或静默降级规避：

- 无法确认唯一受控体系文件主根。
- 无法确认文件编号、文件类别、产品/注册证映射规则。
- 无法确认质量部子管理员、文控、设备管理员、审批人之间的授权边界。
- 无法确认电子签名和培训确认策略。
- 有人提议用假文件、空文件或双路径兼容来“先让校验器通过”。
