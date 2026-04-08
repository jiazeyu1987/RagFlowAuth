# Ragflow Chat Session Compatibility Refactor Test Plan

- Task ID: `ragflow-chat-session-service-py-chat-update-dele-20260408T072732`
- Created: `2026-04-08T07:27:32`
- Workspace: `D:\ProjectPackage\RagflowAuth`
- User Request: `继续进行前后端重构直到重构结束：优先重构 ragflow_chat/session_service.py 的 chat update/delete 兼容逻辑，并在时间允许时进一步拆分下载页 controller，保持现有 API、页面行为与测试契约稳定`

## Test Scope

Validate that the bounded backend refactor preserves:

- chat update retry behavior for unready datasets, parsed-file ownership errors, missing responses,
  auto-clear retries, and merged dataset retries
- chat parsed-file clearing behavior
- chat delete compatibility across batch, delete-by-id, and query-param variants
- agent delete compatibility for not-found handling

Out of scope:

- frontend download-controller refactor or browser validation
- live RAGFlow integration against a running external service
- unrelated stream, prompt-builder, or citation flows

## Environment

- Platform: Windows PowerShell in `D:\ProjectPackage\RagflowAuth`
- Backend: Python with `py_compile` and `pytest`
- Test runtime: fake HTTP adapters embedded in focused unit tests

## Accounts and Fixtures

- tests rely on temporary directories and fake HTTP clients defined in
  `backend/tests/test_ragflow_chat_update_retry_unit.py`
- no live credentials or external RAGFlow service are required for the focused suite
- if Python, `py_compile`, or `pytest` is unavailable, fail fast and record the missing
  prerequisite

## Commands

- `python -m py_compile backend/services/ragflow_chat/session_service.py backend/services/ragflow_chat/session_support.py backend/services/ragflow_chat_service.py`
  - Expected success signal: all edited backend modules compile without syntax errors
- `python -m pytest backend/tests/test_ragflow_chat_update_retry_unit.py -q`
  - Expected success signal: focused compatibility suite passes

## Test Cases

### T1: Ragflow chat compatibility regression

- Covers: P1-AC1, P1-AC2, P1-AC3, P2-AC1, P2-AC2
- Level: unit
- Command: `python -m pytest backend/tests/test_ragflow_chat_update_retry_unit.py -q`
- Expected: update/delete/clear compatibility paths and stable error codes remain unchanged after
  helper extraction

## Coverage Matrix

| Case ID | Area | Scenario | Level | Acceptance IDs | Evidence |
| --- | --- | --- | --- | --- | --- |
| T1 | backend ragflow chat session compatibility | service decomposition preserves update/delete retry behavior and stable errors | unit | P1-AC1, P1-AC2, P1-AC3, P2-AC1, P2-AC2 | `test-report.md#T1` |

## Evaluator Independence

- Mode: blind-first-pass
- Validation surface: real-runtime
- Required tools: python, py_compile, pytest
- First-pass readable artifacts: prd.md, test-plan.md
- Withheld artifacts: execution-log.md, task-state.json
- Real environment expectation: run the focused backend commands against the real repo state
- Escalation rule: do not inspect withheld artifacts until the tester has produced an initial
  verdict

## Pass / Fail Criteria

- Pass when:
  - the compile command succeeds
  - T1 passes
  - public compatibility behavior and stable error codes remain unchanged
- Fail when:
  - either command fails
  - update/delete compatibility behavior regresses
  - the refactor changes stable error strings or silently downgrades incompatible failures

## Regression Scope

- `backend/services/ragflow_chat/session_service.py`
- new helper module(s) under `backend/services/ragflow_chat/`
- `backend/services/ragflow_chat_service.py`
- `backend/tests/test_ragflow_chat_update_retry_unit.py`

## Reporting Notes

- Write results to `test-report.md`.
- Record the exact commands and whether each command passed.
