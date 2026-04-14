# P4：批记录模块工作包

- Parent Task: `iso-13485-20260413T153016`
- Source PRD: `docs/tasks/docs-tasks-iso-13485-20260413t153016-prd-md-iso--20260414T122156/prd.md`
- Owner Type: backend + frontend / batch records
- Parallelism: 可与 `p2-quality-system-frontend.md` 并行预布线，但最终联调依赖 P0-P1 提供 `batch_records.*` capability 合同

## 目标

把 `batch_records` 从声明态补齐为真实业务模块，至少交付：

- 模板管理
- 执行实例
- 步骤写入
- 签名
- 复核
- 导出

并接入质量系统入口。

## Owned Paths

- `backend/database/schema/*batch*`
- `backend/services/*batch*`
- `backend/app/modules/*batch*`
- `backend/app/main.py`
- `backend/app/dependencies.py`
- `backend/tests/test_batch_records_api_unit.py`
- 需要扩展的电子签名/审计相关测试
- `fronted/src/pages/*Batch*`
- `fronted/src/features/*batch*`
- `fronted/src/features/qualitySystem/moduleCatalog.js`
- `fronted/src/pages/QualitySystem.js`
- 新增或修改的批记录前端测试
- 如需浏览器验证：`fronted/e2e/tests/docs.quality-system.spec.js`

## 不在本工作包内

- 不定义新的质量 capability 名称
- 不负责文控主根迁移
- 不负责通用质量系统其它模块的接线

## 必须遵守的约束

- 签名必须复用现有电子签名能力，不另建第二套签名体系
- 所有关键动作必须写审计日志
- 不允许“事后批量补录再冒充实时”
- 如果实时性策略当前做不到，必须明确失败，不返回伪成功

## 推荐切分方式

### 后端子任务

- schema：模板、执行、签名/复核记录
- service：状态机、步骤写入、导出
- router：模板/执行/签名/复核/导出 API
- 审计与电子签名接线

### 前端子任务

- `/quality-system/batch-records` 工作区
- 模板列表
- 执行详情/填写
- 签名与复核入口
- 导出触发
- capability 守卫

## 对其他 LLM 的依赖

- P0-P1：`batch_records` capability 合同和 API 授权语义
- P2：质量系统入口最终路由位置；如同一文件有冲突，以本工作包定义的批记录入口为准并协调合并

## 验收标准

- 后端存在模板、执行、签名、复核、导出 API
- 签名复用现有电子签名能力
- 关键动作进入审计日志
- 未授权用户无法执行模板管理、签名或复核
- 前端存在真实工作区并挂到 `/quality-system/batch-records`
- 至少有一条浏览器正向路径可复核

## 建议测试

```powershell
python -m pytest backend/tests/test_batch_records_api_unit.py -q
Set-Location 'D:\ProjectPackage\RagflowAuth\fronted'
$env:CI='true'
npm test -- --watch=false --runInBand *Batch*.test.js
npx playwright test e2e/tests/docs.quality-system.spec.js --workers=1
```

## 交付物

- 批记录后端接口与数据模型
- 批记录前端工作区
- 电子签名/审计集成说明
- 单测与浏览器验证证据
