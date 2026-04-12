# Test Plan

- Task ID: `docs-exec-plans-active-refactor-hotspots-consoli-20260411T175206`
- Created: `2026-04-11T17:52:06`
- Workspace: `D:\ProjectPackage\RagflowAuth`
- User Request: `按照 docs/exec-plans/active/refactor-hotspots-consolidation-2026-04.md 的方案进行重构。`

## Test Scope

- 验证文档树与验证入口说明一致性（P1）。
- 验证生产环境 JWT 默认密钥 fail-fast 行为与 token 策略文档（P2）。
- 验证 Operation Approval 责任拆分的行为不回归（P3）。
- 验证权限规则收敛到后端快照 + 前端统一适配层（P4）。

Out of scope:
- 业务功能大改或新增功能验收。
- `doc/` 与 `docs/` 的目录重命名迁移。

## Environment

- Python 3.x 可运行环境，已安装 `backend/requirements.txt`。
- Node.js 环境，已安装 `fronted` 依赖。
- 可访问 `data/auth.db`。
- 需要执行文档 E2E 时，具备 `scripts/run_doc_e2e.py` 所需真实依赖与账号。

## Accounts and Fixtures

- 若文档 E2E 或真实链路需要账号或外部服务，必须提供真实凭据。
- 缺少账号/服务时必须 fail-fast，并记录缺失项。

## Commands

1) 文档与验证入口一致性（必须）
- `python scripts\check_doc_e2e_docs.py --repo-root .`
  - Expected: 返回 0。
- `python scripts\run_doc_e2e.py --repo-root . --list`
  - Expected: 输出 manifest 列表且返回 0。
- `python scripts\run_doc_e2e.py --repo-root .`
  - Expected: 完整链路运行通过；若缺少真实依赖，必须 fail-fast 并报告缺失条件。

2) 后端单测（权限/认证/审批相关重点）
- `python -m pytest backend/tests -k "permission_resolver or permission_group or auth_request_token_fail_fast or operation_approval"`
  - Expected: 相关测试通过。

3) 前端测试（权限适配层与 auth 状态）
- `npm --prefix fronted test -- --watchAll=false`
  - Expected: 前端测试通过并退出 0。

## Test Cases

### T1: 文档树与验证入口一致性

- Covers: P1-AC1, P1-AC2
- Level: integration
- Command: `python scripts\check_doc_e2e_docs.py --repo-root .`
- Expected: 文档树约定与验证入口不冲突，命令返回 0。

### T2: 文档 E2E manifest 可执行

- Covers: P1-AC1
- Level: integration
- Command: `python scripts\run_doc_e2e.py --repo-root . --list`
- Expected: manifest 列表输出正常，命令返回 0。

### T3: JWT 默认密钥 fail-fast

- Covers: P2-AC1
- Level: unit
- Command: `python -m pytest backend/tests -k "auth_request_token_fail_fast or auth_password_security"`
- Expected: 当检测到默认 JWT secret 且处于生产配置时，测试断言服务拒绝启动并给出明确错误。

### T4: Token 策略文档落地

- Covers: P2-AC2
- Level: manual
- Command: `Get-Content SECURITY.md`
- Expected: 文档包含 token 存储策略、短期约束、中期替代方向与回滚策略。

### T5: Operation Approval 责任拆分回归

- Covers: P3-AC1, P3-AC2
- Level: unit
- Command: `python -m pytest backend/tests -k "operation_approval"`
- Expected: 相关审批流程测试通过。

### T6: 权限规则收敛回归

- Covers: P4-AC1, P4-AC2
- Level: unit
- Command: `python -m pytest backend/tests -k "permission_resolver"`
- Expected: 权限快照与规则应用测试通过。

### T7: 前端权限适配回归

- Covers: P4-AC1, P4-AC2
- Level: unit
- Command: `npm --prefix fronted test -- --watchAll=false`
- Expected: 前端测试通过，无权限判断相关回归。

## Coverage Matrix

| Case ID | Area | Scenario | Level | Acceptance IDs | Evidence |
| --- | --- | --- | --- | --- | --- |
| T1 | docs/validation | 文档树与验证入口一致性 | integration | P1-AC1, P1-AC2 | test-report.md#T1 |
| T2 | doc/e2e | manifest 列表可执行 | integration | P1-AC1 | test-report.md#T2 |
| T3 | backend/auth | JWT 默认密钥 fail-fast | unit | P2-AC1 | test-report.md#T3 |
| T4 | docs/security | token 策略文档 | manual | P2-AC2 | test-report.md#T4 |
| T5 | backend/operation_approval | 责任拆分回归 | unit | P3-AC1, P3-AC2 | test-report.md#T5 |
| T6 | backend/permission | 权限规则收敛回归 | unit | P4-AC1, P4-AC2 | test-report.md#T6 |
| T7 | fronted/auth | 前端权限适配回归 | unit | P4-AC1, P4-AC2 | test-report.md#T7 |

## Evaluator Independence

- Mode: blind-first-pass
- Validation surface: real-runtime
- Required tools: python, node, npm, pytest, playwright (仅在需要真实浏览器验证时)
- First-pass readable artifacts: prd.md, test-plan.md
- Withheld artifacts: execution-log.md, task-state.json
- Real environment expectation: 在真实仓库与运行环境执行。若涉及 UI/交互路径，必须使用真实浏览器并记录证据。
- Escalation rule: 未写初判前不得查看 withheld artifacts。

## Pass / Fail Criteria

- Pass when:
  - 所有测试用例执行通过，或明确声明缺失前提并 fail-fast 记录。
  - 所有 acceptance id 有对应测试证据。
- Fail when:
  - 任一关键命令失败且无明确缺失前提说明。
  - 发现新增 fallback 或静默降级。

## Regression Scope

- `backend/app/main.py`, `backend/app/dependencies.py` 注册与依赖装配。
- `backend/app/core/permission_resolver.py` 与权限相关测试。
- `backend/services/operation_approval/*` 与通知交互。
- `fronted/src/hooks/useAuth.js`、`fronted/src/components/PermissionGuard.js`。

## Reporting Notes

Write results to `test-report.md`.

The tester must remain independent from the executor and should prefer blind-first-pass unless the task explicitly needs full-context evaluation.
