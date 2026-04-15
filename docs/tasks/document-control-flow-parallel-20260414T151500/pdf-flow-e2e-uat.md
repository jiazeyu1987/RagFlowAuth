# PDF Flow E2E UAT

- Task ID: `document-control-flow-parallel-20260414T151500`
- Date: `2026-04-15`
- Validation type: `real-browser`
- Environment: isolated doc E2E runtime booted by `fronted/playwright.docs.config.js`
- Important boundary: this run used the repository's real-chain E2E environment and real browser automation; it did **not** run against the production server.

## Command

```powershell
cd D:\ProjectPackage\RagflowAuth\fronted
npx playwright test --config playwright.docs.config.js e2e/tests/docs.document-control-pdf-flow.spec.js --project=chromium --workers=1
```

## Evidence

- Main video: `D:\ProjectPackage\RagflowAuth\output\playwright\document-control-pdf-flow\videos\b229ca440fb70e7b8cee7a32cc76c958.webm`
- Secondary video: `D:\ProjectPackage\RagflowAuth\output\playwright\document-control-pdf-flow\videos\7d072b8f73de324347213332c0b6405a.webm`
- Test spec: `D:\ProjectPackage\RagflowAuth\fronted\e2e\tests\docs.document-control-pdf-flow.spec.js`

## PDF Node Mapping

| PDF flow node | E2E coverage | Result |
|---|---|---|
| 新建/修订文件并上传 PDF | 使用桌面 `控制流程初稿.pdf` 作为 `v1`/`v2` 上传源，验证文控上传仅接受 PDF | passed |
| 按文件类别匹配会签矩阵 | 运行前写入 `document_type=pdf_flow_*` 的三步工作流（`cosign -> approve -> standardize_review`） | passed |
| 审核/会签 | 发起审批后完成第 1 步 | passed |
| 批准 | 完成第 2 步 | passed |
| 标准化审核 | 完成第 3 步 | passed |
| 审批节点超时提醒 | 对 `v2` 审批链等待超时后触发 overdue reminder | passed |
| 培训（若需要） | `v2` 设置 training gate，首次发布被门禁阻断；完成阅读与确认后放行 | passed |
| 受控发布 | `v1` 走 `automatic`；`v2` 走 `manual_by_doc_control` 并要求手工归档完成 | passed |
| 相关部门确认 | 发布后生成部门确认，完成部门 `303` 的 acknowledgment | passed |
| 作废 | 对 `v2` 发起并批准 obsolete | passed |
| 销毁 | 等待留存到期后执行 destruction confirm | passed |

## Walkthrough Summary

1. 用桌面 PDF 创建 `v1` 受控文件。
2. 提交审批并完成三步审批链。
3. `v1` 配置为不需要培训，按 `automatic` 发布，并生成部门确认。
4. 以同一桌面 PDF 创建 `v2` 修订。
5. 提交审批，等待超时后发送审批提醒，再完成三步审批链。
6. 为 `v2` 配置 training gate，生成单人培训任务，验证发布先被阻断。
7. 在培训工作区完成阅读计时和“已知晓”确认。
8. 以 `manual_by_doc_control` 发布 `v2`，完成手工归档，再完成部门确认。
9. 验证 `v1` 已被 supersede，`v2` 成为 effective。
10. 发起作废、批准作废、等待留存期到达后确认销毁。

## Verdict

- Overall: `passed`
- Conclusion: current code can complete the control flow represented by `控制流程初稿.pdf` inside the repository's real-browser E2E environment.
