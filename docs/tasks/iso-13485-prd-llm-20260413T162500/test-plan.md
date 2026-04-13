# 测试计划：ISO 13485 多 LLM 开发拆解文档包

- Task ID: `iso-13485-prd-llm-20260413T162500`
- Created: `2026-04-13T16:25:00`
- Workspace: `D:\ProjectPackage\RagflowAuth`
- User Request: `基于现有 ISO 13485 整改 PRD，将其拆解成若干份可以独立开发、可分别分配给不同 LLM 的开发文档包，明确每个工作流的目标、边界、依赖、接口、验收标准与交接约束`

## Test Scope

本轮只验证“开发拆解文档包”是否完整、独立、可交接，不验证后续代码是否已实现。

本轮评审需要验证：

- 是否已经从源 PRD 中拆出一组明确的工作流文档。
- 是否存在总览文档和共享契约文档。
- 每个工作流文档是否都有可分配给独立 LLM 的必要信息。
- 文档是否基于真实仓库路径，而不是虚构模块。
- 是否明确标出源 PRD 中仍然不足以开发化的事项。

以下内容不在本轮范围内：

- 实际编码。
- 实际数据库设计。
- 实际页面效果。
- 实际接口联调。

## Environment

- 平台：Windows / PowerShell。
- 仓库根目录：`D:\ProjectPackage\RagflowAuth`。
- 工具要求：
  - PowerShell
  - `python`
- 说明：
  - 本轮校验以文档和仓库路径为主，不依赖运行中的前后端服务。
  - 如果任务目录或源 PRD 缺失，应立即判定为 `blocked`。

## Accounts and Fixtures

本轮评审不需要账号。

评审所需输入只有：

- 源 PRD [source-prd](D:/ProjectPackage/RagflowAuth/docs/tasks/iso-13485-20260413T153016/prd.md)
- 新任务目录下的 `prd.md`、`test-plan.md` 和 `development-docs/*`
- 当前仓库实际代码结构

若上述任一输入缺失，评审人必须停止并记录缺失前提。

## Commands

所有命令均从仓库根目录执行：

```powershell
Set-Location 'D:\ProjectPackage\RagflowAuth'
```

### 1. 检查开发文档包是否完整

```powershell
Get-ChildItem -Path 'docs/tasks/iso-13485-prd-llm-20260413T162500/development-docs' -File | Select-Object Name
```

期望：

- 可以看到 `00-overview.md`、`01-shared-interfaces.md` 和 `WS01` 到 `WS08` 的工作流文档。

### 2. 检查源 PRD 与拆解 PRD 是否都存在

```powershell
Test-Path 'docs/tasks/iso-13485-20260413T153016/prd.md'
Test-Path 'docs/tasks/iso-13485-prd-llm-20260413T162500/prd.md'
```

期望：

- 两个结果都为 `True`。

### 3. 检查工作流文档是否具备统一结构

```powershell
Select-String -Path 'docs/tasks/iso-13485-prd-llm-20260413T162500/development-docs/WS*.md' -Pattern '^## 目标$','^## 负责边界$','^## 代码写入边界$','^## 共享接口$','^## 验收标准$','^## 交接给 LLM 的规则$'
```

期望：

- 每份 `WS*.md` 都能匹配到上述标题。

### 4. 检查拆解文档是否锚定真实仓库路径

```powershell
Get-Content -Raw 'fronted/src/routes/routeRegistry.js'
Get-Content -Raw 'fronted/src/components/layout/LayoutSidebar.js'
Get-Content -Raw 'backend/app/core/permission_models.py'
Get-Content -Raw 'backend/app/modules/documents/router.py'
Get-Content -Raw 'backend/app/modules/training_compliance/router.py'
Get-Content -Raw 'backend/app/modules/emergency_changes/router.py'
Get-Content -Raw 'backend/app/modules/audit/router.py'
```

期望：

- 评审人能够从这些真实文件中确认拆解文档提到的边界和落点不是虚构的。

### 5. 检查是否记录了源 PRD 的未冻结事项

```powershell
Select-String -Path 'docs/tasks/iso-13485-prd-llm-20260413T162500/development-docs/00-overview.md' -Pattern '钉钉','Windchill','Teamcenter','冠骋','培训方式','李欣'
```

期望：

- 总览文档明确标记这些是上游缺口或待补充事项，而不是已冻结的编码任务。

## Test Cases

### T1: 文档包完整存在

