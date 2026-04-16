# 审批矩阵到文控审批步骤的后端解析内核

- Task ID: `document-approval-matrix-json-20260415T203248`
- Created: `2026-04-15T20:32:48`
- Workspace: `D:\ProjectPackage\RagflowAuth`
- User Request: `实现审批矩阵到文控审批步骤的后端解析内核，基于 document-approval-matrix.json 与体系配置岗位分配生成文控审批链。`

## Goal

实现一个独立的后端矩阵解析服务，把审批矩阵 JSON 与体系配置岗位分配结合起来，解析某个文控文件在提交审批时应走的审批链，并输出清晰可冻结的解析快照。

## Scope

- 新增矩阵解析服务：
  - `backend/services/document_control/matrix_resolver.py`
- 新增或更新导出：
  - `backend/services/document_control/__init__.py`
- 新增定向单元测试：
  - `backend/tests/test_document_control_matrix_resolver_unit.py`

## Non-Goals

- 不在本任务中把解析器真正接入 `submit_revision_for_approval`
- 不修改前端
- 不重构通用 `operation_approval` 流程
- 不实现 `○` 的自动审批逻辑
- 不实现“根据使用区域”的自动条件判断

## Preconditions

- `docs/generated/document-approval-matrix.json` 可读取且为有效 JSON
- 体系配置岗位分配数据结构已存在，可作为 resolver 输入
- Python 测试环境可运行 `pytest`

缺少任一前提时，必须直接报错，不允许 fallback。

## Impacted Areas

- 文控服务后续接入点：
  - `backend/services/document_control/service.py`
- 审批矩阵主数据：
  - `docs/generated/document-approval-matrix.json`
- 体系配置岗位分配输出结构：
  - `backend/services/quality_system_config.py`

## Phase Plan

### P1: 实现矩阵解析器

- Objective:
  - 读取矩阵 JSON，结合岗位分配解析编制校验、审核会签步骤、批准步骤和快照
- Owned paths:
  - `backend/services/document_control/matrix_resolver.py`
  - `backend/services/document_control/__init__.py`
- Dependencies:
  - 审批矩阵 JSON
  - 岗位分配输入结构
- Deliverables:
  - 解析结果结构
  - 明确错误码

### P2: 为解析器补单元测试

- Objective:
  - 用定向单测覆盖核心规则和失败分支
- Owned paths:
  - `backend/tests/test_document_control_matrix_resolver_unit.py`
- Dependencies:
  - P1 完成
- Deliverables:
  - 至少 5 条覆盖规则的单元测试

## Phase Acceptance Criteria

### P1

- P1-AC1: 解析器能根据 `文件小类` 找到矩阵项，并输出 `compiler_check / signoff_steps / approval_steps / snapshot`
- P1-AC2: `编制` 只做岗位校验，不生成审批步骤
- P1-AC3: `审核会签` 只把 `●` 进入自动审批链，`○` 只保留在快照里
- P1-AC4: `批准` 作为最后一步输出
- P1-AC5: `编制人直接主管` 与 `文档管理员` 可被正确解析
- P1-AC6: 对矩阵缺失、文件小类缺失、岗位缺失、岗位无人、直属主管缺失给出明确错误码

### P2

- P2-AC1: 单测覆盖不同文件小类生成不同链路
- P2-AC2: 单测覆盖注册产品条件命中 / 未命中
- P2-AC3: 单测覆盖直属主管缺失
- P2-AC4: 单测覆盖岗位无人
- P2-AC5: 单测覆盖 `○` 不进入自动审批链

Evidence expectation:

- `execution-log.md` 记录修改文件与测试命令
- `test-report.md` 记录测试结果与 acceptance 覆盖情况

## Done Definition

- P1 与 P2 全部完成
- 解析器代码可导入
- 定向单测通过
- 所有 acceptance id 均有对应证据

## Blocking Conditions

- 矩阵 JSON 不存在或格式无效
- 岗位分配结构无法读取到岗位名与已分配用户
- Python 测试环境不可用
