# Execution Log

- Task ID: `docs-tasks-iso-13485-20260413t153016-prd-md-iso--20260414T122156`
- Created: `2026-04-14T12:21:56`

## Phase Entries

Append one reviewed section per executor pass using real phase ids and real evidence refs.

## Phase P2

- Date: `2026-04-14`
- Objective: 质量系统前端入口与真实页面接线（/quality-system 子路由落到真实页面/工作区，并由 capability 守卫控制）

### Delivered

- 路由接线从“同一壳层页”改为“子路由直达真实页面/工作区”：
  - `/quality-system/doc-control` -> `DocumentControl`
  - `/quality-system/equipment` -> `QualitySystemEquipment`（并提供 `/quality-system/equipment/metrology`、`/quality-system/equipment/maintenance` 子路由）
  - `/quality-system/audit` -> `AuditLogs`
  - `/quality-system/training` -> `QualitySystemTraining`
  - `/quality-system/batch-records` -> `QualitySystemBatchRecords`（明确阻断说明，不伪装已接通）
  - `/quality-system/governance-closure` -> `QualitySystemGovernanceClosure`
- capability 守卫统一使用 `PermissionGuard` + capability 权限对象：
  - 质量系统导航项不再用 `allowedRoles` 硬编码隐藏，改为基于 `quality_system.view`
  - 模块入口与子路由 guard 采用 `quality_system.view` + 各模块资源的 `anyPermissions`
- 质量系统 Hub 页：
  - 移除“预留壳层/只供壳层进入”等文案与逻辑
  - 模块卡片按 capability 显隐（无权限则不展示）
- TrainingAckWorkspace：
  - `acknowledge` 行为不再默认允许，改为基于 `training_ack.acknowledge`

### Evidence

- Code paths:
  - `fronted/src/routes/routeRegistry.js`
  - `fronted/src/pages/QualitySystem.js`
  - `fronted/src/features/qualitySystem/moduleCatalog.js`
  - `fronted/src/features/qualitySystem/useQualitySystemPage.js`
  - `fronted/src/pages/QualitySystemTraining.js`
  - `fronted/src/pages/QualitySystemEquipment.js`
  - `fronted/src/pages/QualitySystemBatchRecords.js`
  - `fronted/src/pages/QualitySystemGovernanceClosure.js`
  - `fronted/src/features/qualitySystem/training/TrainingAckWorkspace.js`
- Unit tests (passed):
  - `fronted/src/pages/QualitySystem.test.js`
  - `fronted/src/routes/routeRegistry.test.js`
  - `fronted/src/pages/DocumentControl.test.js`
  - `fronted/src/pages/EquipmentLifecycle.test.js`
  - `fronted/src/pages/MaintenanceManagement.test.js`
  - `fronted/src/pages/MetrologyManagement.test.js`
  - `fronted/src/components/PermissionGuard.test.js`
  - Command:
    ```powershell
    Set-Location 'D:\ProjectPackage\RagflowAuth\fronted'
    $env:CI='true'
    npm test -- --watch=false --runInBand QualitySystem.test.js DocumentControl.test.js EquipmentLifecycle.test.js MaintenanceManagement.test.js MetrologyManagement.test.js PermissionGuard.test.js routeRegistry.test.js
    ```

## Phase P3

- Date: `2026-04-14`
- Objective: 文控单一受控根迁移到 `docs/compliance/`（同步运行时、校验器、种子、review package 与测试；禁止双根与 fallback）

### Delivered

- 文档主根迁移清单（收敛到单根）：
  - Moved `doc/compliance/*` -> `docs/compliance/*`，并删除空目录 `doc/compliance/`。
  - `docs/compliance/` 当前文件：
    - `change_control_sop.md`
    - `controlled_document_register.md`
    - `emergency_change_sop.md`
    - `emergency_change_status.md`
    - `environment_qualification_status.md`
    - `review_package_sop.md`
    - `srs.md`
    - `supplier_assessment.md`
    - `traceability_matrix.md`
    - `training_matrix.md`
    - `training_operator_qualification_status.md`
    - `urs.md`
    - `validation_plan.md`
    - `validation_report.md`
- 运行时 / 校验器 / 种子 / 测试引用统一到 `docs/compliance/*`：
  - `backend/services/document_control/compliance_root.py` 主根常量改为 `docs/compliance`。
  - `backend/services/compliance/*.py` 去除硬编码 `doc/compliance`，统一通过 `controlled_compliance_relpath(...)` 生成受控路径（不引入双根兼容逻辑）。
  - `backend/database/schema/training_compliance.py` 的 `training_material_ref` 种子锚点迁到 `docs/compliance/training_matrix.md#...`。
  - `backend/tests/test_*compliance*` 与 `backend/tests/test_training_compliance_api_unit.py` 更新 fixture 与断言，统一引用 `docs/compliance/*`。

### Evidence

- Repo gate scripts（全部 `passed: true`；external gap 为非阻断项）：
  - `python scripts/validate_fda03_repo_compliance.py --json`（external: `external_release_signoff_pending`）
  - `python scripts/validate_gbz02_repo_compliance.py --json`（external: `external_emergency_change_execution_pending`）
  - `python scripts/validate_gbz04_repo_compliance.py --json`（external: `external_supplier_qualification_records_pending`）
  - `python scripts/validate_gbz05_repo_compliance.py --json`（external: `external_training_qualification_records_pending`）
- Unit tests（passed）：
  - `python -m unittest backend.tests.test_compliance_review_package_api_unit backend.tests.test_training_compliance_api_unit`
  - `python -m unittest backend.tests.test_fda03_compliance_gate_unit backend.tests.test_gbz02_compliance_gate_unit backend.tests.test_gbz04_compliance_gate_unit backend.tests.test_gbz05_compliance_gate_unit`
- Old-root references cleared（无 fallback / 无双根兼容）：
  - `rg -n "doc/compliance" backend scripts ...` => no matches

## Outstanding Blockers

- None yet.
