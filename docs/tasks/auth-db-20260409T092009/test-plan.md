# Test Plan

- Task ID: `auth-db-20260409T092009`
- Created: `2026-04-09T09:20:09`
- Workspace: `D:\ProjectPackage\RagflowAuth`
- User Request: `为数据安全页面实现真实恢复功能，允许用备份包真实覆盖当前 auth.db，并提供前端危险确认入口与测试`

## Test Scope

验证真实恢复功能是否会真实覆盖 live `auth.db`，并验证前端是否把危险操作与“恢复演练”分开、是否要求恢复原因和显式确认。已有恢复演练仅校验路径继续保留，但不是本轮测试重点。

## Environment

- OS: Windows 开发环境，工作区位于 `D:\ProjectPackage\RagflowAuth`
- Backend tests: Python unittest / FastAPI TestClient
- Frontend tests: Jest + Testing Library
- 数据安全测试会在临时目录创建独立 `auth.db` 与备份包，不依赖线上数据库
- 若本地缺少 Python、npm 或测试依赖，测试必须 fail fast 并记录

## Accounts and Fixtures

- 后端测试使用测试用户 `u1`，角色为 admin
- 训练合规通过 `qualify_user_for_action(..., action_code=\"restore_drill_execute\")` 注入
- 备份包 fixture 至少包含 `auth.db` 和 `backup_settings.json`
- 前端测试使用 mocked `dataSecurityApi`

## Commands

- `python -m unittest backend.tests.test_backup_restore_audit_unit`
  - 期望：真实恢复相关后端用例通过
- `CI=true npm test -- --runInBand --runTestsByPath src/pages/DataSecurity.test.js src/features/dataSecurity/useDataSecurityPage.test.js`
  - 期望：数据安全页面与 Hook 相关前端用例通过
- `python C:\Users\BJB110\.codex\skills\spec-driven-delivery\scripts\validate_artifacts.py --cwd D:\ProjectPackage\RagflowAuth --task-id auth-db-20260409T092009`
  - 期望：工件结构校验通过
- `python C:\Users\BJB110\.codex\skills\spec-driven-delivery\scripts\validate_test_report.py --cwd D:\ProjectPackage\RagflowAuth --task-id auth-db-20260409T092009`
  - 期望：测试报告结构校验通过

## Test Cases

### T1: 真实恢复成功覆盖 live auth.db

- Covers: P1-AC1, P1-AC2, P1-AC3, P1-AC5
- Level: backend integration/unit
- Command: `python -m unittest backend.tests.test_backup_restore_audit_unit`
- Expected: 创建匹配备份任务后调用真实恢复 API 成功，live `auth.db` 内容被覆盖且源/目标 SQLite 逻辑内容签名一致，同时生成审计事件

### T2: 真实恢复拒绝非法前提

- Covers: P1-AC2, P1-AC4
- Level: backend integration/unit
- Command: `python -m unittest backend.tests.test_backup_restore_audit_unit`
- Expected: 路径或哈希不匹配、确认字样无效、变更原因为空、存在运行中备份任务时均被拒绝

### T3: 页面展示独立危险恢复入口

- Covers: P2-AC1
- Level: frontend component/page
- Command: `CI=true npm test -- --runInBand --runTestsByPath src/pages/DataSecurity.test.js src/features/dataSecurity/useDataSecurityPage.test.js`
- Expected: 页面同时显示“恢复演练（仅校验）”与独立真实恢复按钮/危险提示

### T4: 前端真实恢复确认链路

- Covers: P2-AC2, P2-AC3, P2-AC4
- Level: frontend page/hook
- Command: `CI=true npm test -- --runInBand --runTestsByPath src/pages/DataSecurity.test.js src/features/dataSecurity/useDataSecurityPage.test.js`
- Expected: prompt 按顺序采集恢复原因与 `RESTORE`，取消时不调用 API，成功时 payload 完整

### T5: 任务工件与证据闭环

- Covers: P3-AC1, P3-AC2, P3-AC3
- Level: workflow validation
- Command: `validate_artifacts.py`, `validate_test_report.py`, `check_completion.py`
- Expected: 工件结构、测试报告结构和完成态检查通过

## Coverage Matrix

| Case ID | Area | Scenario | Level | Acceptance IDs | Evidence |
| --- | --- | --- | --- | --- | --- |
| T1 | backend restore API | 匹配备份包真实覆盖 live auth.db | integration/unit | P1-AC1, P1-AC2, P1-AC3, P1-AC5 | `execution-log.md`, `test-report.md` |
| T2 | backend restore API | 非法输入和运行中备份时拒绝恢复 | integration/unit | P1-AC2, P1-AC4 | `execution-log.md`, `test-report.md` |
| T3 | data security page | UI 明确区分恢复演练与真实恢复 | component/page | P2-AC1 | `execution-log.md`, `test-report.md` |
| T4 | data security page | prompt 确认链路与 API payload | component/page | P2-AC2, P2-AC3, P2-AC4 | `execution-log.md`, `test-report.md` |
| T5 | workflow artifacts | 工件和状态证据闭环 | workflow | P3-AC1, P3-AC2, P3-AC3 | `execution-log.md`, `test-report.md`, `task-state.json` |

## Evaluator Independence

- Mode: blind-first-pass
- Validation surface: real-runtime
- Required tools: python, unittest, npm, jest
- First-pass readable artifacts: prd.md, test-plan.md
- Withheld artifacts: execution-log.md, task-state.json
- Real environment expectation: 在当前真实仓库与测试运行时执行，不依赖 mock 结果作为最终交付证据；前端用 mocked API 做单测，但命令和报告必须基于真实测试运行。
- Escalation rule: 在首轮测试 verdict 形成前，不读取 `execution-log.md` 与 `task-state.json` 作为判定依据。

## Pass / Fail Criteria

- Pass when:
  - 后端测试证明真实恢复成功会覆盖 live `auth.db`
  - 后端测试证明非法前提会明确拒绝
  - 前端测试证明危险入口、prompt 链路与 payload 正确
  - 工件校验脚本通过
- Fail when:
  - 真实恢复仍只是拷贝到演练目录
  - 前端没有显式危险确认
  - 任一 acceptance id 缺少测试覆盖或证据
  - 任一目标测试命令失败

## Regression Scope

- 现有恢复演练 API 与页面展示
- 数据安全备份任务列表与 restore eligible 选择逻辑
- 数据安全设置保存逻辑
- 审计日志记录结构

## Reporting Notes

测试结果写入 `test-report.md`。如果某个命令未执行或被环境阻塞，必须写明阻塞前提和影响，不允许把未执行测试记为通过。
