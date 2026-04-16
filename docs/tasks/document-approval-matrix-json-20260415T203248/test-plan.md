# Test Plan: 审批矩阵后端解析内核

- Task ID: `document-approval-matrix-json-20260415T203248`
- Created: `2026-04-15T20:32:48`
- Workspace: `D:\ProjectPackage\RagflowAuth`
- User Request: `实现审批矩阵到文控审批步骤的后端解析内核，基于 document-approval-matrix.json 与体系配置岗位分配生成文控审批链。`

## Test Scope

验证矩阵解析器是否能：

- 正确读取审批矩阵 JSON
- 根据文件小类生成不同审批链
- 正确处理编制校验、审核会签、批准步骤
- 正确处理注册条件、直属主管、岗位无人和 `○` 标记

本次不验证：

- 文控提交审批入口是否已接入解析器
- 前端页面展示

## Environment

- OS: Windows
- Repo: `D:\ProjectPackage\RagflowAuth`
- Python + pytest 可用

## Accounts and Fixtures

- 使用测试内构造的矩阵 JSON 与岗位分配假数据
- 不依赖真实账号或真实服务

## Commands

1. 语法校验

```powershell
python -m compileall backend/services/document_control/matrix_resolver.py backend/tests/test_document_control_matrix_resolver_unit.py
```

Expected: 无语法错误并成功编译。

2. 定向单元测试

```powershell
pytest backend/tests/test_document_control_matrix_resolver_unit.py -q
```

Expected: 全部测试通过。

## Test Cases

### T1: 不同文件小类生成不同审批链

- Covers: P1-AC1, P2-AC1
- Level: unit
- Command: `pytest backend/tests/test_document_control_matrix_resolver_unit.py -q`
- Expected: 不同文件小类得到不同的 signoff / approval 步骤集合。

### T2: 注册产品条件命中与未命中

- Covers: P1-AC5, P2-AC2
- Level: unit
- Command: `pytest backend/tests/test_document_control_matrix_resolver_unit.py -q`
- Expected: `registration_ref` 为空时，“注册”岗位不进入自动链，仅在快照中以 skip 形式保留。

### T3: 直属主管缺失时报错

- Covers: P1-AC6, P2-AC3
- Level: unit
- Command: `pytest backend/tests/test_document_control_matrix_resolver_unit.py -q`
- Expected: 返回 `document_control_matrix_direct_manager_missing`。

### T4: 岗位无人时报错

- Covers: P1-AC6, P2-AC4
- Level: unit
- Command: `pytest backend/tests/test_document_control_matrix_resolver_unit.py -q`
- Expected: 返回 `document_control_matrix_position_unassigned:<岗位名>`。

### T5: `○` 不进入自动审批链

- Covers: P1-AC3, P2-AC5
- Level: unit
- Command: `pytest backend/tests/test_document_control_matrix_resolver_unit.py -q`
- Expected: `○` 岗位不出现在自动 signoff_steps 中，但在 snapshot 中保留并标记 `optional_mark`。

### T6: 编制仅校验且批准在最后一步

- Covers: P1-AC2, P1-AC4
- Level: unit
- Command: `pytest backend/tests/test_document_control_matrix_resolver_unit.py -q`
- Expected: 编制岗位只出现在 `compiler_check` 中，不出现在自动审批步骤中；批准岗位始终出现在 `approval_steps` 且位于最后。

## Coverage Matrix

| Case ID | Area | Scenario | Level | Acceptance IDs | Evidence |
| --- | --- | --- | --- | --- | --- |
| T1 | resolver | 不同文件小类生成不同链路 | unit | P1-AC1, P2-AC1 | `backend/tests/test_document_control_matrix_resolver_unit.py` |
| T2 | resolver | 注册条件命中/未命中 | unit | P1-AC5, P2-AC2 | `backend/tests/test_document_control_matrix_resolver_unit.py` |
| T3 | resolver | 直属主管缺失 | unit | P1-AC6, P2-AC3 | `backend/tests/test_document_control_matrix_resolver_unit.py` |
| T4 | resolver | 岗位无人 | unit | P1-AC6, P2-AC4 | `backend/tests/test_document_control_matrix_resolver_unit.py` |
| T5 | resolver | `○` 跳过自动链 | unit | P1-AC3, P2-AC5 | `backend/tests/test_document_control_matrix_resolver_unit.py` |
| T6 | resolver | 编制校验与批准顺序 | unit | P1-AC2, P1-AC4 | `backend/tests/test_document_control_matrix_resolver_unit.py` |

## Evaluator Independence

- Mode: blind-first-pass
- Validation surface: real-runtime
- Required tools: pytest
- First-pass readable artifacts: prd.md, test-plan.md
- Withheld artifacts: execution-log.md, task-state.json
- Real environment expectation: 在真实仓库中运行 Python 单元测试，直接验证解析器逻辑。
- Escalation rule: 在初次结论前不查看 `execution-log.md` 与 `task-state.json`。

## Pass / Fail Criteria

- Pass when:
  - 语法校验通过
  - 定向单测全部通过
- Fail when:
  - 任意 acceptance 对应的规则未实现
  - 单测失败或解析器无法导入

## Regression Scope

- `backend/services/document_control/__init__.py` 导出是否保持可用

## Reporting Notes

将命令、结果和 acceptance 覆盖情况写入 `test-report.md`。
