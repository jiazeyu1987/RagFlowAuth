# 测试计划：ISO 13485 整改文档包

- Task ID: `iso-13485-20260413T153016`
- Created: `2026-04-13T15:30:16`
- Workspace: `D:\ProjectPackage\RagflowAuth`
- User Request: `根据已识别的 ISO 13485 不符合项、会议纪要关于文控/设备/变更/批记录/体系文件入口的讨论，以及新增体系文件页签的设想，整理一份详尽的整改文档与验收工件`

## Test Scope

本测试计划验证以下交付：

- P1：ISO 13485 整改文档包（`prd.md` / `test-plan.md` 的完整性、真实性、可执行性）。
- P2-P3：质量 capability 合同冻结与后端 API 鉴权收敛（以 capability 为主授权入口，fail-fast 403，无角色名 fallback），并用后端单测验证。
- P4：批记录后端闭环（模板/执行/步骤写入/签名/复核/导出 + 审计留痕），并用后端单测验证。
- P5：批记录前端工作区与浏览器验证（Jest + Playwright 证据）。

本轮测试应覆盖：

- `prd.md` 是否基于当前仓库真实证据，而不是泛化描述。
- `prd.md` 是否完整覆盖会议纪要中提到的核心整改事项。
- `prd.md` 是否对`体系文件`治理中枢给出可落地的页面、权限和流程设计。
- `prd.md` 是否明确了优先级、路线图、阻断条件和禁止 fallback 的原则。
- `test-plan.md` 是否能让独立评审人复现实锤证据并给出通过/不通过结论。
- 质量 capability 合同（资源集合与 action 集）在前后端常量中一致，且 `auth/me` capability 快照结构稳定可消费。
- 质量域相关 API 鉴权不再依赖 `AdminOnly` 作为默认门，而是统一走 capability 校验，并且未授权返回明确 `403`。
- 批记录后端能力（模板/执行/步骤/签名/复核/导出）具备最小闭环与明确的拒绝语义，并写入审计日志。
- 批记录前端入口受 capability 守卫，Jest 覆盖主要交互，并通过 Playwright 浏览器验证产生证据。

以下内容不在本轮范围内：

- 实际新增 `体系文件` 页面。
- 实际迁移受控文件到新主根。
- 实现设备、变更、计量、维护、投诉、内审、管理评审等业务域的完整能力与页面交互闭环（本轮仍只验证其 capability 合同与 API 鉴权收敛）。

## Environment

- 平台：Windows / PowerShell。
- 仓库根目录：`D:\ProjectPackage\RagflowAuth`。
- 依赖工具：
  - `rg`
  - `python`
  - `python -m pytest`
  - `node` / `npm`
  - `playwright`（通过 `npx playwright`）
- 说明：
  - 若 `rg` 不可用，评审人必须记录缺失前提并判定为 `blocked`。
  - 若需执行合规校验基线命令而 `python` 不可用，也必须记录缺失前提并判定为 `blocked`。
  - 若需验证 P5（Jest / Playwright）而 `node`/`npm` 或 `playwright` 不可用，评审人必须记录缺失前提并判定为 `blocked`（不得以跳过代替通过）。

## Accounts and Fixtures

本轮评审不需要登录账号，也不依赖运行中的前后端服务。

本轮仅需要：

- 当前仓库代码和文档可读。
- 会议纪要中已确认的业务范围可作为评审输入。

如需评审后续实施阶段，则另行准备质量部子管理员账号、测试设备台账、测试文件和测试批记录数据；这些不属于本轮前提。

## Commands

所有命令从仓库根目录执行：

```powershell
Set-Location 'D:\ProjectPackage\RagflowAuth'
```

### 1. 核对文控主根断裂事实

```powershell
rg -n "doc/compliance|REGISTER_RELATIVE_PATH|training_matrix\.md" backend/services/compliance backend/database/schema tobedeleted/compliance
```

期望：

- 能看到 `review_package.py`、合规校验器、培训 schema 中对 `doc/compliance/*` 的真实引用。
- 能看到 `tobedeleted/compliance/controlled_document_register.md` 中仍记录了 `doc/compliance/*` 路径。

### 2. 核对现有合规材料位置

```powershell
Get-ChildItem -Force tobedeleted\compliance | Select-Object Name
```

期望：

- 可看到 `urs.md`、`srs.md`、`traceability_matrix.md`、`validation_plan.md`、`validation_report.md`、`training_matrix.md`、`supplier_assessment.md`、`environment_qualification_status.md` 等文件。

### 3. 核对当前导航接入方式

```powershell
Get-Content -Raw fronted\src\routes\routeRegistry.js
Get-Content -Raw fronted\src\components\layout\LayoutSidebar.js
```

期望：

