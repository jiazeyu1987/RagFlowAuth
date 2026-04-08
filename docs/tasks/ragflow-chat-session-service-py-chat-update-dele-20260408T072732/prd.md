# Ragflow Chat Session Compatibility Refactor PRD

- Task ID: `ragflow-chat-session-service-py-chat-update-dele-20260408T072732`
- Created: `2026-04-08T07:27:32`
- Workspace: `D:\ProjectPackage\RagflowAuth`
- User Request: `继续进行前后端重构直到重构结束：优先重构 ragflow_chat/session_service.py 的 chat update/delete 兼容逻辑，并在时间允许时进一步拆分下载页 controller，保持现有 API、页面行为与测试契约稳定`

## Goal

Extract the highest-risk chat update/delete compatibility logic out of
`RagflowChatSessionService` so future RAGFlow API quirks can be adjusted in one bounded support
layer instead of continuing to accumulate inside the main session service, while preserving the
existing public service behavior and stable error codes.

## Scope

- `backend/services/ragflow_chat/session_service.py`
- new bounded backend helper module(s) under `backend/services/ragflow_chat/` for chat
  update/delete compatibility and cache invalidation responsibilities
- `backend/services/ragflow_chat/__init__.py` only if import wiring must change
- `backend/services/ragflow_chat_service.py` only if inheritance or composition wiring must change
- focused compatibility tests in `backend/tests/test_ragflow_chat_update_retry_unit.py`
- task artifacts under
  `docs/tasks/ragflow-chat-session-service-py-chat-update-dele-20260408T072732/`

## Non-Goals

- changing RAGFlow chat, session, or agent API paths
- changing response envelopes, stable error strings, or current retry semantics
- refactoring the frontend download controller in this tranche
- redesigning the broader Ragflow chat prompt, stream, or citation modules
- introducing fallback, silent downgrade, or mock behavior beyond the existing explicitly preserved
  compatibility paths

## Preconditions

- Python environment can run focused backend pytest and `py_compile`.
- `RagflowChatService` remains the public backend entry point used by callers and tests.
- Existing compatibility behavior covered by
  `backend/tests/test_ragflow_chat_update_retry_unit.py` remains the source of truth.
- No schema or external service prerequisite is required because focused tests use fake HTTP
  clients.

If any item is missing, stop and record it in `task-state.json.blocking_prereqs`.

## Impacted Areas

- chat update compatibility for missing responses, parsed-file ownership failures, stale parsed-file
  binding clearing, and merged dataset retry behavior
- chat delete compatibility across batch delete, delete-by-id, and query-param delete variants
- agent delete compatibility across delete-by-id and batch delete variants
- chat ref cache invalidation after create/update/delete/agent mutation flows
- `RagflowChatService` mixin wiring and callers that depend on stable `update_chat`,
  `clear_chat_parsed_files`, `delete_chat`, and `delete_agent` behavior

## Phase Plan

### P1: Extract chat compatibility support from the session service

- Objective: Move update/delete compatibility helpers and repeated cache-reset behavior into a
  bounded support module while keeping `RagflowChatSessionService` as the stable facade.
- Owned paths:
  - `backend/services/ragflow_chat/session_service.py`
  - new helper module(s) under `backend/services/ragflow_chat/`
  - `backend/services/ragflow_chat_service.py` only if wiring cleanup is required
- Dependencies:
  - existing `RagflowPromptBuilder` helpers for dataset extraction and parsed-file field handling
  - existing public `RagflowChatService` inheritance chain
  - current compatibility tests and stable error codes
- Deliverables:
  - slimmer `session_service.py`
  - extracted support helper(s) for chat update/delete compatibility
  - unchanged public behavior for chat update/delete and agent delete flows

### P2: Focused regression validation and task evidence

- Objective: Prove the bounded backend refactor preserved the current compatibility behavior and
  fail-fast semantics.
- Owned paths:
  - `backend/tests/test_ragflow_chat_update_retry_unit.py`
  - task artifacts for this tranche
- Dependencies:
  - P1 completed
- Deliverables:
  - focused backend regression coverage
  - execution and test evidence for each acceptance criterion

## Phase Acceptance Criteria

### P1

- P1-AC1: `RagflowChatSessionService` no longer directly owns the response coercion, update
  verification, dataset-ownership retry, delete compatibility sequencing, and repeated cache-reset
  details in one file.
- P1-AC2: `update_chat`, `clear_chat_parsed_files`, `delete_chat`, and `delete_agent` preserve the
  current public behavior, including stable error codes such as `chat_dataset_not_ready`,
  `chat_dataset_locked`, `chat_not_found`, and `agent_not_found`.
- P1-AC3: compatibility handling still fails fast on non-compatible upstream failures instead of
  adding silent downgrade paths.
- Evidence expectation:
  - `execution-log.md#Phase-P1`
  - `test-report.md#T1`

### P2

- P2-AC1: focused backend compatibility tests pass against the final code state.
- P2-AC2: task artifacts record the exact commands run, verified acceptance coverage, and any
  bounded residual risk.
- Evidence expectation:
  - `execution-log.md#Phase-P2`
  - `test-report.md#T1`

## Done Definition

- P1 and P2 are completed.
- All acceptance ids have evidence in `execution-log.md` or `test-report.md`.
- `test_status` is `passed`.
- `RagflowChatService` remains the stable public entry point and compatibility behavior stays
  unchanged for focused update/delete flows.

## Blocking Conditions

- focused backend validation cannot run
- the refactor would require changing public API paths, response envelopes, or stable error strings
- preserving current behavior would require adding new fallback branches or silent downgrades
- helper extraction would break the current `RagflowChatService` inheritance chain or public method
  contract
