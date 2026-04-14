# ISO 13485 体系文件治理实现测试计划

- Task ID: `docs-tasks-iso-13485-20260413t153016-prd-md-iso--20260414T122156`
- Created: `2026-04-14T12:21:56`
- Workspace: `D:\ProjectPackage\RagflowAuth`
- User Request: `基于 docs/tasks/iso-13485-20260413T153016/prd.md 中识别出的差距，完善当前系统中未满足的 ISO 13485 体系文件治理需求，重点补齐质量权限模型、质量系统前端接线、文控单一受控根迁移与批记录模块实现，并提供可独立复核的测试工件`

## Test Scope

本测试计划验证以下实现结果，而不是只验证文档描述：

- 质量 capability 是否真正下发到 `auth/me` 并在后端 API 生效。
- `/quality-system` 子路由是否进入真实页面，而不是停留在保留壳层。
- 文控受控主根是否从 `doc/compliance` 收敛到 `docs/compliance`，且相关校验器和测试同步通过。
- `batch_records` 是否具备真实后端闭环、前端工作区、签名/审计集成与浏览器验证路径。

以下内容不在本轮测试范围：

- 与本次差距无直接关系的其它合规域重构。
- 线上环境发布验证。
- 仓库外纸质签核或线下归档证据本身的真实性审计。

## Environment

- 平台：Windows / PowerShell
- 仓库根目录：`D:\ProjectPackage\RagflowAuth`
- 后端测试解释器：`python`
- 前端目录：`D:\ProjectPackage\RagflowAuth\fronted`
- 浏览器验证工具：`npx playwright`
- 前端依赖：`fronted/node_modules`
- 真实运行环境要求：
  - 后端 API 可本地启动
  - 前端可本地启动
  - 浏览器可访问质量系统页面

如果上述任一条件缺失，测试必须标记为 `blocked`，不得以静态代码阅读替代真实验证。

## Accounts and Fixtures

- `admin` 账号：用于验证全域质量管理能力。
- `sub_admin` 账号：必须绑定质量 capability，且不依赖全局 `admin`。
- 普通执行账号：用于验证培训确认、批记录执行、权限拒绝路径。
- 数据夹具至少应包含：
  - 一条可查看的受控文档/修订记录
  - 一条可操作的变更请求
  - 一条设备/计量/维保样例
  - 一条可生成培训确认的有效修订
  - 批记录模板与执行实例样例

若账号或夹具不存在，tester 必须在 `test-report.md` 明确记录缺失项并停止相关用例。

## Commands

所有命令从仓库根目录执行，除非特别说明。

```powershell
Set-Location 'D:\ProjectPackage\RagflowAuth'
```

### 后端单测

```powershell
python -m unittest `
  backend.tests.test_auth_me_service_unit `
  backend.tests.test_document_control_api_unit `
  backend.tests.test_training_compliance_api_unit `
  backend.tests.test_change_control_api_unit `
  backend.tests.test_equipment_api_unit `
  backend.tests.test_metrology_api_unit `
  backend.tests.test_maintenance_api_unit `
  backend.tests.test_governance_closure_api_unit `
  backend.tests.test_batch_records_api_unit
