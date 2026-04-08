# Test Plan

- Task ID: `data-security-20260408T013422`
- Created: `2026-04-08T01:34:22`
- Workspace: `D:\ProjectPackage\RagflowAuth`
- User Request: `继续推进系统重构，完成 data_security 模块前后端第一期局部重构，保持现有行为与接口稳定`

## Test Scope

验证数据安全模块后端 store 内部分层、锁语义收紧、设置策略抽离，以及前端页面/Hook 拆分后，数据安全 API 契约、备份/恢复演练核心行为和现有页面交互保持稳定。

本次明确不在测试范围：

- 通知中心重构
- 权限模型重构
- 文档预览重构
- 非数据安全模块页面行为

## Environment

- Windows PowerShell
- Python 3.12
- 仓库根目录：`D:\ProjectPackage\RagflowAuth`
- 前端目录：`D:\ProjectPackage\RagflowAuth\fronted`
- 后端测试依赖已安装
- 前端 `react-scripts test` 可运行
- 若进行真实浏览器验证，需要本地可启动前端应用

## Accounts and Fixtures

- 后端数据安全测试使用现有临时 SQLite、mock store、临时目录夹具
- 前端测试使用现有 `dataSecurityApi` mock
- 真实浏览器验证基于本地前端运行实例，不额外引入 mock 页面

如果上述夹具或运行实例不可用，测试必须失败并记录缺失前提。

## Commands

1. `python -m pytest backend/tests/test_data_security_runner_stale_lock.py backend/tests/test_data_security_store_lock_unit.py backend/tests/test_data_security_cancel_unit.py backend/tests/test_config_change_log_unit.py`
   - 期望：锁语义、取消流程和配置变更日志回归通过
2. `python -m pytest backend/tests/test_data_security_router_unit.py backend/tests/test_data_security_scheduler_v2_unit.py backend/tests/test_data_security_models_unit.py backend/tests/test_data_security_backup_steps_unit.py backend/tests/test_data_security_path_mapping.py`
   - 期望：数据安全核心后端回归通过
3. `python -m pytest backend/tests/test_backup_restore_audit_unit.py backend/tests/test_audit_evidence_export_api_unit.py backend/tests/test_data_security_image_backup_fallback.py backend/tests/test_data_security_run_cmd_live_eof.py`
   - 期望：恢复演练、审计导出和邻近数据安全回归通过
4. `$env:CI='true'; npm test -- --runInBand --watchAll=false src/features/dataSecurity/api.test.js src/features/dataSecurity/useDataSecurityPage.test.js src/pages/DataSecurity.test.js`
   - 期望：前端 API、Hook、页面回归通过
5. `启动前端与后端应用后，使用 Playwright 登录并打开 /data-security?advanced=1 页面，验证关键分区与交互入口，并记录截图证据`
   - 期望：数据安全页面在真实浏览器中正常渲染
6. `python C:/Users/BJB110/.codex/skills/spec-driven-delivery/scripts/check_completion.py --cwd D:/ProjectPackage/RagflowAuth --tasks-root docs/tasks --task-id data-security-20260408T013422 --apply`
   - 期望：任务完成检查通过

## Test Cases

### T1: 数据安全后端 facade 与仓储回归

- Covers: P1-AC1, P1-AC2, P1-AC3
- Level: unit/integration
- Command: `python -m pytest backend/tests/test_data_security_runner_stale_lock.py backend/tests/test_data_security_store_lock_unit.py backend/tests/test_data_security_cancel_unit.py backend/tests/test_config_change_log_unit.py`，以及 `python -m pytest backend/tests/test_data_security_router_unit.py backend/tests/test_data_security_scheduler_v2_unit.py backend/tests/test_data_security_models_unit.py backend/tests/test_data_security_backup_steps_unit.py backend/tests/test_data_security_path_mapping.py`
- Expected: `DataSecurityStore` 调用链继续可用，设置读取/更新、锁释放、调度器查询、路由辅助逻辑回归通过。

