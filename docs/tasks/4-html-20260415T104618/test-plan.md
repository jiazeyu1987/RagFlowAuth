# Test Plan: HTML 文件审核会签矩阵（从截图转写）

- Task ID: `4-html-20260415T104618`
- Created: `2026-04-15T10:46:18`
- Workspace: `D:\ProjectPackage\RagflowAuth`
- User Request: `识别上面 4 张图里的内容，将图里的内容制作成一个 HTML 的表格`

## Test Scope

验证输出 HTML 是否：

- 可在浏览器中正常渲染
- DMR / DHF 已合并为同一张表展示
- “编制人直接主管”列对所有行均为“●”
- “文档管理员”列对所有行均为“●”
- 表头/行内容/●○标记与截图一致（以抽样 + 关键行核对为主）

不在本次范围：

- 不验证 ●/○ 的业务语义
- 不验证任何后端/前端业务逻辑或接口

## Environment

- OS: Windows
- Repo: `D:\ProjectPackage\RagflowAuth`
- 需要能读取输入截图（见 PRD Preconditions）

## Accounts and Fixtures

无账号/权限依赖。

## Commands

1) 结构自检（行数统计）

```powershell
python -c "import re, pathlib; p=pathlib.Path('docs/generated/document-approval-matrix.html').read_text(encoding='utf-8'); m=re.search(r'const DATA =\\s*\\{([\\s\\S]*?)\\n\\s*\\};', p); b=m.group(1); import re as _; \nfor cat in ['DMR','DHF']:\n  m2=_.search(rf'{cat}:\\s*\\[(.*?)\\n\\s*\\],', b, _.S) or _.search(rf'{cat}:\\s*\\[(.*?)\\n\\s*\\]', b, _.S);\n  print(cat, 'rows', len(_.findall(r'\\bfile\\s*:', m2.group(1))));"
```

期望：输出 `DMR rows 24`，`DHF rows 24`（合计 48 行）。

2) 合并逻辑自检（单表渲染）

```powershell
python -c "import re, pathlib; p=pathlib.Path('docs/generated/document-approval-matrix.html').read_text(encoding='utf-8'); assert re.search(r'renderCombinedTable\\(\\[\\s*\\x22DMR\\x22\\s*,\\s*\\x22DHF\\x22\\s*\\]\\)', p); assert 'renderTable(' not in p; print('OK: combined table renderer')"
```

期望：输出 `OK: combined table renderer`。

3) 直接主管/文档管理员会签规则自检（默认全为 ●）

```powershell
python -c "import re, pathlib; p=pathlib.Path('docs/generated/document-approval-matrix.html').read_text(encoding='utf-8'); assert re.search(r'const\\s+marks\\s*=\\s*\\{[\\s\\S]*directManager:\\s*\\x22\\u25cf\\x22', p); assert re.search(r'const\\s+marks\\s*=\\s*\\{[\\s\\S]*docAdmin:\\s*\\x22\\u25cf\\x22', p); print('OK: directManager/docAdmin default mark')"
```

期望：输出 `OK: directManager/docAdmin default mark`。

4) 渲染截图（用于人工复核）

```powershell
npx playwright screenshot "file:///D:/ProjectPackage/RagflowAuth/docs/generated/document-approval-matrix.html" "evidence/document-approval-matrix.png" --full-page
```

期望：生成 `evidence/document-approval-matrix.png`。

5) JSON 结构自检（条数 + 关键键 + 角色数）

```powershell
python -c "import json; from pathlib import Path; items=json.loads(Path('docs/generated/document-approval-matrix.json').read_text(encoding='utf-8')); assert len(items)==48; first=items[0]; assert set(['文件小类','编制','审核会签','批准']).issubset(first.keys()); assert len(first['审核会签'])==17; print('OK: json extracted', len(items))"
```

期望：输出 `OK: json extracted 48`。

## Test Cases

### T1: HTML 能打开并渲染

- Covers: P1-AC1
- Level: manual
- Command: 手工用浏览器打开 `docs/generated/document-approval-matrix.html`
- Expected: 页面无报错，且页面仅渲染一张表，表格可横向滚动。

### T2: 表头列名一致

- Covers: P1-AC2
- Level: manual
- Command: 手工检查两行表头（或结合 `evidence/document-approval-matrix.png` 截图核对）
- Expected: 表头分组与列名完整，包含：编制人直接主管、QA、QC、QMS、注册、新品开发、设备开发、生产、生产计划、生产采购、仓储物流、包装设计、市场、检测中心、人力资源、财务、文档管理员、批准、备注。

### T3: DMR 表行内容与标记抽样一致