- `routeRegistry.js` 使用 `showInNav` 定义导航项。
- `LayoutSidebar.js` 通过 `NAVIGATION_ROUTES` 和 `PermissionGuard` 渲染与控权。

### 4. 核对当前权限模型边界

```powershell
Get-Content -Raw fronted\src\shared\auth\capabilities.js
Get-Content -Raw backend\app\core\permission_models.py
```

期望：

- capability 覆盖知识库、工具、聊天、用户管理等资源，并已扩展质量域资源（`quality_system`、`document_control`、`training_ack`、`change_control`、`equipment_lifecycle`、`metrology`、`maintenance`、`audit_events` 等）。
- 前后端 `QUALITY_CAPABILITY_ACTIONS` 的资源与 action 集保持一致，前端可无二义性消费 `auth/me` capability 快照。

### 5. 核对审计、站内信、电子签名基础能力

```powershell
Get-Content -Raw backend\app\modules\audit\router.py
Get-Content -Raw backend\services\notification\inbox_service.py
Get-Content -Raw backend\app\modules\electronic_signature\routes\manage.py
```

期望：

- 仓库中已有审计、站内信、电子签名的基础代码，可作为后续整改复用能力。

### 6. 可选：核对当前合规校验基线

```powershell
python scripts\validate_fda03_repo_compliance.py --json
python scripts\validate_gbz02_repo_compliance.py --json
python scripts\validate_gbz04_repo_compliance.py --json
python scripts\validate_gbz05_repo_compliance.py --json
```

期望：

- 在整改前，至少部分报告显示 `passed=false` 或暴露缺失前提。

Fail-fast 规则：

- 若命令无法执行，评审人应明确记录是工具缺失、环境缺失还是仓库事实变化，不能把失败当作通过。

### 7. 运行质量权限与 API 鉴权单测（P2-P3）

```powershell
python -m pytest `
  backend/tests/test_auth_me_service_unit.py `
  backend/tests/test_document_control_api_unit.py `
  backend/tests/test_training_compliance_api_unit.py `
  backend/tests/test_change_control_api_unit.py `
  backend/tests/test_equipment_api_unit.py `
  backend/tests/test_metrology_api_unit.py `
  backend/tests/test_maintenance_api_unit.py `
  backend/tests/test_audit_events_api_unit.py -q
```

期望：

- 全部用例通过。
- 未授权访问返回明确 `403`，且 detail 不出现 `admin_required` 作为兼容兜底。
- 至少包含非 `admin`（质量子管理员）成功访问质量域 API 的用例。

### 8. 运行批记录后端单测（P4）

```powershell
python -m pytest backend/tests/test_batch_records_api_unit.py -q
```

期望：

- 用例通过。
- 未授权路径返回明确 `403`。
- 签名复用电子签名能力，关键动作写入审计日志。

### 9. 运行批记录前端 Jest 单测（P5）

```powershell
Set-Location 'D:\ProjectPackage\RagflowAuth\fronted'
$env:CI='true'
npm test -- --watch=false --runInBand src/pages/QualitySystemBatchRecords.test.js
```

期望：

- 用例通过。
- 页面渲染、能力守卫与主要交互具备覆盖。

### 10. 运行批记录 Playwright 浏览器验证（P5）

```powershell
Set-Location 'D:\ProjectPackage\RagflowAuth\fronted'
npx playwright test --config=playwright.docs.config.js docs.quality-system.batch-records.spec.js --workers=1
```

期望：

- 用例通过。
- 至少产生截图、trace、HAR 或等效证据文件。

## Test Cases

### T1: 仓库现实证据与 PRD 描述一致

- Covers: P1-AC1
- Level: manual + repo inspection
- Command: 执行“核对文控主根断裂事实”“核对现有合规材料位置”“核对当前导航接入方式”“核对当前权限模型边界”“核对审计、站内信、电子签名基础能力”。
- Expected: `prd.md` 中关于文档主根冲突、`tobedeleted/compliance/*`、导航接入、能力快照、基础能力复用的描述都能从仓库中找到证据。

### T2: 整改问题清单覆盖会议纪要与 ISO 差距

- Covers: P1-AC2
- Level: manual
- Command: 打开 `docs/tasks/iso-13485-20260413T153016/prd.md`，检查“整改问题清单”章节。
- Expected: 清单覆盖文控、设计开发文件、培训、`体系文件`入口、变更、设备、计量、维护、批记录、审计日志、投诉待定等事项，且每项都能追溯到仓库证据或明确标注为会议纪要要求。

### T3: `体系文件`治理中枢方案可落地

- Covers: P1-AC3
- Level: manual + repo inspection
- Command: 阅读 `prd.md` 中“`体系文件`治理中枢方案”章节，并对照执行“核对当前导航接入方式”“核对当前权限模型边界”。
- Expected: PRD 明确说明新增入口如何挂接当前路由与侧边栏，并说明质量子管理员如何复用现有 capability/resource/action 模型，而不是另造权限系统。

