# Test Report

- Task ID: `docs-tasks-iso-13485-prd-llm-20260413t162500-dev-20260413T173900`
- Created: `2026-04-13T17:39:00`
- Workspace: `D:\ProjectPackage\RagflowAuth`
- User Request: `参考 docs/tasks/iso-13485-prd-llm-20260413T162500/development-docs/WS07-audit-and-evidence-export.md 开发 WS07：补齐统一审计事件、证据导出、全局搜索与智能对话留痕，并完成后端/前端/测试交付`

## Environment Used

- Evaluation mode: blind-first-pass
- Validation surface: real-browser
- Tools: pytest, npm/react-scripts, playwright, playwright-cli
- Initial readable artifacts: prd.md, test-plan.md
- Initial withheld artifacts: execution-log.md, task-state.json
- Initial verdict before withheld inspection: yes

Record the tester's first-pass visibility honestly. In `blind-first-pass`, the tester should record `yes` only after writing an initial verdict before inspecting withheld artifacts.

## Results

### T1: 后端审计查询契约

- Result: passed
- Covers: P1-AC1
- Command run: python -m pytest backend/tests/test_audit_events_api_unit.py
- Environment proof: Local workspace D:\ProjectPackage\RagflowAuth on Windows with Python 3.12.10 and repository pytest config
- Evidence refs: output/playwright/ws07-t1-pytest.log, output/playwright/ws07-audit-global-search.png
- Notes: 1 test passed; the /api/audit/events unit contract stayed stable after the WS07 field additions.

### T2: 搜索与对话留痕后端路径

- Result: passed
- Covers: P1-AC2, P1-AC3, P1-AC5
- Command run: python -m pytest backend/tests/test_search_chat_audit_unit.py backend/tests/test_audit_log_manager_unit.py
- Environment proof: Local workspace D:\ProjectPackage\RagflowAuth on Windows with Python 3.12.10 and repository pytest config
- Evidence refs: output/playwright/ws07-t2-pytest.log, output/playwright/ws07-audit-smart-chat.png
- Notes: 4 tests passed; search/chat audit writes and manager shaping covered the new global_search and smart_chat persistence paths without silent fallback.

### T3: 证据导出携带 WS07 事件

- Result: passed
- Covers: P1-AC4, P1-AC5
- Command run: python -m pytest backend/tests/test_audit_evidence_export_api_unit.py
- Environment proof: Local workspace D:\ProjectPackage\RagflowAuth on Windows with Python 3.12.10 and repository pytest config
- Evidence refs: output/playwright/ws07-t3-pytest.log, output/playwright/ws07-inspection-evidence-20260413T104735Z.zip, output/playwright/ws07-inspection-evidence-20260413T105007Z.zip
- Notes: 2 tests passed; audit evidence export stayed verifiable and the browser-downloaded packages later confirmed manifest/checksum files in real output artifacts.

### T4: 前端审计页状态与导出交互

- Result: passed
- Covers: P2-AC1, P2-AC3
- Command run: CI=true npm test -- --runInBand --watch=false src/features/audit/api.test.js src/features/audit/useAuditLogsPage.test.js src/pages/AuditLogs.test.js
- Environment proof: Local fronted/ workspace with npm/react-scripts available; Jest executed against the checked-out React app
- Evidence refs: output/playwright/ws07-t4-frontend.log, output/playwright/ws07-audit-global-search.png
- Notes: 3 suites / 8 tests passed. PowerShell surfaced npm stdout as a NativeCommandError-formatted line, but Jest completed with exit code 0 and the suite summary was fully green.

### T5: 前端对搜索/对话类事件展示

- Result: passed
- Covers: P2-AC2, P2-AC3
- Command run: CI=true npm test -- --runInBand --watch=false src/pages/AuditLogs.test.js
- Environment proof: Local fronted/ workspace with npm/react-scripts available; targeted AuditLogs page test ran against the checked-out React app
- Evidence refs: output/playwright/ws07-t5-frontend.log, output/playwright/ws07-audit-smart-chat.png
- Notes: 1 test passed; AuditLogs rendered the mapped global_search/smart_chat labels and readable context strings such as 查询摘要 and 问题摘要 for WS07 events.

### T6: 真实浏览器管理员验收

- Result: passed
- Covers: P1-AC2, P1-AC3, P1-AC4, P2-AC1, P2-AC2
- Command run: Playwright CLI browser session on http://127.0.0.1:3001 using the logged-in admin account; executed one /agents search for "记录", created one /chat session and sent one question, filtered /logs by 智能对话 and 全局搜索, then exported evidence packages from the audit page
- Environment proof: Local frontend reachable at http://127.0.0.1:3001, authenticated admin browser session, /api/auth/me returned 200, and the same runtime produced fresh audit rows timestamped 2026-04-13 18:41:40 and 2026-04-13 18:43:07
- Evidence refs: output/playwright/ws07-search-results.png, output/playwright/ws07-chat-response.png, output/playwright/ws07-audit-smart-chat.png, output/playwright/ws07-audit-global-search.png, output/playwright/ws07-inspection-evidence-20260413T104735Z.zip, output/playwright/ws07-inspection-evidence-20260413T105007Z.zip
- Notes: The audit UI showed fresh smart_chat and global_search rows with readable summaries, then downloaded two real evidence packages. Both packages contained audit_events.csv/json plus manifest.json and checksums.json; the 20260413T104735Z package included global_search_execute rows for query=记录, and the 20260413T105007Z package included smart_chat_completion with session/question/evidence_json content. A non-blocking console 401 on /api/inbox?limit=1 appeared during the logs-page session and did not interrupt WS07 flows.

## Final Verdict

- Outcome: passed
- Verified acceptance ids: P1-AC1, P1-AC2, P1-AC3, P1-AC4, P1-AC5, P2-AC1, P2-AC2, P2-AC3
- Blocking prerequisites:
- Summary: Targeted backend and frontend validation commands passed, and real-browser validation confirmed fresh global_search and smart_chat events are visible in the audit UI and exportable as verifiable evidence packages with manifest/checksum artifacts.

## Open Issues

- None blocking.
