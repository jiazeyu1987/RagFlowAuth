# WS03：受控发布、旧版回收与发布台账

- Parent Task: `document-control-flow-parallel-20260414T151500`
- Owner Type: backend / release / document-control
- Parallelism: 依赖 `WS01` 和 `WS02`；完成后供 `WS04`、`WS05`、`WS06` 消费

## 目标

把当前“修订变成 `effective` 时顺手把上一版置 `obsolete`”的实现，升级成目标流程里的受控发布链路：

- 发布新版本
- 回收旧版本
- 显式区分自动模式 / 文控人工模式
- 生成受控标识、作废标识、对应时间
- 形成发布台账

## Owned Paths

- `backend/services/document_control/service.py`
- `backend/app/modules/document_control/router.py`
- `backend/database/schema/document_control.py`
- `backend/tests/test_document_control_service_unit.py`
- `backend/tests/test_document_control_api_unit.py`

## Shared Integration Paths

- `backend/database/schema/ensure.py`
- `backend/services/compliance/review_package.py`

## 不在本包内

- 审批矩阵、标准化审核和驳回重提
- 培训疑问闭环
- 部门确认
- 作废/销毁审批
- 前端页面渲染

## 当前差距

- 当前没有“发布”这个独立动作，只是直接改修订状态。
- 没有发布台账、发布模式、旧版回收记录。
- 旧版变 `obsolete` 之后也没有与“发布动作”关联的业务留痕。

## 实施要求

### 1. 发布动作独立化

- 发布必须是显式动作，前提至少包括：
  - `WS01` 审批已通过
  - 如需要培训，则 `WS02` 门禁满足
- 不允许继续把“审批通过”自动等价成“已生效已发布”。

### 2. 发布模式

- 至少建模：
  - `automatic`
  - `manual_by_doc_control`
- 发布台账必须记录模式、操作人、时间、目标修订、被替代修订。

### 3. 旧版回收 / 替代

- 旧版替代必须与发布动作绑定。
- 明确区分：
  - 旧版因新版本替代而退出现行
  - 文件生命周期上的作废
- 这两个概念不能继续混在同一个 `obsolete` 语义里。

### 4. 受控标识

- 必须有受控状态和受控时间。
- 被替代版本必须有替代/回收时间和来源修订信息。

### 5. 审计和导出

- 发布与旧版回收必须被审计。
- 后续审查包/登记表导出需要能消费发布台账。

## 验收标准

- 发布是显式接口和显式记录，不再只是状态跳转副作用。
- 发布前校验审批结果和培训门禁。
- 上一版退出现行时有清晰的替代记录。
- 自动模式和人工模式都被建模并可审计。

## 建议测试

```powershell
python -m pytest `
  backend/tests/test_document_control_service_unit.py `
  backend/tests/test_document_control_api_unit.py -q
```

重点补测：

- 未完成审批或培训时拒绝发布
- 发布成功后生成发布记录
- 发布新版本时旧版替代关系正确
- 自动 / 人工模式记录字段正确

## 交付物

- 发布台账和状态字段设计
- 发布接口与校验规则
- 旧版替代 / 回收规则说明
- 通过的后端测试清单
