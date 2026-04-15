# WS04：相关部门通知与执行确认

- Parent Task: `document-control-flow-parallel-20260414T151500`
- Owner Type: backend / notification / execution-ack
- Parallelism: 依赖 `WS03`；可与 `WS05` 并行

## 目标

补上目标流程中的“相关部门收到通知点击确认”链路，形成显式的部门通知、提醒和确认闭环。

## Owned Paths

- `backend/app/modules/document_control/router.py`
- `backend/services/notification/`
- `backend/app/modules/inbox/router.py`
- `backend/tests/test_document_control_api_unit.py`

## Shared Integration Paths

- `backend/services/document_control/service.py`
- `backend/database/schema/document_control.py`
- `backend/database/schema/ensure.py`

## 不在本包内

- 审批矩阵和标准化审核
- 培训分配与培训确认
- 发布台账和旧版回收
- 作废/销毁
- 前端工作区

## 当前差距

- 文控模块没有“相关部门确认”表、状态或接口。
- 仓库里相似的“跨部门确认”存在于变更控制模块，但语义不同，不能直接挪用。

## 实施要求

### 1. 确认对象

- 明确确认对象来自哪里：
  - 受控分发的部门列表
  - 或者发布动作显式传入的部门
- 若当前仓库缺少稳定部门映射前提，必须 fail-fast，而不是默认所有部门。

### 2. 确认状态

- 至少区分：
  - `pending`
  - `confirmed`
  - `overdue`
- 每条确认记录必须带部门、发布记录、确认人、确认时间、备注。

### 3. 提醒与通知

- 发布后自动创建站内通知或 inbox 项。
- 未确认项支持催办或超时提醒。
- 提醒动作必须可审计。

### 4. 与发布关系

- 只允许对已发布记录生成部门确认。
- 后续 `WS05` 如需用“执行确认完成”作为作废前提，必须消费本包状态，不允许再造一套字段。

## 验收标准

- 发布后能生成部门确认项。
- 部门确认有独立状态和审计记录。
- 提醒链路是显式建模，不借用变更控制的确认语义。
- 后续前端和作废流程可以稳定消费确认结果。

## 建议测试

```powershell
python -m pytest backend/tests/test_document_control_api_unit.py -q
```

重点补测：

- 发布后生成确认项
- 非目标部门无法确认
- 重复确认处理
- 超时提醒与状态变更

## 交付物

- 部门确认数据模型
- 通知 / inbox 事件类型与触发条件
- 确认接口与提醒规则
- 通过的测试清单
