# 识别图片内容并转写为 HTML 表格（DMR / DHF 文件审核会签矩阵）

- Task ID: `4-html-20260415T104618`
- Created: `2026-04-15T10:46:18`
- Workspace: `D:\ProjectPackage\RagflowAuth`
- User Request: `识别上面 4 张图里的内容，将图里的内容制作成一个 HTML 的表格`

## Goal

把用户提供的 4 张截图中的“文件审核会签矩阵”转写为可编辑的 HTML 表格，包含：

- 表头（含“审核会签 / 标准化审核”分组）
- 行内容（文件大类/文件小类/编制/批准/备注）
- 单元格标记（● / ○）

## Scope

- 生成一个 HTML 文件：`docs/generated/document-approval-matrix.html`
- 提取并生成一个 JSON 文件：`docs/generated/document-approval-matrix.json`
- 内容包含 DMR 与 DHF，并合并为同一张表展示
- “编制人直接主管”列对所有行均需会签（●）
- “文档管理员”列对所有行均需会签（●）

## Non-Goals

- 不解释或推断 “● / ○” 的业务含义（仅按截图转写）
- 不把表格写入数据库 / 不接入后端接口
- 不新增导出 PDF/Excel 等功能（除非用户后续明确要求）

## Preconditions

必须能访问 4 张输入截图（路径为当前环境实测可读）：

- DMR（上半）：`C:\Users\BJB110\AppData\Roaming\DingTalk\de78dc71902ffa4b3495_v3\resource_cache\09\09389e5e5b7b58a4534ad47a9a385d5f.png`
- DMR（下半）：`C:\Users\BJB110\AppData\Roaming\DingTalk\de78dc71902ffa4b3495_v3\resource_cache\a0\a09b998c77fd28549fbd49c436532579.png`
- DHF（上半）：`C:\Users\BJB110\AppData\Roaming\DingTalk\de78dc71902ffa4b3495_v3\ImageFiles\82\lQLPKczaDRrIvgXNAwDNBl6wwkk3gC_UxHcJtVUQiymWAA_1630_768.png`
- DHF（下半）：`C:\Users\BJB110\AppData\Roaming\DingTalk\de78dc71902ffa4b3495_v3\ImageFiles\ae\lQLPJxIIcXtK4IXNAjfNBXewTsg7vIxeXawJtVUtLBbxAA_1399_567.png`

如果任一输入缺失，应停止并记录到 `task-state.json.blocking_prereqs`。

## Impacted Areas

- `docs/generated/document-approval-matrix.html`
- 任务工件（`docs/tasks/4-html-20260415T104618/*`）

## Phase Plan

### P1: 生成 HTML 表格

- Objective: 从截图转写数据并输出为 HTML 表格（含 DMR 与 DHF）
- Owned paths:
  - `docs/generated/document-approval-matrix.html`
- Dependencies:
  - 输入截图可读
- Deliverables:
  - HTML 文件可直接打开查看

### P2: 合并 DMR 与 DHF 为单表

- Objective: 将 DMR 与 DHF 的内容在同一个 `<table>` 内呈现（仍保留“文件大类”列区分 DMR / DHF）。
- Owned paths:
  - `docs/generated/document-approval-matrix.html`
- Dependencies:
  - P1 已完成且数据转写正确
- Deliverables:
  - 页面仅渲染一张表，包含 DMR 与 DHF 全部行

### P3: 编制人直接主管全部会签

- Objective: “编制人直接主管”列对所有行均为“●”。
- Owned paths:
  - `docs/generated/document-approval-matrix.html`
- Dependencies:
  - P1/P2 已完成
- Deliverables:
  - 合并后的单表中，“编制人直接主管”列所有行均显示“●”

### P4: 文档管理员全部会签

- Objective: “文档管理员”列对所有行均为“●”。
- Owned paths:
  - `docs/generated/document-approval-matrix.html`
- Dependencies:
  - P1/P2 已完成
- Deliverables:
  - 合并后的单表中，“文档管理员”列所有行均显示“●”

### P5: 输出 JSON（文件小类/编制/审核会签/批准）

- Objective: 将表格数据按“文件小类 / 编制 / 审核会签 / 批准”字段导出为 JSON，便于系统对接或二次加工。
- Owned paths:
  - `docs/generated/document-approval-matrix.json`
- Dependencies:
  - P1-P4 已完成
- Deliverables:
  - JSON 文件可被程序读取（UTF-8）

## Phase Acceptance Criteria

### P1

- P1-AC1: `docs/generated/document-approval-matrix.html` 存在且为 UTF-8，可在浏览器中打开渲染。
- P1-AC2: 表头列名与截图一致（文件大类/文件小类/编制/审核会签列/标准化审核列/批准/备注）。
- P1-AC3: DMR 表包含截图中的全部行内容与对应单元格标记（● / ○），且备注文本一致。
- P1-AC4: DHF 表包含截图中的全部行内容与对应单元格标记（● / ○），且备注文本一致。
- P1-AC5: 生成可复核证据（例如 Playwright 截图）用于对照检查渲染结果。

### P2

- P2-AC1: 页面仅渲染一张表（DMR 与 DHF 同表展示），且“文件大类”列能区分 DMR / DHF。
- P2-AC2: 合并后不丢行：DMR 24 行 + DHF 24 行，总计 48 行。
- P2-AC3: 更新渲染截图证据，用于人工复核合并后的显示效果。

### P3

- P3-AC1: “编制人直接主管”列对所有行均显示“●”。
- P3-AC2: 更新渲染截图证据，用于人工复核“编制人直接主管”列显示效果。

### P4

- P4-AC1: “文档管理员”列对所有行均显示“●”。
- P4-AC2: 更新渲染截图证据，用于人工复核“文档管理员”列显示效果。

### P5

- P5-AC1: `docs/generated/document-approval-matrix.json` 存在且为有效 JSON（UTF-8）。
- P5-AC2: JSON 内共 48 条记录（DMR 24 + DHF 24），且每条记录包含键：文件小类、编制、审核会签、批准。
- P5-AC3: 审核会签字段包含 17 个角色键（含“编制人直接主管”与“文档管理员”），且二者在所有记录中均为“●”。

Evidence expectation:

- 证据应写入 `execution-log.md` 与 `test-report.md`，至少包含：
  - 输出 HTML 路径
  - 渲染截图路径（或可复现的生成命令）

## Done Definition

- P1 完成，且 P1-AC1 ~ P1-AC5 全部满足
- P2 完成，且 P2-AC1 ~ P2-AC3 全部满足
- P3 完成，且 P3-AC1 ~ P3-AC2 全部满足
- P4 完成，且 P4-AC1 ~ P4-AC2 全部满足
- P5 完成，且 P5-AC1 ~ P5-AC3 全部满足
- `test-report.md` 显示测试通过（或可复现实测证据）

## Blocking Conditions

- 无法读取输入截图或无法确认截图内容（禁止“猜测补全”）
- 输出 HTML 无法渲染或明显缺失行/列/标记
