# Test Report: HTML 文件审核会签矩阵（从截图转写）

- Task ID: `4-html-20260415T104618`
- Created: `2026-04-15T10:46:18`
- Workspace: `D:\ProjectPackage\RagflowAuth`
- User Request: `识别上面 4 张图里的内容，将图里的内容制作成一个 HTML 的表格`

## Environment Used

- Evaluation mode: blind-first-pass
- Validation surface: real-browser
- Tools: python, npx playwright, playwright
- Initial readable artifacts: prd.md, test-plan.md
- Initial withheld artifacts: execution-log.md, task-state.json
- Initial verdict before withheld inspection: yes

## Results

### T1: HTML 能打开并渲染

- Result: passed
- Covers: P1-AC1
- Command run: `npx playwright screenshot "file:///D:/ProjectPackage/RagflowAuth/docs/generated/document-approval-matrix.html" "evidence/document-approval-matrix.png" --full-page`
- Environment proof: `file:///D:/ProjectPackage/RagflowAuth/docs/generated/document-approval-matrix.html`
- Evidence refs: evidence/document-approval-matrix.png
- Notes: 页面可渲染，且 DMR / DHF 已合并为同一张表展示。

### T2: 表头列名一致

- Result: passed
- Covers: P1-AC2
- Command run: Manual check against evidence/document-approval-matrix.png
- Environment proof: evidence/document-approval-matrix.png
- Evidence refs: evidence/document-approval-matrix.png
- Notes: 两行表头包含分组“审核会签 / 标准化审核”，列名与截图一致。

### T3: DMR 表行内容与标记抽样一致

- Result: passed
- Covers: P1-AC3
- Command run: Inline python substring checks (see Notes)
- Environment proof: `docs/generated/document-approval-matrix.html`
- Evidence refs: evidence/document-approval-matrix.png
- Notes:
  - 抽样核对：`包装设计` 备注含“注册针对注册产品进行会签”；`图纸` 的生产=○、生产计划=●；`过程检验规程` 含 directManager=● 且 docAdmin=●；`检验用工装模具采购技术要求及设计图纸` 备注含“根据使用区域”。

### T4: DHF 表行内容与标记抽样一致

- Result: passed
- Covers: P1-AC4
- Command run: Inline python substring checks (see Notes)
- Environment proof: `docs/generated/document-approval-matrix.html`
- Evidence refs: evidence/document-approval-matrix.png
- Notes:
  - 抽样核对：`项目立项书` 批准为“研发部门负责人或总经理”；`设计验证方案/报告` 含 production=○、docAdmin=● 且备注“计划性文件”；`设备安装确认(IQ)方案/报告` 含新品开发=○。

### T5: 有可复核证据

- Result: passed
- Covers: P1-AC5, P2-AC3
- Command run: `npx playwright screenshot ... evidence/document-approval-matrix.png --full-page`
- Environment proof: evidence/document-approval-matrix.png exists
- Evidence refs: evidence/document-approval-matrix.png
- Notes: 证据文件已生成，可用于人工复核。

### T6: DMR/DHF 合并为单表且不丢行

- Result: passed
- Covers: P2-AC1, P2-AC2
- Command run: Manual check + python self-checks in test-plan Commands
- Environment proof: docs/generated/document-approval-matrix.html
- Evidence refs: evidence/document-approval-matrix.png
- Notes: 合并后页面仅渲染一张表；数据自检为 DMR 24 行 + DHF 24 行（合计 48 行）。

### T7: 编制人直接主管批所有行

- Result: passed
- Covers: P3-AC1, P3-AC2
- Command run: Manual check against evidence/document-approval-matrix.png + HTML rule self-check in test-plan Commands
- Environment proof: docs/generated/document-approval-matrix.html
- Evidence refs: evidence/document-approval-matrix.png
- Notes: “编制人直接主管”列对所有行均显示“●”。

### T8: 文档管理员批所有行

- Result: passed
- Covers: P4-AC1, P4-AC2
- Command run: Manual check against evidence/document-approval-matrix.png + HTML rule self-check in test-plan Commands
- Environment proof: docs/generated/document-approval-matrix.html
- Evidence refs: evidence/document-approval-matrix.png
- Notes: “文档管理员”列对所有行均显示“●”。

### T9: JSON 已导出且结构正确

- Result: passed
- Covers: P5-AC1, P5-AC2, P5-AC3
- Command run: python JSON self-check in test-plan Commands
- Environment proof: docs/generated/document-approval-matrix.json
- Evidence refs: docs/generated/document-approval-matrix.json
- Notes: JSON 共 48 条记录；每条记录包含 文件小类/编制/审核会签/批准；审核会签含 17 个角色键。

## Final Verdict

- Outcome: passed
- Verified acceptance ids: P1-AC1, P1-AC2, P1-AC3, P1-AC4, P1-AC5, P2-AC1, P2-AC2, P2-AC3, P3-AC1, P3-AC2, P4-AC1, P4-AC2, P5-AC1, P5-AC2, P5-AC3
- Blocking prerequisites:
- Summary: 已将 4 张截图内容转写为 docs/generated/document-approval-matrix.html，并将 DMR/DHF 合并为同一张表展示；“编制人直接主管/文档管理员”列对所有行均为“●”；已导出 JSON：docs/generated/document-approval-matrix.json；渲染截图为 evidence/document-approval-matrix.png。

## Open Issues

- None.
