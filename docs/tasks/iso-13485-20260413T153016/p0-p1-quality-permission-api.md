# P0-P1：质量权限与 API 鉴权工作包

- Parent Task: `iso-13485-20260413T153016`
- Source PRD: `docs/tasks/docs-tasks-iso-13485-20260413t153016-prd-md-iso--20260414T122156/prd.md`
- Owner Type: backend / auth / permission
- Parallelism: 可与 `p2-quality-system-frontend.md`、`p3-compliance-root-migration.md`、`p4-batch-records.md` 并行，但必须先冻结 capability 合同

## 目标

把质量域从“只有入口可见”改成“质量子管理员可基于 capability 执行真实动作”，并把质量相关 API 从 `AdminOnly` 或零散判断收敛到统一的 capability 校验。

本工作包同时覆盖：

- P0：冻结质量 capability 合同与授权边界
- P1：把后端 API 鉴权切换到质量 capability

## 必须先确认的合同

以下内容由本工作包定义并冻结，其他 LLM 直接依赖，不各自发明：

- 质量资源集合：
  - `quality_system`
  - `document_control`
  - `training_ack`
  - `change_control`
  - `equipment_lifecycle`
  - `metrology`
  - `maintenance`
  - `batch_records`
  - `audit_events`
  - `complaints`
  - `capa`
  - `internal_audit`
  - `management_review`
- 每个资源的 action 集
- `auth/me` 中 capability 快照结构
- 非授权请求的拒绝语义：明确 `403`，不回退到角色名硬编码

## Owned Paths

- `backend/app/core/permission_models.py`
- `backend/app/core/authz.py`
- `backend/app/core/permission_resolver.py`
- `backend/services/auth_me_service.py`
- `backend/app/modules/document_control/router.py`
- `backend/app/modules/training_compliance/router.py`
- `backend/app/modules/change_control/router.py`
- `backend/app/modules/equipment/router.py`
- `backend/app/modules/metrology/router.py`
- `backend/app/modules/maintenance/router.py`
- `backend/app/modules/complaints/router.py`
- `backend/app/modules/capa/router.py`
- `backend/app/modules/internal_audit/router.py`
- `backend/app/modules/management_review/router.py`
- `backend/app/modules/audit/router.py`
- `backend/tests/test_auth_me_service_unit.py`
- 新增或修改的质量域后端测试

## 不在本工作包内

- 不负责前端路由接线和页面渲染
- 不负责 `doc/compliance` 到 `docs/compliance` 的迁移
- 不负责批记录前后端业务实现，只负责其 capability 合同

## 对其他 LLM 的输出契约

完成后必须保证：

1. `fronted/src/shared/auth/capabilities.js` 可以无二义性消费后端 capability。
2. 前端 LLM 不需要猜测任何质量 capability 名称或 action 名称。
3. `batch_records.*` 已在 capability 合同中稳定存在，供批记录工作包直接接线。

## 现状缺口

- 质量子管理员当前仍只有壳层访问，缺少真实动作授权。
- 多个质量域路由仍由 `AdminOnly` 保护，和 PRD 的“质量部子管理员可执行”目标冲突。
- 质量 capability 虽已出现，但投诉/CAPA/内审/管评等资源仍为空 action，需要明确是否保持空集或补齐最小动作。

## 实施要求

### 1. capability 冻结

- 后端 `PermissionSnapshot` 必须生成稳定的质量 capability 结构。
- capability 计算逻辑只允许一处定义，不允许路由层重新拼接第二套权限语义。

### 2. API 鉴权收敛

- 文控、培训、变更、设备、计量、维保、投诉、CAPA、内审、管评、质量审计 API 必须统一走 capability 校验。
- 允许保留“参与人可见”的业务判断，但不能替代 capability 作为主授权入口。
- 禁止继续新增 `AdminOnly` 作为质量域的默认门。

### 3. fail-fast

- capability 缺失时直接拒绝，不做角色名 fallback。
- 不引入“如果没有质量 capability 就默认为 admin/sub_admin 可过”的兼容分支。

## 验收标准

- `auth/me` 对质量子管理员返回真实质量域 action，而不只是 `quality_system.view`
- 非 `admin` 用户在具备对应 capability 时可操作被授权质量 API
- 未授权用户访问质量 API 明确返回 `403`
- 相关测试覆盖成功、拒绝、快照输出三类路径

## 建议测试

```powershell
python -m pytest `
  backend/tests/test_auth_me_service_unit.py `
  backend/tests/test_document_control_api_unit.py `
  backend/tests/test_training_compliance_api_unit.py `
  backend/tests/test_change_control_api_unit.py `
  backend/tests/test_equipment_api_unit.py `
  backend/tests/test_metrology_api_unit.py `
  backend/tests/test_maintenance_api_unit.py -q
```

## 交付物

- 代码改动
- capability 合同摘要
- 被替换掉的 `AdminOnly` 路由清单
- 通过的后端测试命令与结果