### T4: 关键流程要求已细化到可执行规则

- Covers: P1-AC4
- Level: manual
- Command: 阅读 `prd.md` 中“关键流程整改要求”章节。
- Expected: 至少明确上传时确认上一版关系、审核/批准/生效/作废留痕、培训 15 分钟阅读与“已知晓/有疑问”双分支、站内信提问闭环、目标知识库选择、变更台账与计划提醒及回归台账、设备/计量/维护台账要求、批记录实时性/拍照/签名要求，以及全局搜索/智能对话/文档调用留痕。

### T5: 路线图、优先级与 no-fallback 原则明确

- Covers: P1-AC5
- Level: manual
- Command: 阅读 `prd.md` 中“整改实施路线图”“Non-Goals”“Blocking Conditions”章节。
- Expected: PRD 明确“文控 + 设备”为前期重点，明确单一受控主根原则，并明确禁止通过占位文件、双路径兼容或静默降级来“先过门禁”。

### T6: 测试计划可支持独立评审

- Covers: P1-AC6
- Level: manual
- Command: 阅读 `docs/tasks/iso-13485-20260413T153016/test-plan.md`。
- Expected: 测试计划包含具体命令、可执行的人工校验步骤、评审独立性约束和明确的通过/不通过标准。

### T7: 质量 capability 合同与 `auth/me` 快照稳定

- Covers: P2-AC1; P2-AC2
- Level: automated (pytest)
- Command: `python -m pytest backend/tests/test_auth_me_service_unit.py -q`
- Expected: 用例通过；并断言前后端质量 capability 资源/action 集一致，且质量子管理员（非 `admin`）在 `auth/me` 返回真实质量 action。

### T8: 未授权访问质量域 API 明确拒绝（403）

- Covers: P2-AC3; P3-AC2
- Level: automated (pytest)
- Command: `python -m pytest backend/tests/test_equipment_api_unit.py backend/tests/test_metrology_api_unit.py backend/tests/test_maintenance_api_unit.py -q`
- Expected: 非授权用户访问质量域写接口返回 `403`，detail 不为 `admin_required`。

### T9: 非 admin（质量子管理员）可基于 capability 执行质量域动作

- Covers: P3-AC2
- Level: automated (pytest)
- Command: `python -m pytest backend/tests/test_document_control_api_unit.py backend/tests/test_training_compliance_api_unit.py backend/tests/test_change_control_api_unit.py -q`
- Expected: 至少一个非 `admin` 用户成功调用质量域写接口；其他未授权路径返回明确 `403`。

### T10: 建议质量域回归命令全量通过

- Covers: P3-AC1; P3-AC3
- Level: automated (pytest)
- Command: 执行“运行质量权限与 API 鉴权单测（P2-P3）”中的 pytest 命令。
- Expected: 全部通过，且输出无静默跳过/伪通过。

### T11: 批记录后端闭环通过单测

- Covers: P4-AC1; P4-AC2; P4-AC3; P4-AC4
- Level: automated (pytest)
- Command: `python -m pytest backend/tests/test_batch_records_api_unit.py -q`
- Expected: 覆盖模板、执行、步骤写入、签名/复核、导出与拒绝路径；签名复用电子签名能力；关键动作写入审计日志。

### T12: 批记录前端工作区通过目标 Jest 测试

- Covers: P5-AC1; P5-AC2; P5-AC3
- Level: automated (jest)
- Command: `Set-Location 'D:\ProjectPackage\RagflowAuth\fronted'; $env:CI='true'; npm test -- --watch=false --runInBand src/pages/QualitySystemBatchRecords.test.js`
- Expected: 页面渲染、能力守卫与主要交互通过单测验证。

### T13: 批记录入口 Playwright 浏览器验证通过

- Covers: P5-AC4
- Level: e2e
- Command: `Set-Location 'D:\ProjectPackage\RagflowAuth\fronted'; npx playwright test --config=playwright.docs.config.js docs.quality-system.batch-records.spec.js --workers=1`
- Expected: 真实浏览器中验证质量系统入口与批记录工作区可访问，并覆盖至少一个能力受限场景，且产出截图/trace/HAR 等证据。

## Coverage Matrix

