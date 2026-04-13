# WS01：受控文件基线与合规门禁

- Workstream ID: `WS01`
- 推荐 owner：后端主导，全栈配合
- 独立性：高

## 目标

把源 PRD 中与文控基线相关的内容拆成一个先行工作流，优先解决“唯一受控主根、受控文件生命周期、审核包/校验器一致性、文件编号分类、知识库下发”的基础问题。

## 来源需求

- 源 PRD 问题项：`DC-01`、`DC-02`、`DC-03`、`DD-01`、`VAL-01`
- 源 PRD 章节：文控管理、建议的核心台账/实体、整改实施路线图 `R1`

## 负责边界

- 唯一受控文件主根的实现落点。
- `ControlledDocument` / `ControlledRevision` 的数据模型和生命周期。
- 文件编号、文件名、文件类别、产品、注册证、目标知识库等元数据。
- 生效、作废、上一版继承、受控登记表挂接。
- 审核包导出和合规校验器的路径一致性修复。
- 将 `URS/SRS/追溯矩阵/验证计划/验证报告` 等证据纳入受控主根的迁移方案。

## 不负责范围

- `体系文件`工作台导航和权限模型。
- 培训 15 分钟确认与疑问闭环的业务流程。
- 变更台账。
- 设备、计量、维护和批记录。
- 通用审计事件 schema 设计。

## 代码写入边界

后端 owner：

- `backend/services/compliance/*`
- `backend/app/modules/documents/*`
- `backend/services/documents/*`
- `backend/database/schema/training_compliance.py`

前端 owner：

- `fronted/src/features/knowledge/upload/*`
- `fronted/src/features/knowledge/documentBrowser/*`
- `fronted/src/pages/KnowledgeUpload.js`
- `fronted/src/pages/DocumentBrowser.js`

允许新增：

- `backend/app/modules/document_control/*`
- `backend/services/document_control/*`
- `fronted/src/features/documentControl/*`
- `fronted/src/pages/DocumentControl.js`

禁止主动修改：

- `fronted/src/routes/routeRegistry.js`
- `fronted/src/components/layout/LayoutSidebar.js`
- `fronted/src/shared/auth/capabilities.js`
- `backend/app/core/permission_models.py`
- `backend/app/modules/audit/*`

## 共享接口

本工作流拥有：

- `ControlledDocument`
- `ControlledRevision`
- 文档状态枚举：`draft`、`in_review`、`approved`、`effective`、`obsolete`
- 事件：`controlled_revision_effective`、`controlled_revision_obsolete`

本工作流消费：

- `WS02` 的能力资源名和入口路由壳层
- `WS03` 的通知 payload 契约
- `WS07` 的审计事件结构

## 依赖关系

- 可最早启动，是整个拆解包的前置工作流之一。
- 会阻塞 `WS03` 培训、`WS04` 变更关联和 `WS07` 的部分证据导出。

## 验收标准

- 唯一受控主根在代码和文档层都有唯一来源，不再双写。
- 受控文件生命周期、上一版关系和作废状态可被明确表达。
- 文件能按编号、名称、文件类别、产品/注册证检索。
- 审核包和校验器不再依赖失效路径。
- 生效文件能发出标准化事件供 `WS03` 等消费。

## 交接给 LLM 的规则

1. 只处理文控基线和合规门禁，不接手工作台导航。
2. 不自行创建新的权限资源名，直接使用 `WS02` 冻结的能力名。
3. 所有通知和审计字段都按共享契约输出，不自行新增字段。
4. 如果必须改共享契约，先更新 `01-shared-interfaces.md`。
