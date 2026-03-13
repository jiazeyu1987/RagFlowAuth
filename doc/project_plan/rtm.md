# Requirement Traceability Matrix (RTM)

Status legend:
- `implemented`: already available in current system
- `partial`: available but not complete for acceptance scope
- `planned`: not implemented yet, must be delivered

Test ID convention:
- `UT-*`: unit test
- `IT-*`: integration test
- `E2E-*`: Playwright end-to-end
- `SEC-*`: security test
- `PERF-*`: performance/stability test

| Req ID | Requirement | Current Status | Target Module/API/UI | Acceptance Test IDs |
|---|---|---|---|---|
| R-01 | User lifecycle management (create/disable/reset) | implemented | `backend/app/modules/users`, `fronted/src/pages/UserManagement.js` | E2E-USER-001, E2E-USER-002 |
| R-02 | Permission group and fine-grained authorization | implemented | `backend/app/modules/permission_groups`, `fronted/src/pages/PermissionGroupManagement.js` | IT-AUTH-001, E2E-AUTH-001 |
| R-03 | Session concurrency + idle timeout governance | implemented | `backend/services/auth_flow_service.py`, `fronted/src/hooks/useAuth.js` | UT-SESSION-001, E2E-SESSION-001 |
| R-04 | Knowledge directory tree governance (drag/drop/batch/archive) | partial | `knowledge/routes/directory.py`, Knowledge pages | E2E-KDIR-001, E2E-KDIR-002 |
| R-05 | Chat config and search config independent maintenance | implemented | `ChatConfigsPanel`, `SearchConfigsPanel` + related APIs | E2E-CONFIG-001 |
| R-06 | Document/file/folder upload with whitelist and conflict handling | partial | Upload routes/pages + review overwrite routes | IT-UPLOAD-001, E2E-UPLOAD-001 |
| R-07 | Conflict overwrite with mandatory reason tracking | planned | upload/review domain + audit schema | IT-UPLOAD-002, E2E-REVIEW-003 |
| R-08 | Multi-session intelligent chat with streaming and source evidence | partial | `chat` module + `Chat.js` + source preview | IT-CHAT-001, E2E-CHAT-001 |
| R-09 | Full-library federated search with threshold/top_k/highlight/history | implemented | `agents` module + `Agents.js` | IT-SEARCH-001, E2E-SEARCH-001 |
| R-10 | Paper workspace (edit/version trace/version compare/rollback) | planned | new paper workspace module + UI | UT-PAPER-001, IT-PAPER-001, E2E-PAPER-001 |
| R-11 | Plagiarism module (dup rate + similar span localization + report) | planned | new plagiarism service + report UI | UT-PLAG-001, IT-PLAG-001, E2E-PLAG-001 |
| R-12 | Topic collection orchestration (start/stop/pause/resume/retry/history) | partial | paper/patent download managers + pages | IT-COLLECT-001, E2E-COLLECT-001 |
| R-13 | Auto-analysis failure tagging and visual diagnostics | partial | paper/patent analysis pipeline + UI panels | IT-COLLECT-002, E2E-COLLECT-002 |
| R-14 | Data security runtime modes (intranet/internet) | planned | data security policy module + ops UI | IT-SECMODE-001, E2E-SECMODE-001 |
| R-15 | Egress minimization policy | planned | egress gateway policy engine | SEC-EGRESS-001, IT-EGRESS-001 |
| R-16 | Sensitive classification + auto desensitization + high-sensitivity block | planned | security classification/desensitization services | SEC-DLP-001, SEC-DLP-002, IT-DLP-001 |
| R-17 | External model allowlist (domestic-only policy) | planned | model access policy service + admin UI | SEC-MODEL-001, IT-MODEL-001 |
| R-18 | Research-oriented 3-column UI layout for core workflows | planned | global layout + key page refactor | E2E-UI-001, E2E-UI-002 |

## Coverage Summary
- Total requirements: 18
- Implemented: 6
- Partial: 6
- Planned (gap): 6

## Notes
- This matrix is the single acceptance baseline for `WP-01`.
- For each planned item, implementation PR must add/attach corresponding test IDs.