| Case ID | Area | Scenario | Level | Acceptance IDs | Evidence |
| --- | --- | --- | --- | --- | --- |
| T1 | 仓库事实 | PRD 中的核心事实与仓库现实一致 | manual + repo inspection | P1-AC1 | `test-report.md` |
| T2 | 差距清单 | 整改问题清单覆盖会议纪要与 ISO 差距 | manual | P1-AC2 | `test-report.md` |
| T3 | 体系页签 | `体系文件`治理中枢方案可落地且接入现有模式 | manual + repo inspection | P1-AC3 | `test-report.md` |
| T4 | 流程规则 | 文控、培训、变更、设备、批记录、审计等规则足够具体 | manual | P1-AC4 | `test-report.md` |
| T5 | 实施原则 | 路线图、优先级与 no-fallback 原则明确 | manual | P1-AC5 | `test-report.md` |
| T6 | 独立评审 | 测试计划本身具备独立评审能力 | manual | P1-AC6 | `test-report.md` |
| T7 | capability 合同 | 质量 capability 与 `auth/me` 快照稳定可消费 | automated (pytest) | P2-AC1; P2-AC2 | `test-report.md` |
| T8 | API 鉴权 | 未授权访问质量域 API 返回明确 403 | automated (pytest) | P2-AC3; P3-AC2 | `test-report.md` |
| T9 | API 鉴权 | 质量子管理员可基于 capability 执行质量域动作 | automated (pytest) | P3-AC2 | `test-report.md` |
| T10 | 回归 | 质量域相关 pytest 命令全量通过 | automated (pytest) | P3-AC1; P3-AC3 | `test-report.md` |
| T11 | 批记录后端 | 批记录模板/执行/签名/复核/导出闭环 | automated (pytest) | P4-AC1; P4-AC2; P4-AC3; P4-AC4 | `test-report.md` |
| T12 | 批记录前端 | 工作区渲染、能力守卫与主要交互 | automated (jest) | P5-AC1; P5-AC2; P5-AC3 | `test-report.md` |
| T13 | 批记录浏览器 | Playwright 浏览器入口与受限场景验证 | e2e | P5-AC4 | `test-report.md` |

## Evaluator Independence

- Mode: blind-first-pass
- Validation surface: real-browser
- Required tools: rg, PowerShell, python, python -m pytest, node, npm, playwright
- First-pass readable artifacts: prd.md, test-plan.md
- Withheld artifacts: execution-log.md, task-state.json
- Real environment expectation: 评审应以当前真实仓库为准；如果仓库事实变化，应先记录差异再判定结果。
- Escalation rule: 在写出初始判断前，不应查看 execution-log.md 和 task-state.json；除非主代理要求做差异分析。

## Pass / Fail Criteria

- Pass when:
  - `prd.md` 与 `test-plan.md` 完整、结构正确，并满足 P1-AC1 至 P1-AC6。
  - 质量 capability 合同冻结与 `auth/me` 快照满足 P2-AC1 至 P2-AC3。
  - 质量域 API 鉴权收敛与单测满足 P3-AC1 至 P3-AC3。
  - 批记录后端闭环与单测满足 P4-AC1 至 P4-AC4。
  - 批记录前端工作区、Jest 与 Playwright 证据满足 P5-AC1 至 P5-AC4。
  - PRD 中的关键事实均能通过仓库命令或会议纪要核实。
  - 文档明确说明本次仅交付整改方案，不伪装成系统已整改完成。
- Fail when:
  - 文档泛泛而谈，无法对照仓库事实。
  - `体系文件`只被描述为普通文件页，没有治理中枢定位。
  - 缺少文控、培训、变更、设备、批记录、审计等关键要求。
  - 质量域 API 仍依赖 `AdminOnly` 或角色名硬编码作为主要鉴权入口。
  - 未授权路径未返回明确 `403`，或出现角色名 fallback 的兼容兜底。
  - 批记录签名未复用电子签名能力，或关键动作未写入审计日志。
  - Playwright 用例未产出可复核证据文件（截图/trace/HAR 等）。
  - 文档建议使用双路径兼容、占位文件、静默降级等方式来通过合规门禁。
- Blocked when:
  - 评审环境缺少必要工具，导致关键事实无法验证。
  - 缺少 node/npm 或 playwright，导致 P5 无法验证。

## Regression Scope

P1 是文档交付；P2-P3 包含后端权限与鉴权代码变更，因此需要最小回归范围：

- `auth/me` capability 快照结构与前端消费一致性。
- 质量域路由的 capability 鉴权与 403 拒绝语义。
- 质量域相关后端单测覆盖与稳定性。
- 批记录后端与前端工作区的最小闭环测试（pytest/Jest/Playwright）。

为支持后续实施与评审，评审人仍应关注下列耦合区域是否在 PRD 中被正确点名：

- 合规校验脚本与审核包导出。
- 导航与权限接入模式。
- 培训数据种子与训练矩阵引用。
- 审计、站内信、电子签名基础能力。

## Reporting Notes

测试结果写入 `test-report.md`，至少包含：

- 执行环境。
- 每个测试用例的结果与简短证据说明。
- 最终结论。
- 若发现 PRD 与仓库现实不一致，必须明确列出差异点。
