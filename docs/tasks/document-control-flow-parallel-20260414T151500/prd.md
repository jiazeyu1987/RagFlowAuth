# Document Control Flow Gap Parallelization PRD

- Task ID: `document-control-flow-parallel-20260414T151500`
- Created: `2026-04-14T20:50:21`
- Workspace: `D:\ProjectPackage\RagflowAuth`
- User Request: `把文件控制流程初稿与当前系统差异，细化成可由不同 LLM 并行执行的独立工作文件`

## Goal

把桌面 PDF《文件控制流程初稿》与当前仓库实现之间的差异，拆成 6 份可由不同 LLM 独立执行的工作包。每个工作包必须明确边界、依赖、Owned Paths、验收标准和建议测试，后续可以直接作为执行输入。

## Scope

- 新建一个独立任务目录，沉淀总控工件和工作包索引。
- 输出 6 份与目标流程对齐的工作文件：
  - `WS01` 审批/会签/标准化审核主合同
  - `WS02` 培训门禁与培训确认闭环
  - `WS03` 受控发布、旧版回收和发布台账
  - `WS04` 相关部门通知与执行确认
  - `WS05` 作废、留存、销毁和访问控制
  - `WS06` 文控前端工作区接线
- 在 PRD 和 Test Plan 中固化依赖图和验收口径。

## Non-Goals

- 本任务不直接修改业务代码，不实现任何后端或前端行为。
- 本任务不代替业务方拍板培训门禁、销毁责任边界等制度决策；只能把这些前提显式写入工作包。
- 本任务不创建 fallback、兼容分支或“暂时沿用旧流程”的隐式方案。

## Preconditions

- 目标流程来源仍以桌面 PDF `C:\Users\BJB110\Desktop\文件控制流程初稿.pdf` 为准。
- 当前仓库中以下实现路径可读：
  - `backend/services/document_control/service.py`
  - `backend/app/modules/document_control/router.py`
  - `backend/services/training_compliance.py`
  - `backend/services/operation_approval/`
  - `backend/services/compliance/retired_records.py`
  - `fronted/src/pages/DocumentControl.js`
- `docs/tasks/` 可写，用于保存任务工件和工作包。

## Impacted Areas

- 审批与会签：`backend/services/operation_approval/`、`backend/app/modules/operation_approvals/`
- 文控主链路：`backend/services/document_control/`、`backend/app/modules/document_control/`
- 培训闭环：`backend/services/training_compliance.py`、`backend/app/modules/training_compliance/router.py`
- 退役与留存：`backend/services/compliance/retired_records.py`、`backend/app/modules/knowledge/routes/retired.py`
- 前端文控页面：`fronted/src/pages/DocumentControl.js`、`fronted/src/features/documentControl/`
- 合规模板与 SOP：`docs/compliance/`

## Phase Plan

### P1: 审批工作流主合同

- Objective: 固化 PDF 目标流程里的会签、批准、标准化审核、驳回/重提和加签规则，形成后续包都消费的唯一合同。
- Owned paths:
  - `docs/tasks/document-control-flow-parallel-20260414T151500/ws01-approval-workflow-contract.md`
- Dependencies: 无。
- Deliverables:
  - 工作包文档
  - 冻结后的流程状态/接口/审计边界

### P2: 培训门禁与确认闭环

- Objective: 把“培训（若需要）”从当前的生效后动作，重构为与目标流程兼容的显式门禁或显式阻断前提。
- Owned paths:
  - `docs/tasks/document-control-flow-parallel-20260414T151500/ws02-training-gate-and-ack-loop.md`
- Dependencies:
  - `P1`
- Deliverables:
  - 工作包文档
  - 对培训分配、阅读时长、疑问闭环和阻断条件的执行说明

### P3: 受控发布与旧版回收

- Objective: 定义发布、旧版替代、受控标识、作废标识、自动/人工模式和台账留痕。
- Owned paths:
  - `docs/tasks/document-control-flow-parallel-20260414T151500/ws03-controlled-release-and-distribution.md`
- Dependencies:
  - `P1`
  - `P2`
- Deliverables:
  - 工作包文档
  - 发布与旧版回收的最小实现边界

### P4: 部门通知与执行确认

