# Test Report

- Task ID: `iso-13485-20260413T153016`
- Created: `2026-04-13T15:30:16`
- Workspace: `D:\ProjectPackage\RagflowAuth`
- User Request: `根据已识别的 ISO 13485 不符合项、会议纪要关于文控/设备/变更/批记录/体系文件入口的讨论，以及新增体系文件页签的设想，整理一份详尽的整改文档与验收工件`

## Environment Used

- Evaluation mode: blind-first-pass
- Validation surface: real-runtime
- Tools: PowerShell, python, rg, pytest
- Initial readable artifacts: prd.md, test-plan.md
- Initial withheld artifacts: execution-log.md, task-state.json
- Initial verdict before withheld inspection: yes

## Results

### T1: Repo Facts Match PRD

- Result: passed
- Covers: P1-AC1
- Command run: `rg -n "doc/compliance|REGISTER_RELATIVE_PATH|training_matrix\.md" backend/services/compliance backend/database/schema tobedeleted/compliance`; `Get-ChildItem -Name tobedeleted/compliance`; `rg -n "showInNav|PermissionGuard|NAVIGATION_ROUTES|quality_system" fronted/src/routes/routeRegistry.js fronted/src/components/layout/LayoutSidebar.js fronted/src/shared/auth/capabilities.js backend/app/core/permission_models.py`
- Environment proof: local repository runtime and file system inspection in `D:\ProjectPackage\RagflowAuth`
- Evidence refs: repository files and command outputs captured during this run
- Notes: PRD evidence anchors are all traceable in repository files.

### T2: Gap List Coverage

- Result: passed
- Covers: P1-AC2
- Command run: manual inspection of `docs/tasks/iso-13485-20260413T153016/prd.md` issue list section
- Environment proof: local markdown artifact inspection
- Evidence refs: `prd.md` sections “整改问题清单” and “仓库现状与证据”
- Notes: Coverage includes document control, design docs, training, entry governance, change, equipment, metrology, maintenance, batch records, audit, and complaint backlog.

### T3: Governance Hub Design

- Result: passed
- Covers: P1-AC3
- Command run: manual inspection of PRD governance section plus route and capability integration checks
- Environment proof: local code inspection
- Evidence refs: `fronted/src/routes/routeRegistry.js`, `fronted/src/components/layout/LayoutSidebar.js`, `fronted/src/shared/auth/capabilities.js`, `backend/app/core/permission_models.py`
- Notes: Entry model, user model, modules, and capability extension are coherent and implementable.

### T4: Executable Process Rules

- Result: passed
- Covers: P1-AC4
- Command run: manual inspection of `prd.md` “关键流程整改要求”
- Environment proof: local markdown artifact inspection
- Evidence refs: `prd.md` sections A-F
- Notes: Rules are explicit for upload/version linkage, review/approve/effective/obsolete, 15-minute training acknowledgement with question loop, KB publish, change ledger, equipment/metrology/maintenance, batch records, and audit traceability.

### T5: Priority and No-Fallback

- Result: passed
- Covers: P1-AC5
- Command run: manual inspection of PRD priority and blocking sections; runtime checks with `python scripts/validate_fda03_repo_compliance.py --json`; `python scripts/validate_gbz02_repo_compliance.py --json`; `python scripts/validate_gbz04_repo_compliance.py --json`; `python scripts/validate_gbz05_repo_compliance.py --json`
- Environment proof: local repository runtime
- Evidence refs: validator JSON outputs from current run
- Notes: All repository-scoped blocking issues for these gates now return `passed=true`; remaining issues are external evidence archival only.

### T6: Independent Reviewability

- Result: passed
- Covers: P1-AC6
- Command run: manual inspection of `docs/tasks/iso-13485-20260413T153016/test-plan.md`
- Environment proof: local markdown artifact inspection
- Evidence refs: `test-plan.md` command set, independence model, and pass/fail criteria
- Notes: Test plan supports independent verification without hidden context dependency.

### T7: 质量 capability 合同与 `auth/me` 快照稳定

- Result: passed
- Covers: P2-AC1, P2-AC2
- Command run: `python -m pytest backend/tests/test_auth_me_service_unit.py -q`
- Environment proof: local pytest run in `D:\ProjectPackage\RagflowAuth`
- Evidence refs: `backend/app/core/permission_models.py`; `fronted/src/shared/auth/capabilities.js`; `backend/tests/test_auth_me_service_unit.py`
- Notes: Contract constants are aligned and the unit test asserts non-admin (sub_admin) receives real quality actions in `auth/me`.

### T8: 未授权访问质量域 API 明确拒绝（403）

