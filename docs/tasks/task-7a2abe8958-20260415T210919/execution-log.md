# Execution Log

- Task ID: `task-7a2abe8958-20260415T210919`
- Created: `2026-04-15T21:09:19`

## Phase Entries

### P1 (2026-04-15): 接入矩阵解析器到文控提交链

- Changed paths:
  - `backend/services/document_control/service.py`
  - `backend/services/document_control/models.py`
  - `backend/services/document_control/__init__.py`
- Notes:
  - `submit_revision_for_approval` 已改为调用矩阵解析器和体系配置岗位分配，自动生成审批实例步骤与审批人。
  - 不再在提交时依赖固定 `approver_user_ids` 来生成实例链路。
  - 生成的 `workflow_snapshot` 已带 `mode/file_subtype/matrix_snapshot/position_snapshot`。

### P2 (2026-04-15): 增加实例快照字段与回显

- Changed paths:
  - `backend/database/schema/document_control.py`
  - `backend/services/document_control/models.py`
  - `backend/services/document_control/service.py`
- Notes:
  - 为文控数据补充了 `file_subtype`。
  - 为 revision 补充了 `matrix_snapshot_json / position_snapshot_json` 写入与读取。
  - detail 侧可通过审批实例的 `workflow_snapshot` 读取矩阵相关信息。

### P3 (2026-04-15): 补服务/API测试并验证兼容

- Changed paths:
  - `backend/tests/test_document_control_service_unit.py`
  - `backend/tests/test_document_control_api_unit.py`
- Validation run:
  - `python -m compileall backend/services/document_control/service.py backend/tests/test_document_control_service_unit.py backend/tests/test_document_control_api_unit.py`
  - `pytest backend/tests/test_document_control_service_unit.py -q`
  - `pytest backend/tests/test_document_control_api_unit.py -q`
- Evidence refs:
  - `backend/tests/test_document_control_service_unit.py`
  - `backend/tests/test_document_control_api_unit.py`

## Outstanding Blockers

- None yet.