- Objective: 定义发布后“相关部门收到通知并点击确认”的数据模型、提醒链路和确认闭环。
- Owned paths:
  - `docs/tasks/document-control-flow-parallel-20260414T151500/ws04-department-ack-and-execution-confirmation.md`
- Dependencies:
  - `P3`
- Deliverables:
  - 工作包文档
  - 部门确认的接口、状态和提醒规则

### P5: 作废、留存与销毁

- Objective: 定义作废审批、访问拦截、留存期、销毁记录与合规边界，解决当前“仓库外残余项”和目标流程的冲突。
- Owned paths:
  - `docs/tasks/document-control-flow-parallel-20260414T151500/ws05-obsolete-retention-and-destruction.md`
- Dependencies:
  - `P3`
  - `P4`
- Deliverables:
  - 工作包文档
  - 作废/留存/销毁执行边界

### P6: 文控前端工作区

- Objective: 把当前“直接改状态”的文控页面改成消费前五个工作包合同的工作区。
- Owned paths:
  - `docs/tasks/document-control-flow-parallel-20260414T151500/ws06-document-control-frontend-workspace.md`
- Dependencies:
  - `P1`
  - `P2`
  - `P3`
  - `P4`
  - `P5`
- Deliverables:
  - 工作包文档
  - 前端页面、Hook、测试和阻断提示的接线范围

## Phase Acceptance Criteria

### P1

- P1-AC1: `WS01` 明确冻结“会签 -> 批准 -> 标准化审核”的顺序，并禁止各后续包自行改写。
- P1-AC2: `WS01` 明确“不同意/驳回”与“重新发起”的语义，不允许后续包各自定义退回规则。
- Evidence expectation: `ws01-approval-workflow-contract.md` 含目标、Owned Paths、依赖、非目标、验收和建议测试。

### P2

- P2-AC1: `WS02` 明确培训是目标流程的一部分，并写清阻断条件与未满足时的 fail-fast 行为。
- P2-AC2: `WS02` 明确培训指派来源、阅读确认、疑问线程和培训记录边界。
- Evidence expectation: `ws02-training-gate-and-ack-loop.md` 对应条目完整。

### P3

- P3-AC1: `WS03` 明确“发布”“旧版替代/回收”“自动/人工模式”“发布台账”的实现边界。
- P3-AC2: `WS03` 明确不得继续沿用当前“effective 时直接置 obsolete 但不留发布记录”的行为。
- Evidence expectation: `ws03-controlled-release-and-distribution.md` 对应条目完整。

### P4

- P4-AC1: `WS04` 明确部门确认对象、提醒机制、确认状态和访问入口。
- P4-AC2: `WS04` 明确这部分不再借用变更控制模块的确认流程语义。
- Evidence expectation: `ws04-department-ack-and-execution-confirmation.md` 对应条目完整。

### P5

- P5-AC1: `WS05` 明确作废、留存和销毁的状态及访问策略。
- P5-AC2: `WS05` 明确当前仓库外残余项与目标流程冲突的处理前提，不允许静默降级。
- Evidence expectation: `ws05-obsolete-retention-and-destruction.md` 对应条目完整。

### P6

- P6-AC1: `WS06` 明确前端不再保留“Move to approved/effective/obsolete”这类直接状态按钮。
- P6-AC2: `WS06` 明确前端如何消费前五个包的 API、阻断状态和审计可见信息。
- Evidence expectation: `ws06-document-control-frontend-workspace.md` 对应条目完整。

## Done Definition

- 本任务目录存在一份总览索引 `README.md` 和 6 份工作文件。
- `prd.md` 与 `test-plan.md` 已从模板替换成可执行内容。
- 每份工作文件都包含：
  - 目标
  - Parallelism / Dependencies
  - Owned Paths
  - Shared Integration Paths 或冲突说明
  - 非目标
  - 实施要求
  - 验收标准
  - 建议测试
- 任务状态处于可交接给执行阶段的状态。

## Blocking Conditions

- 目标 PDF 被替换或撤销，导致目标流程不再成立。
- 业务方明确否认 PDF 中的关键步骤但未给出替代规则，尤其是：
  - 培训是否阻断发布
  - 驳回后是否必须终止并重发
  - 销毁是否由系统自动执行
- 仓库关键入口缺失，无法定位当前真实实现。
