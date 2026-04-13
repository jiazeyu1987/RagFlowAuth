# 测试计划：ISO 13485 整改文档包

- Task ID: `iso-13485-20260413T153016`
- Created: `2026-04-13T15:30:16`
- Workspace: `D:\ProjectPackage\RagflowAuth`
- User Request: `根据已识别的 ISO 13485 不符合项、会议纪要关于文控/设备/变更/批记录/体系文件入口的讨论，以及新增体系文件页签的设想，整理一份详尽的整改文档与验收工件`

## Test Scope

本测试计划只验证本次交付的整改文档包是否完整、真实、可执行，不验证后续功能是否已经实现。

本轮测试应覆盖：

- `prd.md` 是否基于当前仓库真实证据，而不是泛化描述。
- `prd.md` 是否完整覆盖会议纪要中提到的核心整改事项。
- `prd.md` 是否对`体系文件`治理中枢给出可落地的页面、权限和流程设计。
- `prd.md` 是否明确了优先级、路线图、阻断条件和禁止 fallback 的原则。
- `test-plan.md` 是否能让独立评审人复现实锤证据并给出通过/不通过结论。

以下内容不在本轮范围内：

- 实际新增 `体系文件` 页面。
- 实际迁移受控文件到新主根。
- 实际实现设备、变更、计量、批记录等业务功能。

## Environment

- 平台：Windows / PowerShell。
- 仓库根目录：`D:\ProjectPackage\RagflowAuth`。
- 依赖工具：
  - `rg`
  - `python`
- 说明：
  - 若 `rg` 不可用，评审人必须记录缺失前提并判定为 `blocked`。
  - 若需执行合规校验基线命令而 `python` 不可用，也必须记录缺失前提并判定为 `blocked`。

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

- 现有 capability 主要围绕知识库、工具、聊天、用户管理等资源。
- 尚未出现 `quality_system`、`document_control`、`change_control`、`equipment_lifecycle` 等质量域资源。

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

## Coverage Matrix

| Case ID | Area | Scenario | Level | Acceptance IDs | Evidence |
| --- | --- | --- | --- | --- | --- |
| T1 | 仓库事实 | PRD 中的核心事实与仓库现实一致 | manual + repo inspection | P1-AC1 | `test-report.md` |
| T2 | 差距清单 | 整改问题清单覆盖会议纪要与 ISO 差距 | manual | P1-AC2 | `test-report.md` |
| T3 | 体系页签 | `体系文件`治理中枢方案可落地且接入现有模式 | manual + repo inspection | P1-AC3 | `test-report.md` |
| T4 | 流程规则 | 文控、培训、变更、设备、批记录、审计等规则足够具体 | manual | P1-AC4 | `test-report.md` |
| T5 | 实施原则 | 路线图、优先级与 no-fallback 原则明确 | manual | P1-AC5 | `test-report.md` |
| T6 | 独立评审 | 测试计划本身具备独立评审能力 | manual | P1-AC6 | `test-report.md` |

## Evaluator Independence

- Mode: blind-first-pass
- Validation surface: real-runtime
- Required tools: `rg`, PowerShell；`python` 用于可选基线核验
- First-pass readable artifacts: prd.md, test-plan.md
- Withheld artifacts: execution-log.md, task-state.json
- Real environment expectation: 评审应以当前真实仓库为准；如果仓库事实变化，应先记录差异再判定结果。
- Escalation rule: 在写出初始判断前，不应查看 execution-log.md 和 task-state.json；除非主代理要求做差异分析。

## Pass / Fail Criteria

- Pass when:
  - `prd.md` 与 `test-plan.md` 完整、结构正确，并满足 P1-AC1 至 P1-AC6。
  - PRD 中的关键事实均能通过仓库命令或会议纪要核实。
  - 文档明确说明本次仅交付整改方案，不伪装成系统已整改完成。
- Fail when:
  - 文档泛泛而谈，无法对照仓库事实。
  - `体系文件`只被描述为普通文件页，没有治理中枢定位。
  - 缺少文控、培训、变更、设备、批记录、审计等关键要求。
  - 文档建议使用双路径兼容、占位文件、静默降级等方式来通过合规门禁。
- Blocked when:
  - 评审环境缺少必要工具，导致关键事实无法验证。

## Regression Scope

本次任务是文档交付，严格来说没有产品代码回归范围。

但为支持后续实施，评审人应特别关注下列耦合区域是否在 PRD 中被正确点名：

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
