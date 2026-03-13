# Delivery Progress

## Current Status
- `WP-01`: DONE
- `WP-02`: DOING

## Completed in This Iteration
1. `WP-01` governance baseline artifacts created:
   - `doc/project_plan/rtm.md`
   - `doc/project_plan/dod_template.md`
   - `doc/project_plan/change_audit_template.md`
   - `doc/project_plan/README.md`

2. `WP-02` first implementation slice (task persistence for NAS folder import):
   - Added DB schema for NAS import tasks:
     - `backend/database/schema/nas_tasks.py`
     - `backend/database/schema/ensure.py` updated to ensure the table/index.
   - Added persistent store:
     - `backend/services/nas_task_store.py`
   - Injected store into app dependencies:
     - `backend/app/dependencies.py`
   - Refactored NAS service to use persistent task store (instead of in-memory dict):
     - `backend/services/nas_browser_service.py`
   - Refactored NAS router to pass injected store and cleaned route texts:
     - `backend/app/modules/nas/router.py`

3. `WP-02` second implementation slice (task cancel/retry + lifecycle controls):
   - Extended NAS task schema/control fields:
     - `pending_files_json`, `retry_count`, `cancel_requested_at_ms`
     - status index for task query path
   - Added cancel/retry lifecycle persistence APIs in store:
     - `backend/services/nas_task_store.py`
   - Implemented task status transitions:
     - `pending -> running -> completed`
     - `pending/running -> canceling -> canceled`
     - `failed/canceled/completed(with failed files) -> pending (retry)`
   - Added NAS task control APIs:
     - `POST /api/nas/import-folder/{task_id}/cancel`
     - `POST /api/nas/import-folder/{task_id}/retry`
   - Added frontend action wiring in NAS page:
     - progress panel supports cancel/retry operations and status labels.
   - Added unit tests:
     - `backend/tests/test_nas_task_store_unit.py`
     - `backend/tests/test_nas_browser_service_unit.py` (task control cases)

## Validation Completed
- `python -m py_compile` passed for all modified backend files.
- `ensure_schema(...)` executed successfully on `data/auth.db`.
- `python -m unittest backend.tests.test_nas_browser_service_unit backend.tests.test_nas_task_store_unit` passed.
- `npm run build` (fronted) passed.

## Next Step (in order)
- Continue `WP-02`:
  - Extract a shared background task abstraction (upload/collect/plagiarism to converge on one task model).
  - Add cross-task queue policy and priority scheduling (beyond NAS scoped semaphore).
  - Add unified task list/query endpoint and metrics (failed rate/backlog/avg latency).
