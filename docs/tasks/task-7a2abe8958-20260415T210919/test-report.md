# Test Report

- Task ID: `task-7a2abe8958-20260415T210919`
- Created: `2026-04-15T21:09:19`
- Workspace: `D:\ProjectPackage\RagflowAuth`
- User Request: `把文控提交审批改造成由审批矩阵自动生成审批实例，接入矩阵解析器并写入快照字段。`

## Environment Used

- Evaluation mode: blind-first-pass
- Validation surface: real-runtime
- Tools: python, pytest
- Initial readable artifacts: prd.md, test-plan.md
- Initial withheld artifacts: execution-log.md, task-state.json
- Initial verdict before withheld inspection: yes

## Results

### T1: 提交后实例步骤正确

- Result: passed
- Covers: P1-AC1, P1-AC3, P1-AC4, P3-AC1, P3-AC5
- Command run: `pytest backend/tests/test_document_control_service_unit.py -q`
- Environment proof: `backend/tests/test_document_control_service_unit.py`
- Evidence refs: `backend/tests/test_document_control_service_unit.py`
- Notes: 提交后审批链由矩阵生成，批准步骤位于最后。

### T2: 快照写入正确

- Result: passed
- Covers: P2-AC1, P2-AC2, P2-AC3, P3-AC2
- Command run: `pytest backend/tests/test_document_control_service_unit.py -q`
- Environment proof: `backend/tests/test_document_control_service_unit.py`
- Evidence refs: `backend/tests/test_document_control_service_unit.py`
- Notes: revision 中已可读取 `file_subtype / matrix_snapshot / position_snapshot`。

### T3: 编制岗位不匹配时报错

- Result: passed
- Covers: P1-AC2, P3-AC3
- Command run: `pytest backend/tests/test_document_control_service_unit.py -q`
- Environment proof: `backend/tests/test_document_control_service_unit.py`
- Evidence refs: `backend/tests/test_document_control_service_unit.py`
- Notes: 返回错误码 `document_control_matrix_compiler_mismatch`。

### T4: 岗位无人时报错

- Result: passed
- Covers: P3-AC4
- Command run: `pytest backend/tests/test_document_control_service_unit.py -q`
- Environment proof: `backend/tests/test_document_control_service_unit.py`
- Evidence refs: `backend/tests/test_document_control_service_unit.py`
- Notes: 返回错误码 `document_control_matrix_position_unassigned:QA`。

### T5: 历史实例读取兼容

- Result: passed
- Covers: P2-AC5
- Command run: `pytest backend/tests/test_document_control_api_unit.py -q`
- Environment proof: `backend/tests/test_document_control_api_unit.py`
- Evidence refs: `backend/tests/test_document_control_api_unit.py`
- Notes: 现有文控 API 查询与审批相关测试全部通过，说明旧读取路径未被破坏。

### T6: 审批详情带出矩阵信息

- Result: passed
- Covers: P2-AC4
- Command run: `pytest backend/tests/test_document_control_service_unit.py -q`
- Environment proof: `backend/tests/test_document_control_service_unit.py`
- Evidence refs: `backend/tests/test_document_control_service_unit.py`
- Notes: 提交后可从审批请求的 `workflow_snapshot` 中读取 `mode/file_subtype/matrix_snapshot/position_snapshot`。

## Final Verdict

- Outcome: passed
- Verified acceptance ids: P1-AC1, P1-AC2, P1-AC3, P1-AC4, P2-AC1, P2-AC2, P2-AC3, P2-AC4, P2-AC5, P3-AC1, P3-AC2, P3-AC3, P3-AC4, P3-AC5
- Blocking prerequisites:
- Summary: 文控提交审批已切换为矩阵驱动实例生成，revision 已写入矩阵快照，现有服务/API定向测试保持通过。

## Open Issues

- None yet.