```

预期：全部通过；其中必须覆盖质量 capability、非 admin 质量授权、批记录 API。

### 合规校验脚本

```powershell
python scripts/validate_fda03_repo_compliance.py --json
python scripts/validate_gbz02_repo_compliance.py --json
python scripts/validate_gbz04_repo_compliance.py --json
python scripts/validate_gbz05_repo_compliance.py --json
```

预期：`passed` 为 `true`，且引用路径以 `docs/compliance/*` 为准。

### 前端单测

```powershell
Set-Location 'D:\ProjectPackage\RagflowAuth\fronted'
$env:CI='true'
npm test -- --watch=false --runInBand QualitySystem.test.js DocumentControl.test.js EquipmentLifecycle.test.js MaintenanceManagement.test.js MetrologyManagement.test.js PermissionGuard.test.js
```

预期：质量系统入口、真实页面接线、守卫行为相关测试通过。

如批记录前端新增独立测试文件，应在同一命令中补入该文件名或等效 pattern。

### 浏览器验证

```powershell
Set-Location 'D:\ProjectPackage\RagflowAuth\fronted'
npx playwright test e2e/tests/docs.quality-system.spec.js --workers=1
```

预期：真实浏览器中至少验证：

- `sub_admin` 可进入被授权的质量系统模块
- 未授权场景被正确拒绝
- 批记录工作区可完成至少一条关键正向路径
- 生成 screenshot、video、trace、HAR 等至少一种证据文件

## Test Cases

### T1: 质量 capability 在 `auth/me` 与后端 API 同步生效

- Covers: P1-AC1, P1-AC2, P1-AC3, P1-AC4
- Level: unit + API
- Command: 运行“后端单测”命令
- Expected: 后端单测全部通过，且覆盖 `auth/me` capability 快照、非 `admin` 授权成功与未授权 `403` 拒绝路径。

### T2: 质量系统子路由进入真实页面

- Covers: P2-AC1, P2-AC2, P2-AC3, P2-AC4
- Level: frontend unit
- Command: 运行“前端单测”命令
- Expected: 前端单测全部通过，且覆盖质量系统子路由落点、预留壳层清除与 capability 守卫行为。

### T3: 文控受控根迁移后的仓库内一致性

- Covers: P3-AC1, P3-AC2, P3-AC3, P3-AC4
- Level: repo inspection + unit + script
- Command: 运行“合规校验脚本”命令，并补充执行 `rg -n "doc/compliance|docs/compliance|controlled_compliance_relpath" backend scripts` 作为仓库内引用清零检查。
- Expected: 合规校验脚本通过，且运行时代码/校验器/种子/测试统一引用 `docs/compliance`，仓库内不存在新的双根兼容逻辑。

### T4: 批记录后端闭环可用

- Covers: P4-AC1, P4-AC2, P4-AC3, P4-AC4
- Level: API + unit
- Command: 运行“后端单测”命令
- Expected: 后端单测全部通过，且覆盖批记录模板/执行/签名/复核/导出 API、签名复用与审计/拒绝路径。

### T5: 批记录前端与真实浏览器路径可复核

- Covers: P5-AC1, P5-AC2, P5-AC3, P5-AC4
- Level: e2e
- Command: 运行“前端单测”命令与“浏览器验证”命令
- Expected: `/quality-system/batch-records` 存在真实工作区且守卫按 capability 生效，并且 Playwright 产生至少一种真实浏览器证据文件。

## Coverage Matrix

| Case ID | Area | Scenario | Level | Acceptance IDs | Evidence |
| --- | --- | --- | --- | --- | --- |
| T1 | 质量权限 | capability 快照与 API 鉴权一致 | unit + API | P1-AC1, P1-AC2, P1-AC3, P1-AC4 | `test-report.md` |
| T2 | 质量系统前端 | 子路由进入真实页面并受 capability 控制 | frontend unit | P2-AC1, P2-AC2, P2-AC3, P2-AC4 | `test-report.md` |
| T3 | 文控主根迁移 | 运行时、校验器、种子与测试统一引用 `docs/compliance` | repo inspection + unit + script | P3-AC1, P3-AC2, P3-AC3, P3-AC4 | `test-report.md` |
| T4 | 批记录后端 | 模板/执行/签名/复核/导出闭环 | API + unit | P4-AC1, P4-AC2, P4-AC3, P4-AC4 | `test-report.md` |
| T5 | 批记录前端 | 质量系统入口与真实浏览器交互 | frontend unit + e2e | P5-AC1, P5-AC2, P5-AC3, P5-AC4 | `test-report.md` |

## Evaluator Independence

- Mode: blind-first-pass
- Validation surface: real-browser
- Required tools: python, rg, npm, playwright
- First-pass readable artifacts: prd.md, test-plan.md
- Withheld artifacts: execution-log.md, task-state.json
- Real environment expectation: tester 必须基于真实仓库状态、真实后端/前端运行环境和真实浏览器执行验证，不得只看代码或只看 executor 说明。
- Escalation rule: tester 在写出首轮结论前不得查看 `execution-log.md` 与 `task-state.json`；只有首轮结论落入 `test-report.md` 后，主代理才可要求做差异分析。

## Pass / Fail Criteria

- Pass when:
  - T1 至 T5 全部通过
  - 所有 acceptance id 均被至少一个测试用例覆盖并在 `test-report.md` 中有结果
  - 浏览器验证生成真实证据文件
  - 未出现依赖旧根 `doc/compliance` 的运行时或校验器残留
- Fail when:
  - 质量 capability 仍只停留在前端声明层，未在 `auth/me` 或后端 API 生效
  - `/quality-system` 任一目标子模块仍回到预留壳层
  - 运行时代码或校验器继续依赖 `doc/compliance`
  - `batch_records` 缺少真实 API、前端工作区、签名复用或审计留痕
  - 浏览器验证没有真实证据文件
- Blocked when:
  - 必需工具、运行环境、账号或夹具缺失

## Regression Scope

- `auth/me` 载荷结构及登录后权限消费链路
- `PermissionGuard`、`useAuth`、路由守卫和导航渲染
- 文控、培训、变更、设备、计量、维保、治理闭环现有 API
- 合规校验脚本与 review package 导出
- 电子签名、审批、审计导出相关共用能力

## Reporting Notes

- 所有结果写入 `test-report.md`。
- tester 必须记录：
  - 执行环境
  - 每个测试用例的结果
  - 对应证据文件或命令结果
  - 最终 `pass/fail/blocked` 结论
- 如发现 PRD 与仓库实现不一致，必须把差异点逐条写出，不得用“基本符合”替代。