- Result: passed
- Covers: P2-AC3, P3-AC2
- Command run: `python -m pytest backend/tests/test_equipment_api_unit.py backend/tests/test_governance_closure_api_unit.py backend/tests/test_audit_evidence_export_api_unit.py backend/tests/test_compliance_review_package_api_unit.py -q`
- Environment proof: local pytest run in `D:\ProjectPackage\RagflowAuth`
- Evidence refs: pytest assertions for `*_forbidden` detail codes in updated unit tests
- Notes: Denial paths return explicit `403` with capability-oriented detail codes; no `admin_required` fallback is used for quality-domain APIs.

### T9: 非 admin（质量子管理员）可基于 capability 执行质量域动作

- Result: passed
- Covers: P3-AC2
- Command run: `python -m pytest backend/tests/test_equipment_api_unit.py backend/tests/test_document_control_api_unit.py backend/tests/test_change_control_api_unit.py -q`
- Environment proof: local pytest run in `D:\ProjectPackage\RagflowAuth`
- Evidence refs: `backend/tests/test_equipment_api_unit.py` sub_admin workflow case; updated router capability checks
- Notes: Non-admin (sub_admin) can call quality-domain write APIs when capabilities are present; unauthorized paths remain 403.

### T10: 建议质量域回归命令全量通过

- Result: passed
- Covers: P3-AC1, P3-AC3
- Command run: `python -m pytest backend/tests/test_auth_me_service_unit.py backend/tests/test_document_control_api_unit.py backend/tests/test_training_compliance_api_unit.py backend/tests/test_change_control_api_unit.py backend/tests/test_equipment_api_unit.py backend/tests/test_metrology_api_unit.py backend/tests/test_maintenance_api_unit.py backend/tests/test_audit_events_api_unit.py backend/tests/test_audit_evidence_export_api_unit.py backend/tests/test_compliance_review_package_api_unit.py backend/tests/test_governance_closure_api_unit.py -q`
- Environment proof: local pytest run in `D:\ProjectPackage\RagflowAuth`
- Evidence refs: pytest output for this run (all cases passed) + updated router/authz code paths
- Notes: Quality-domain routers now use capability checks as the primary gate, and targeted regression tests pass in this run.

### T11: 批记录后端闭环通过单测

- Result: passed
- Covers: P4-AC1, P4-AC2, P4-AC3, P4-AC4
- Command run: `python -m pytest backend/tests/test_batch_records_api_unit.py -q`
- Environment proof: local pytest run in `D:\ProjectPackage\RagflowAuth`
- Evidence refs: `backend/app/modules/batch_records/router.py`; `backend/services/batch_records/service.py`; `backend/tests/test_batch_records_api_unit.py`
- Notes: 覆盖模板创建/发布、执行创建、步骤写入、签名、复核、导出与 403 拒绝路径，并验证关键动作写入审计日志。

### T12: 批记录前端工作区通过目标 Jest 测试

- Result: passed
- Covers: P5-AC1, P5-AC2, P5-AC3
- Command run: `Set-Location 'D:\ProjectPackage\RagflowAuth\fronted'; $env:CI='true'; npm test -- --watch=false --runInBand src/pages/QualitySystemBatchRecords.test.js`
- Environment proof: local React/Jest run in `D:\ProjectPackage\RagflowAuth\fronted`
- Evidence refs: `fronted/src/features/batchRecords/BatchRecordsWorkspace.js`; `fronted/src/pages/QualitySystemBatchRecords.js`; `fronted/src/pages/QualitySystemBatchRecords.test.js`
- Notes: 覆盖模板/执行列表渲染、步骤写入交互，以及通过电子签名 challenge 发起签名的主路径。

### T13: 质量体系批记录入口浏览器路径通过

- Result: passed
- Covers: P5-AC4
- Command run: `Set-Location 'D:\ProjectPackage\RagflowAuth\fronted'; npx playwright test --config=playwright.docs.config.js docs.quality-system.batch-records.spec.js --workers=1`
- Environment proof: local Playwright run with dedicated docs config and isolated doc e2e bootstrap
- Evidence refs: `fronted/e2e/tests/docs.quality-system.batch-records.spec.js`
- Notes: 真实浏览器下验证 `/quality-system/batch-records` 页面可访问，且模板与执行列表请求返回成功；同时验证无质量权限账号会被重定向到 `/unauthorized`。

## Final Verdict

- Outcome: passed
- Verified acceptance ids: P1-AC1, P1-AC2, P1-AC3, P1-AC4, P1-AC5, P1-AC6, P2-AC1, P2-AC2, P2-AC3, P3-AC1, P3-AC2, P3-AC3, P4-AC1, P4-AC2, P4-AC3, P4-AC4, P5-AC1, P5-AC2, P5-AC3, P5-AC4
- Blocking prerequisites:
- Summary: P1-P3 质量权限与鉴权整改保持通过状态。P4 已补齐批记录后端模型、API、电子签名复用与审计留痕；P5 已补齐 `/quality-system/batch-records` 前端工作区，并通过目标 Jest 与 Playwright 验证。

## Open Issues

- Offline evidence archival remains pending per validator external_gaps (outside this repository task scope).
