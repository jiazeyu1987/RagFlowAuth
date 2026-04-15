# 文控流程差异补齐并行工作包

- Parent Task: `document-control-flow-parallel-20260414T151500`
- Target Source: `C:\Users\BJB110\Desktop\文件控制流程初稿.pdf`
- Current Repo Baseline:
  - `backend/services/document_control/service.py`
  - `backend/app/modules/document_control/router.py`
  - `backend/services/training_compliance.py`
  - `backend/services/operation_approval/`
  - `backend/services/compliance/retired_records.py`
  - `fronted/src/pages/DocumentControl.js`

## 拆包结果

本次固定 `X=6`。6 份工作包分别对应目标流程里的 6 个独立责任域，按“先冻结合同，再拆后端生命周期，再接前端”的顺序组织。

工作包列表：

- `WS01` `ws01-approval-workflow-contract.md`
  - 会签、批准、标准化审核、驳回/重提、加签主合同
- `WS02` `ws02-training-gate-and-ack-loop.md`
  - 培训门禁、阅读确认、疑问闭环、培训记录
- `WS03` `ws03-controlled-release-and-distribution.md`
  - 受控发布、旧版回收、发布模式和台账
- `WS04` `ws04-department-ack-and-execution-confirmation.md`
  - 相关部门通知、提醒和确认闭环
- `WS05` `ws05-obsolete-retention-and-destruction.md`
  - 作废审批、访问控制、留存和销毁
- `WS06` `ws06-document-control-frontend-workspace.md`
  - 文控前端工作区、状态可视化和前后端接线

## 依赖图

- `WS01` 必须先完成。后续工作包不允许自行定义第二套审批状态机。
- `WS02` 依赖 `WS01` 的审批完成事件和文控修订合同。
- `WS03` 依赖 `WS01` 的审批合同，并消费 `WS02` 的培训门禁结果。
- `WS04` 依赖 `WS03` 产出的发布/分发记录。
- `WS05` 依赖 `WS03` 的发布/旧版替代语义，部分策略依赖 `WS04` 的执行确认结果。
- `WS06` 依赖前五个工作包冻结后的 API 和状态合同；可先做页面骨架，但最终接线必须等合同稳定。

## 推荐并行顺序

1. `WS01`
2. `WS02` 和 `WS03`
3. `WS04` 和 `WS05`
4. `WS06`

## 分配规则

- 一个 LLM 只接一个工作包，不跨包改写核心语义。
- 所有包都必须复用 `WS01` 冻结的术语、状态和事件名。
- 共享冲突点要显式处理，不允许隐式覆盖别人的设计。

高风险共享文件：

- `backend/app/modules/document_control/router.py`
- `backend/services/document_control/service.py`
- `backend/database/schema/ensure.py`

处理要求：

- 优先在各包中新增子模块，减少集中改同一文件。
- 对上述共享文件的改动只允许做接线和注册，不允许在不同包里各自扩写完整逻辑。
- 若多个包必须同时改这些文件，最后单独做一次集成合并，不在包内偷偷解决。

## 执行前必须确认的制度前提

- 培训是否是发布前阻断门禁。
- 驳回后是否必须终止当前实例并重新发起。
- 销毁是否由系统自动执行，还是仅由系统记录到期并要求线下处置。

如果这些前提被推翻，必须回到对应工作包修改合同，不允许由执行 LLM 临场拍板。

## 执行 Prompt

如果要直接把任务分发给不同 LLM，优先使用下面这些执行 prompt 文件：

- `prompt-ws01-approval-workflow-contract.md`
- `prompt-ws02-training-gate-and-ack-loop.md`
- `prompt-ws03-controlled-release-and-distribution.md`
- `prompt-ws04-department-ack-and-execution-confirmation.md`
- `prompt-ws05-obsolete-retention-and-destruction.md`
- `prompt-ws06-document-control-frontend-workspace.md`

分发前先读：

- `README.md`
- 对应 `ws*.md`
- `DISPATCH.md`
