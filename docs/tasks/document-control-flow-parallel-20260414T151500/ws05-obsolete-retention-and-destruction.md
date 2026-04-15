# WS05：作废、留存与销毁

- Parent Task: `document-control-flow-parallel-20260414T151500`
- Owner Type: backend / compliance / retention
- Parallelism: 依赖 `WS03`；可与 `WS04` 并行，但最终访问策略要能消费发布结果

## 目标

把目标流程里的“作废审批 -> 禁止访问 -> 留存 -> 到期销毁 -> 销毁记录”明确成可执行包，同时正面处理当前仓库文档把一部分留存/销毁划为仓库外残余项的事实。

## 关键前提

- 当前 `docs/compliance/release_and_retirement_sop.md` 与 `docs/compliance/retirement_plan.md` 明确把部分销毁处置放在仓库外。
- 本包必须先确认这条边界是否要被修改。
- 若制度所有者不允许系统内自动销毁，本包必须停在“记录留存截止 / 生成到期提醒 / 记录线下处置证明”的边界，不能偷偷删文件。

## Owned Paths

- `backend/services/compliance/retired_records.py`
- `backend/app/modules/knowledge/routes/retired.py`
- `backend/app/modules/knowledge/routes/files.py`
- `backend/services/document_control/service.py`
- `docs/compliance/release_and_retirement_sop.md`
- `docs/compliance/retirement_plan.md`
- `backend/tests/test_document_control_api_unit.py`

## Shared Integration Paths

- `backend/database/schema/document_control.py`
- `backend/database/schema/ensure.py`
- `backend/app/modules/document_control/router.py`

## 不在本包内

- 审批矩阵、标准化审核、加签
- 培训门禁
- 发布台账
- 部门确认通知
- 前端工作区渲染

## 当前差距

- 当前文控 `obsolete` 不是完整的作废审批链路。
- 普通知识库预览/下载主要拦截的是 `archived`，不是文控作废态。
- 合规文档仍把到期销毁放在仓库外残余项。

## 实施要求

### 1. 作废审批

- 作废必须是显式动作或显式流程，不允许继续直接 `effective -> obsolete`。
- 作废原因、申请人、批准人、时间必须可追溯。

### 2. 访问控制

- 一旦进入作废/留存态，普通下载和预览策略必须明确。
- 必须区分：
  - 现行文档访问
  - 作废留存期内受控访问
  - 销毁后不可访问

### 3. 留存期

- 每份作废文档必须显式记录 `retention_until` 或等价字段。
- 若法规年限无法由系统自动推导，必须要求调用方提供并留痕。

### 4. 销毁

- 若允许系统内执行销毁：
  - 需要显式的到期扫描入口
  - 需要销毁记录
  - 需要禁止无记录删除
- 若不允许系统内销毁：
  - 需要显式的到期提醒和线下处置证明挂载点
  - 不允许伪造“已自动删除”

### 5. 合规文档对齐

- `docs/compliance/` 中关于退役/留存/销毁的边界必须与代码事实一致。
- 不允许代码和 SOP 各说各话。

## 验收标准

- 作废成为显式审批或显式记录链路。
- 作废后访问策略清晰且与留存期绑定。
- 销毁策略和制度边界被显式对齐。
- 合规文档和代码事实一致。

## 建议测试

```powershell
python -m pytest `
  backend/tests/test_document_control_api_unit.py `
  backend/tests/test_retired_document_access_unit.py -q
```

重点补测：

- 作废前后访问策略变化
- 留存期内允许的受控访问
- 留存期到期后的阻断或销毁记录
- 合规模块导出和访问不会绕过作废策略

## 交付物

- 作废 / 留存 / 销毁状态与字段合同
- 访问控制规则
- SOP 同步更新
- 通过的测试清单