- Covers: P1-AC3
- Level: manual
- Command: 对照输入截图，抽样核对 DMR 表关键行的文字与 ●/○ 标记
- Spot-check rows (至少核对以下行):
  - `包装设计`（备注应包含“注册针对注册产品进行会签”）
  - `图纸`（生产列为“○”，生产计划列为“●”）
  - `过程检验规程`（含“编制人直接主管”与“文档管理员”标记）
  - `检验用工装模具采购技术要求及设计图纸`（备注“根据使用区域”，且含“○”标记）
- Expected: DMR 表抽样行内容与截图一致（含备注与 ●/○ 标记）。

### T4: DHF 表行内容与标记抽样一致

- Covers: P1-AC4
- Level: manual
- Command: 对照输入截图，抽样核对 DHF 表关键行的文字与 ●/○ 标记
- Spot-check rows:
  - `项目立项书`（批准应为“研发部门负责人或总经理”）
  - `设计验证方案/报告`（生产列为“○”，备注“计划性文件”，且文档管理员列为“●”）
  - `设备安装确认(IQ)方案/报告`（新品开发列为“○”）
  - `注册/临床资料汇编`（无 QA 标记）
- Expected: DHF 表抽样行内容与截图一致（含备注与 ●/○ 标记）。

### T5: 有可复核证据

- Covers: P1-AC5, P2-AC3
- Level: manual
- Command: Playwright screenshot command
- Expected: `evidence/document-approval-matrix.png` 存在。

### T6: DMR/DHF 合并为单表且不丢行

- Covers: P2-AC1, P2-AC2
- Level: manual
- Command: 运行 “结构自检（行数统计）” 与 “合并逻辑自检（单表渲染）”，并结合截图人工确认页面只渲染一张表。
- Expected: DMR 24 行 + DHF 24 行（合计 48 行），且页面只渲染一张表（DMR 与 DHF 同表展示）。

### T7: 编制人直接主管批所有行

- Covers: P3-AC1, P3-AC2
- Level: manual
- Command: 结合 `evidence/document-approval-matrix.png` 截图核对“编制人直接主管”列（该列应在“编制”右侧的第一列）。
- Expected: 表内所有行的“编制人直接主管”列均显示“●”。

### T8: 文档管理员批所有行

- Covers: P4-AC1, P4-AC2
- Level: manual
- Command: 结合 `evidence/document-approval-matrix.png` 截图核对“文档管理员”列（该列位于“标准化审核”分组下）。
- Expected: 表内所有行的“文档管理员”列均显示“●”。

### T9: JSON 已导出且结构正确

- Covers: P5-AC1, P5-AC2, P5-AC3
- Level: manual
- Command: 运行 “JSON 结构自检（条数 + 关键键 + 角色数）”
- Expected: `docs/generated/document-approval-matrix.json` 为有效 JSON，含 48 条记录，每条记录键与角色数符合预期。

## Coverage Matrix

| Case ID | Area | Scenario | Level | Acceptance IDs | Evidence |
| --- | --- | --- | --- | --- | --- |
| T1 | docs/generated | HTML 渲染 | manual | P1-AC1 | `evidence/document-approval-matrix.png` |
| T2 | docs/generated | 表头列名 | manual | P1-AC2 | `evidence/document-approval-matrix.png` |
| T3 | DMR | 行内容/标记抽样 | manual | P1-AC3 | `evidence/document-approval-matrix.png` |
| T4 | DHF | 行内容/标记抽样 | manual | P1-AC4 | `evidence/document-approval-matrix.png` |
| T5 | evidence | 证据产出 | manual | P1-AC5, P2-AC3 | `evidence/document-approval-matrix.png` |
| T6 | merge | 单表合并 + 行数 | manual | P2-AC1, P2-AC2 | `evidence/document-approval-matrix.png` |
| T7 | directManager | 直接主管全会签 | manual | P3-AC1, P3-AC2 | `evidence/document-approval-matrix.png` |
| T8 | docAdmin | 文档管理员全会签 | manual | P4-AC1, P4-AC2 | `evidence/document-approval-matrix.png` |
| T9 | json | 导出 JSON | manual | P5-AC1, P5-AC2, P5-AC3 | `docs/generated/document-approval-matrix.json` |

## Evaluator Independence

- Mode: blind-first-pass
- Validation surface: real-browser
- Required tools: playwright
- First-pass readable artifacts: prd.md, test-plan.md
- Withheld artifacts: execution-log.md, task-state.json
- Real environment expectation: 在真实工作区打开生成的 HTML 文件，并使用 Playwright 生成截图作为证据；抽样对照输入截图核对关键行文字与 ●/○ 标记。
- Escalation rule: 在给出初次结论前，不应查看 `execution-log.md` 与 `task-state.json`。

## Pass / Fail Criteria

- Pass when:
  - T1 ~ T9 全部通过
- Fail when:
  - 缺少输入截图导致无法核对
  - HTML 缺行/缺列/明显标记错误

## Regression Scope

无（本任务仅新增静态 HTML 文档）。

## Reporting Notes

将结果写入 `test-report.md`，并附证据文件路径。