- Covers: P1-AC1
- Level: manual
- Command: 执行“检查开发文档包是否完整”和“检查源 PRD 与拆解 PRD 是否都存在”。
- Expected: 源 PRD、新任务 PRD、新任务测试计划以及 `development-docs` 下的总览、共享契约和各工作流文档全部存在。

### T2: 工作流拆分足够独立

- Covers: P1-AC1, P1-AC3
- Level: manual
- Command: 阅读 `00-overview.md` 和所有 `WS*.md`，重点核对“负责边界”“代码写入边界”“依赖关系”。
- Expected: 每个工作流都有清晰 owner，且共享文件 owner 被明确指定，不存在大面积长期重叠写入。

### T3: 每份工作流文档都有独立交接能力

- Covers: P1-AC2
- Level: manual + repo inspection
- Command: 执行“检查工作流文档是否具备统一结构”，并抽查至少 3 份 `WS*.md`。
- Expected: 每份工作流文档都至少包含目标、负责边界、代码写入边界、共享接口、验收标准、交接规则。

### T4: 共享契约足以避免不同 LLM 自行发明接口

- Covers: P1-AC4
- Level: manual
- Command: 阅读 `01-shared-interfaces.md`。
- Expected: 文档中冻结了路由前缀、能力资源名、通用实体 ID、通知载荷和审计事件结构，并明确了 owner。

### T5: 上游缺口被显式记录

- Covers: P1-AC5
- Level: manual
- Command: 执行“检查是否记录了源 PRD 的未冻结事项”，并阅读 `00-overview.md` 的相应章节。
- Expected: 文档清楚说明哪些事项不能直接分发给编码 LLM，避免误开发。

### T6: 测试计划可支撑独立复核

- Covers: P1-AC6
- Level: manual
- Command: 阅读 `docs/tasks/iso-13485-prd-llm-20260413T162500/test-plan.md`。
- Expected: 测试计划包含具体命令、人工核对步骤、独立性约束和通过/不通过标准。

## Coverage Matrix

| Case ID | Area | Scenario | Level | Acceptance IDs | Evidence |
| --- | --- | --- | --- | --- | --- |
| T1 | 工件存在性 | 新旧 PRD 与拆解文档包存在 | manual | P1-AC1 | `test-report.md` |
| T2 | 并行开发边界 | 工作流独立且 owner 明确 | manual | P1-AC1, P1-AC3 | `test-report.md` |
| T3 | 文档结构 | 每份工作流文档可独立交接给 LLM | manual + repo inspection | P1-AC2 | `test-report.md` |
| T4 | 共享契约 | 共享接口冻结且有唯一 owner | manual | P1-AC4 | `test-report.md` |
| T5 | 上游缺口 | 未冻结事项被显式记录 | manual | P1-AC5 | `test-report.md` |
| T6 | 评审独立性 | 测试计划可独立执行 | manual | P1-AC6 | `test-report.md` |

## Evaluator Independence

- Mode: blind-first-pass
- Validation surface: real-runtime
- Required tools: PowerShell, python
- First-pass readable artifacts: prd.md, test-plan.md
- Withheld artifacts: execution-log.md, task-state.json
- Real environment expectation: 评审人以当前仓库和当前任务目录中的真实文档为准，不依赖聊天上下文补充隐含信息。
- Escalation rule: 在写出初始判断前，不查看 `execution-log.md` 和 `task-state.json`；除非主代理要求做偏差分析。

## Pass / Fail Criteria

- Pass when:
  - `development-docs/` 下的总览、共享契约和所有工作流文档都存在。
  - 每份工作流文档都能独立交接给 LLM。
  - 共享接口、共享 owner、依赖顺序和上游缺口都被明确写出。
- Fail when:
  - 文档包只有总纲，没有细分工作流。
  - 多个工作流仍长期共享同一组核心写入文件且没有 owner 约束。
  - 文档没有写清代码边界、共享接口或验收标准。
  - 源 PRD 未冻结事项被误写成可直接编码需求。

## Regression Scope

本次任务是文档拆解任务，没有产品代码回归。

但评审时应确认文档引用的真实代码区域至少覆盖：

- 路由与侧边栏
- 权限快照
- 文档模块
- 培训模块
- 通知/站内信模块
- 变更模块
- 审计模块

## Reporting Notes

测试结果写入 `test-report.md`，至少包含：

- 执行环境
- 每个测试用例的结果
- 对文档包是否可供不同 LLM 独立开发的结论
- 发现的重叠边界或缺口
