# WS02：培训门禁与确认闭环

- Parent Task: `document-control-flow-parallel-20260414T151500`
- Owner Type: backend / training / acknowledgment
- Parallelism: 依赖 `WS01`；可与 `WS03` 并行，但最终发布门禁合同必须先对齐

## 目标

把当前“仅对已生效版本生成培训任务”的实现，调整成与目标流程一致的培训链路。目标流程要求：

- 文件如需培训，培训必须是显式步骤
- 受训人阅读、确认理解
- 有疑问时发起沟通线程
- 系统生成培训记录

## 前置假设

- 目标流程默认认为 `training_required=true` 时，培训是发布前的门禁条件。
- 如果业务方否认这一前提，本包必须停止并上报，不允许静默保留当前“生效后再培训”的旧逻辑。

## Owned Paths

- `backend/services/training_compliance.py`
- `backend/app/modules/training_compliance/router.py`
- `backend/database/schema/training_ack.py`
- `backend/database/schema/training_compliance.py`
- `backend/tests/test_training_compliance_api_unit.py`
- `backend/tests/test_document_control_api_unit.py`

## Shared Integration Paths

- `backend/services/document_control/service.py`
- `backend/app/modules/document_control/router.py`
- `backend/database/schema/ensure.py`

只允许补充门禁接线和合同字段，不允许在这里重新定义审批语义。

## 不在本包内

- 审批矩阵和标准化审核
- 发布台账和旧版回收
- 部门确认
- 作废、留存、销毁
- 前端展示

## 当前差距

- 当前只能对 `effective` 修订生成培训任务。
- 培训分配入口默认可发给全部 active 用户，不支持按部门收敛。
- 文控修订没有“待培训完成”的显式阻断状态。

## 实施要求

### 1. 门禁状态

- 为文控修订补充培训门禁结果，而不是继续把培训当成独立旁路。
- 至少区分：
  - 不需要培训
  - 待分配培训
  - 培训进行中
  - 培训已完成
  - 培训存在未解决疑问

### 2. 培训对象来源

- 支持按显式人员列表分配。
- 支持按部门选人，或给出为什么当前仓库缺少该前提的 fail-fast 错误。
- 不允许继续把“未指定 assignee”解释成默认全员，除非业务明确要求。

### 3. 阅读与确认

- 继续保留最短阅读时长、阅读心跳、确认理解和疑问线程。
- 培训记录必须与 `controlled_revision_id`、版本号、用户、时间、决策绑定。

### 4. 疑问闭环

- 有疑问时必须阻断培训完成。
- 疑问线程关闭后，培训对象才能再次完成确认。
- 疑问与处理结果必须保留审计轨迹。

### 5. 对文控发布的影响

- `WS03` 只能消费本包的稳定门禁结果。
- 门禁未满足时必须显式拒绝发布，不允许前端或后端偷偷放行。

## 验收标准

- 培训任务不再仅依赖 `effective` 版本。
- 需要培训的文控修订具备显式培训门禁状态。
- 支持“确认理解”和“提出疑问”两类结果，并保留培训记录。
- 发布端能够消费本包给出的门禁结果。

## 建议测试

```powershell
python -m pytest `
  backend/tests/test_training_compliance_api_unit.py `
  backend/tests/test_document_control_api_unit.py -q
```

重点补测：

- 需要培训但未分配对象时拒绝进入发布链路
- 阅读时长不足时拒绝确认
- 疑问未关闭时培训不能完成
- 培训完成后门禁状态可供发布消费

## 交付物

- 培训门禁状态合同
- 培训分配与确认 API 说明
- 文控修订与培训结果的关联方式
- 通过的测试清单