### T2: 数据安全恢复演练与审计联动回归

- Covers: P1-AC3
- Level: integration
- Command: `python -m pytest backend/tests/test_backup_restore_audit_unit.py backend/tests/test_audit_evidence_export_api_unit.py backend/tests/test_data_security_image_backup_fallback.py backend/tests/test_data_security_run_cmd_live_eof.py`
- Expected: 恢复演练持久化、备份审计导出和邻近数据安全行为保持通过。

### T3: 数据安全前端 Hook 与页面回归

- Covers: P2-AC1, P2-AC2, P2-AC3
- Level: component/unit
- Command: `$env:CI='true'; npm test -- --runInBand --watchAll=false src/features/dataSecurity/api.test.js src/features/dataSecurity/useDataSecurityPage.test.js src/pages/DataSecurity.test.js`
- Expected: 设置保存、备份记录展示、恢复演练提交和高级设置交互保持通过。

### T4: 数据安全页面真实浏览器回归

- Covers: P2-AC2, P2-AC3, P3-AC1
- Level: e2e
- Command: `启动前端与后端应用后，使用 Playwright 以 admin/admin123 登录，打开 /data-security?advanced=1 页面，验证备份记录区域、恢复演练区域和高级设置入口仍可渲染与交互，并记录截图证据。`
- Expected: 页面在真实浏览器中可打开，关键分区与交互入口存在，无明显渲染或脚本错误。

### T5: 任务证据一致性检查

- Covers: P3-AC1, P3-AC2, P3-AC3
- Level: manual/tooling
- Command: `人工核对 execution-log.md / test-report.md / task-state.json，并运行 check_completion.py`
- Expected: 三份工件与阶段状态一致，完成检查通过。

## Coverage Matrix

| Case ID | Area | Scenario | Level | Acceptance IDs | Evidence |
| --- | --- | --- | --- | --- | --- |
| T1 | 后端数据安全 | facade、settings policy、repositories、锁语义回归 | unit/integration | P1-AC1, P1-AC2, P1-AC3 | `test-report.md` |
| T2 | 后端数据安全联动 | 恢复演练与审计导出链路回归 | integration | P1-AC3 | `test-report.md` |
| T3 | 前端数据安全 | Hook/页面拆分后的行为回归 | component/unit | P2-AC1, P2-AC2, P2-AC3 | `test-report.md` |
| T4 | 前端数据安全 | 真实浏览器下页面分区与关键入口回归 | e2e/manual | P2-AC2, P2-AC3, P3-AC1 | `test-report.md` |
| T5 | 任务工件 | 阶段状态与证据一致性 | manual/tooling | P3-AC1, P3-AC2, P3-AC3 | `execution-log.md`, `test-report.md`, `task-state.json` |

## Evaluator Independence

- Mode: blind-first-pass
- Validation surface: real-browser
- Required tools: pytest, react-scripts test, playwright
- First-pass readable artifacts: prd.md, test-plan.md
- Withheld artifacts: execution-log.md, task-state.json
- Real environment expectation: 在真实仓库中运行后端 pytest、前端 Jest，并在可启动的前端应用上使用 Playwright 做一次真实浏览器验证，记录截图或等效证据。
- Escalation rule: 在初次结论产出前，不查看 execution-log.md 和 task-state.json。

## Pass / Fail Criteria

- Pass when:
  - T1、T2、T3 命令全部通过
  - T4 浏览器检查通过并有证据
  - T5 检查无冲突
  - 没有引入 fallback、mock、静默降级路径
- Fail when:
  - 任一命令失败
  - 数据安全 API 契约、`DataSecurityStore` 公开接口或前端关键交互发生回归
  - 任务工件与实际执行结果不一致

## Regression Scope

- 数据安全后端路由层
- 运行器与调度器对 `DataSecurityStore` 的调用链
- 备份/恢复演练相关审计导出链路
- 前端数据安全页面与 Hook

## Reporting Notes

将命令、结果、失败信息和最终结论写入 `test-report.md`。
