# ISO 13485 多 LLM 开发文档包总览

## 来源输入

- 源整改 PRD：`docs/tasks/iso-13485-20260413T153016/prd.md`
- 当前拆解任务 PRD：`docs/tasks/iso-13485-prd-llm-20260413T162500/prd.md`
- 当前仓库真实落点：
  - 文档/合规：`backend/services/compliance/*`、`backend/app/modules/documents/*`
  - 培训/站内信：`backend/app/modules/training_compliance/*`、`backend/app/modules/inbox/*`
  - 变更：`backend/app/modules/emergency_changes/*`
  - 审计：`backend/app/modules/audit/*`
  - 入口与权限：`fronted/src/routes/routeRegistry.js`、`fronted/src/components/layout/LayoutSidebar.js`、`fronted/src/shared/auth/capabilities.js`、`backend/app/core/permission_models.py`

## 拆解目标

把“一个整改总纲”拆成一组可以交给不同 LLM 独立推进的工作流文档，优先满足：

- 写入边界尽量不重叠
- 共享接口有唯一 owner
- 可分批并行
- 上游缺口不被误开发

## 文档清单

| 文档 | 作用 | 推荐 owner |
| --- | --- | --- |
| `01-shared-interfaces.md` | 冻结共享接口、能力名、路由前缀、通知与审计结构 | 主控 LLM / 架构 owner |
| `WS01-controlled-doc-baseline.md` | 文控基线、受控文件生命周期、合规门禁修复 | 后端主导，全栈配合 |
| `WS02-quality-system-hub-and-auth.md` | `体系文件`入口、权限模型、工作台壳层 | 前端主导，全栈配合 |
| `WS03-training-and-inbox-loop.md` | 培训确认、15 分钟知晓、疑问闭环、站内信 | 全栈 |
| `WS04-change-control-ledger.md` | 变更台账、计划、确认、回归台账与文控关联 | 全栈偏后端 |
| `WS05-equipment-metrology-maintenance.md` | 设备生命周期、计量、维护保养、提醒 | 全栈偏后端 |
| `WS06-batch-records-and-signature.md` | 批记录模板、执行、拍照、签名、导出 | 全栈 |
| `WS07-audit-and-evidence-export.md` | 审计事件 taxonomy、证据导出、搜索/对话留痕 | 后端主导，全栈配合 |
| `WS08-complaints-and-governance-closure.md` | 投诉、CAPA、内审、管理评审、供应商/环境确认闭环 | 后端主导，需求先行 |

## 推荐并行波次

### Wave A：可先行启动

- `WS01` 文控基线与合规门禁
- `WS02` 体系入口与权限
- `WS05` 设备/计量/维护
- `WS07` 审计与证据导出

### Wave B：依赖共享契约冻结后启动

- `WS03` 培训与站内信闭环
  - 依赖 `WS01` 的受控文件事件
  - 依赖 `WS02` 的能力模型
- `WS04` 变更控制台账
  - 依赖 `WS01` 的文档关联契约
  - 依赖 `WS02` 的入口和权限
  - 依赖 `WS07` 的审计事件 schema

### Wave C：后续启动

- `WS06` 批记录与电子签名
  - 依赖 `WS02` 的入口与权限
  - 依赖 `WS07` 的审计与证据结构

### Wave D：等待上游补充后启动

- `WS08` 投诉、CAPA、内审、管理评审等闭环域

## 共享文件 owner 约束

| 共享区域 | 唯一 owner | 其他工作流规则 |
| --- | --- | --- |
| `fronted/src/routes/routeRegistry.js` | `WS02` | 其他工作流只提路由需求，不直接改 |
| `fronted/src/components/layout/LayoutSidebar.js` | `WS02` | 其他工作流不直接改 |
| `fronted/src/shared/auth/capabilities.js` | `WS02` | 其他工作流消费能力名 |
| `backend/app/core/permission_models.py` | `WS02` | 其他工作流消费能力名 |
| 通知 payload 结构 | `WS03` | 其他工作流按共享契约发通知 |
| 通用审计事件 schema | `WS07` | 其他工作流只在各自模块里埋点 |
| 受控文件实体与生命周期 | `WS01` | 其他工作流只引用，不重定义 |

## 不能直接分发给编码 LLM 的上游缺口

以下事项出现在会议讨论中，但在源 PRD 里还不够开发化，本次只记录，不直接拆成编码任务：

- 钉钉审批流程平移
- Windchill / Teamcenter / 冠骋对标研究
- 设备负责人“李欣”的正式组织口确认
- 培训方式分类细则
- 投诉流程完整闭环细则

## 交接总规则

1. 每个 LLM 只修改自己工作流文档里声明的写入边界。
2. 任何共享接口的变更，必须先改 `01-shared-interfaces.md` 再编码。
3. 若发现需要长期共享同一核心文件，应回退到主控 LLM 重新划分边界。
4. 若需求来自会议纪要但不在源 PRD 中，应先补需求，不直接编码。
