# WS01：审批工作流主合同

- Parent Task: `document-control-flow-parallel-20260414T151500`
- Owner Type: backend / workflow / operation-approval
- Parallelism: 必须先完成；`WS02` 到 `WS06` 全部依赖本包冻结的合同

## 目标

把当前文控模块从“前端直接驱动 `draft -> in_review -> approved -> effective -> obsolete`”改成与目标 PDF 一致的显式审批链路：

- 会签
- 批准
- 标准化审核
- 驳回 / 终止 / 重新发起
- 加签

本包负责冻结整个审批主合同，后续包只能消费，不允许再发明第二套状态机。

## 冻结决策

- 复用现有 `operation_approval` 能力作为审批引擎，不新造第二套通用工作流系统。
- 文控审批顺序固定为：
  - `cosign`
  - `approve`
  - `standardize_review`
- 驳回是显式终止当前审批实例，不允许“假退回但沿用同一实例继续审批”的隐式分支。
- 缺审批矩阵、缺步骤成员、缺角色映射时必须 fail-fast。

## Owned Paths

- `backend/services/operation_approval/`
- `backend/app/modules/operation_approvals/router.py`
- `backend/services/document_control/service.py`
- `backend/app/modules/document_control/router.py`
- `backend/database/schema/document_control.py`
- `backend/tests/test_document_control_service_unit.py`
- `backend/tests/test_document_control_api_unit.py`

## Shared Integration Paths

- `backend/database/schema/ensure.py`
- `backend/app/main.py`

本包可以改这些文件做注册和接线，但后续包不应再在这里扩写业务语义。

## 不在本包内

- 培训分配、培训确认和疑问闭环
- 发布、旧版回收和发布台账
- 部门通知与执行确认
- 作废、留存、销毁
- 前端工作区渲染

## 当前差距

- 当前文控只有 5 个状态，且只允许单向前进。
- 没有审批矩阵、多人会签、加签、驳回/重提。
- 没有“标准化审核”这个独立步骤。
- 前端当前仍允许直接触发状态跳转。

## 实施要求

### 1. 审批合同

- 为文控修订定义审批操作类型，例如 `document_control_revision_approval`。
- 审批矩阵按 `document_type` 或等价类别解析；若输入字段不足以映射矩阵，本包必须先补合同字段。
- 每个步骤必须能区分：
  - 步骤类型
  - 审批规则 `all|any`
  - 步骤成员来源
  - 超时提醒参数

### 2. 修订状态与审批状态分离

- 文控修订自身状态不再直接等价于审批步骤状态。
- 必须显式区分：
  - 修订草稿/待提交流程
  - 审批进行中
  - 审批驳回
  - 审批通过待发布
- 不允许继续让前端直接把修订改成 `approved` 或 `effective`。

### 3. 驳回与重提

- 驳回必须保留驳回意见、节点、操作人和时间。
- 重新发起必须产生新的审批实例，不能无痕重开旧实例。
- 若业务最终要求“原单重提”，也必须作为显式合同，不允许先偷偷实现。

### 4. 加签

- 只允许对当前活动步骤加签。
- 加签必须保留操作记录、原因和新增成员信息。
- 加签不能绕过原步骤审批规则。

### 5. 标准化审核

- 标准化审核必须是单独步骤，不可继续混在普通 review notes 里。
- 至少覆盖模板、格式、页码等检查项的承载入口。

### 6. 审计与通知

- 审批创建、步骤激活、通过、驳回、加签、重提都必须有审计事件。
- 超时提醒必须以显式字段和事件建模，后续提醒实现可由其他包消费。

## 验收标准

- 文控审批主链路不再依赖直接状态跳转。
- 能从类别/矩阵解析出会签、批准、标准化审核 3 类步骤。
- 驳回和重提有显式实例语义与审计记录。
- 加签被建模为当前步骤上的受控动作。
- 后续工作包无需重新定义审批状态或审批事件。

## 建议测试

```powershell
python -m pytest `
  backend/tests/test_document_control_service_unit.py `
  backend/tests/test_document_control_api_unit.py -q
```

重点补测：

- 审批矩阵缺失时拒绝提交流程
- 会签 / 批准 / 标准化审核顺序
- 驳回后必须终止当前实例
- 重提生成新实例
- 加签后成员与审计事件正确

## 交付物

- 审批主合同实现说明
- 关键状态/事件名清单
- 审批矩阵解析规则
- 通过的后端测试清单
