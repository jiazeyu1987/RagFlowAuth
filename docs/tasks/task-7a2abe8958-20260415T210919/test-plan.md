# Test Plan: 文控矩阵驱动提交审批

- Task ID: `task-7a2abe8958-20260415T210919`
- Created: `2026-04-15T21:09:19`
- Workspace: `D:\ProjectPackage\RagflowAuth`
- User Request: `把文控提交审批改造成由审批矩阵自动生成审批实例，接入矩阵解析器并写入快照字段。`

## Test Scope

验证文控提交审批链路是否：

- 使用矩阵解析结果生成审批实例
- 写入 `file_subtype / matrix_snapshot / position_snapshot`
- 保持旧实例读取与现有审批动作兼容

本次不验证：

- 前端矩阵展示
- 真正按业务 UI 选择文件小类的流程

## Environment

- OS: Windows
- Repo: `D:\ProjectPackage\RagflowAuth`
- pytest 可运行

## Accounts and Fixtures

- 使用文控服务/API测试中的测试矩阵 JSON
- 使用文控服务/API测试中的岗位分配假数据

## Commands

1. 语法校验

```powershell
python -m compileall backend/services/document_control/service.py backend/tests/test_document_control_service_unit.py backend/tests/test_document_control_api_unit.py
```

Expected: 编译成功，无语法错误。

2. 文控服务单测

```powershell
pytest backend/tests/test_document_control_service_unit.py -q
```

Expected: 全部通过。

3. 文控 API 单测

```powershell
pytest backend/tests/test_document_control_api_unit.py -q
```

Expected: 全部通过。

## Test Cases

### T1: 提交后实例步骤正确

- Covers: P1-AC1, P1-AC3, P1-AC4, P3-AC1, P3-AC5
- Level: unit
- Command: `pytest backend/tests/test_document_control_service_unit.py -q`
- Expected: 提交后实例步骤由矩阵生成，批准步骤位于最后。

### T2: 快照写入正确

- Covers: P2-AC1, P2-AC2, P2-AC3, P3-AC2
- Level: unit
- Command: `pytest backend/tests/test_document_control_service_unit.py -q`
- Expected: revision 中可读到 `file_subtype / matrix_snapshot / position_snapshot`。

### T3: 编制岗位不匹配时报错

- Covers: P1-AC2, P3-AC3
- Level: unit
- Command: `pytest backend/tests/test_document_control_service_unit.py -q`
- Expected: 返回 `document_control_matrix_compiler_mismatch`。

### T4: 岗位无人时报错

- Covers: P3-AC4
- Level: unit
- Command: `pytest backend/tests/test_document_control_service_unit.py -q`
- Expected: 返回 `document_control_matrix_position_unassigned:<岗位名>`。

### T5: 历史实例读取兼容

- Covers: P2-AC5
- Level: unit
- Command: `pytest backend/tests/test_document_control_api_unit.py -q`
- Expected: 现有文控查询和审批接口依旧可用，不因新增快照字段而损坏。

### T6: 审批详情带出矩阵信息

- Covers: P2-AC4
- Level: unit
- Command: `pytest backend/tests/test_document_control_api_unit.py -q`
- Expected: request detail 或相关回显结构中可访问 `workflow_snapshot` 内的矩阵信息。

## Coverage Matrix

| Case ID | Area | Scenario | Level | Acceptance IDs | Evidence |
| --- | --- | --- | --- | --- | --- |
| T1 | document_control service | 矩阵驱动生成实例步骤 | unit | P1-AC1, P1-AC3, P1-AC4, P3-AC1, P3-AC5 | `backend/tests/test_document_control_service_unit.py` |
| T2 | document_control service | 快照写入 | unit | P2-AC1, P2-AC2, P2-AC3, P3-AC2 | `backend/tests/test_document_control_service_unit.py` |
| T3 | document_control service | 编制岗位校验失败 | unit | P1-AC2, P3-AC3 | `backend/tests/test_document_control_service_unit.py` |
| T4 | document_control service | 岗位无人 | unit | P3-AC4 | `backend/tests/test_document_control_service_unit.py` |
| T5 | document_control api | 历史实例/现有接口兼容 | unit | P2-AC5 | `backend/tests/test_document_control_api_unit.py` |
| T6 | document_control api | 审批详情矩阵信息 | unit | P2-AC4 | `backend/tests/test_document_control_api_unit.py` |

## Evaluator Independence

- Mode: blind-first-pass
- Validation surface: real-runtime
- Required tools: pytest
- First-pass readable artifacts: prd.md, test-plan.md
- Withheld artifacts: execution-log.md, task-state.json
- Real environment expectation: 在真实仓库中运行文控服务/API单测，验证提交流程、快照和兼容性。
- Escalation rule: 在初次结论前不查看 `execution-log.md` 与 `task-state.json`。

## Pass / Fail Criteria

- Pass when:
  - 编译通过
  - 文控服务/API测试通过
- Fail when:
  - 提交审批仍依赖旧固定 approver 链
  - 快照字段缺失或读取失败
  - 现有查询/审批接口被破坏

## Regression Scope

- `backend/services/document_control/models.py`
- `backend/database/schema/document_control.py`
- `backend/app/modules/document_control/router.py`

## Reporting Notes

将命令、结果与 acceptance 覆盖情况写入 `test-report.md`。
