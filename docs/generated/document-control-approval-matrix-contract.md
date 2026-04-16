# 文控审批矩阵接口契约

本文档描述当前仓库里“审批矩阵接入文控审批流”的后端/前端对接契约。数据库、接口和前端页面都以当前实现为准。

## 范围

- 文控创建文件时的 `file_subtype`
- 文控提交审批前的矩阵预览
- 文控提交审批后的审批实例快照
- 审批详情里的矩阵相关字段
- 关键错误码

## 术语

- `document_type`：文控文件的大类
- `file_subtype`：文控文件的小类，来自体系配置中的 active 文件小类
- `matrix_snapshot_json`：提交审批时冻结的审批矩阵解析快照
- `position_snapshot_json`：提交审批时冻结的岗位 -> 审批人展开结果

## 创建受控文件

接口：

- `POST /api/quality-system/doc-control/documents`

请求体：

- `doc_code: string`
- `title: string`
- `document_type: string`
- `file_subtype: string` 必填
- `target_kb_id: string`
- `product_name?: string`
- `registration_ref?: string` 可为空；仅在矩阵命中“注册”会签条件时参与解析
- `usage_scope?: string` 当前业务字段尚未进入文控表单；对于 HTML 备注为“根据使用区域”的文件小类，后端会先失败并提示缺少该前提
- `change_summary?: string`
- `file: binary`

说明：

- `file_subtype` 不能为空。
- `registration_ref` 允许为空，空值表示当前文档不触发“注册针对注册产品进行会签”。
- 若未在审批矩阵中配置该 `file_subtype`，后续矩阵预览和提交审批会失败。

## 矩阵预览

接口：

- `GET /api/quality-system/doc-control/revisions/{controlled_revision_id}/matrix-preview`

返回：

```json
{
  "file_subtype": "设计验证方案/报告",
  "compiler_check": {
    "position_name": "项目负责人",
    "matched": true,
    "matched_user_ids": ["u-submitter"]
  },
  "signoff_steps": [
    {
      "step_name": "cosign",
      "step_semantic": "signoff",
      "position_name": "QA",
      "matrix_mark": "●",
      "member_source": "position",
      "approvers": [
        {
          "user_id": "u-qa-1",
          "source": "position"
        }
      ]
    }
  ],
  "approval_steps": [
    {
      "step_name": "approve",
      "step_semantic": "approval",
      "position_name": "编制部门负责人或授权代表",
      "matrix_mark": "●",
      "member_source": "position",
      "approvers": [
        {
          "user_id": "u-approver-1",
          "source": "position"
        }
      ]
    }
  ],
  "snapshot": {
    "file_subtype": "设计验证方案/报告",
    "compiler_check": {
      "position_name": "项目负责人",
      "matched": true,
      "matched_user_ids": ["u-submitter"]
    },
    "signoff_steps": [],
    "approval_steps": [],
    "optional_positions": []
  },
  "position_snapshot": {
    "positions": {
      "QA": ["u-qa-1"],
      "编制部门负责人或授权代表": ["u-approver-1"]
    }
  }
}
```

字段说明：

- `compiler_check.position_name`：矩阵中的编制岗位
- `compiler_check.matched`：当前用户是否满足编制岗位
- `signoff_steps`：所有自动进入审批链的会签步骤
- `approval_steps`：最终批准步骤，顺序上始终位于最后
- `matrix_mark`：当前只会自动执行 `●`
- `member_source`：当前支持 `position` / `direct_manager`

## 提交审批

接口：

- `POST /api/quality-system/doc-control/revisions/{controlled_revision_id}/submit`

提交逻辑：

1. 读取当前 revision 所属 document 的 `file_subtype`
2. 调用审批矩阵解析器
3. 校验提交人是否满足 `compiler_check`
4. 生成审批步骤和审批人
5. 写入审批请求、矩阵快照、岗位快照

提交后 revision 关键字段：

- `status = "approval_in_progress"`
- `approval_request_id`
- `file_subtype`
- `matrix_snapshot_json`
- `position_snapshot_json`

对应的 `workflow_snapshot` 关键字段：

```json
{
  "name": "document_control_<document_type>_approval",
  "mode": "approval_matrix",
  "file_subtype": "设计验证方案/报告",
  "compiler_check": {
    "position_name": "项目负责人",
    "matched": true,
    "matched_user_ids": ["u-submitter"]
  },
  "matrix_snapshot": {},
  "position_snapshot": {},
  "steps": [
    {
      "step_name": "cosign",
      "step_semantic": "signoff",
      "position_name": "QA",
      "members": [
        {
          "user_id": "u-qa-1",
          "full_name": "QA Reviewer"
        }
      ]
    },
    {
      "step_name": "approve",
      "step_semantic": "approval",
      "position_name": "编制部门负责人或授权代表",
      "members": [
        {
          "user_id": "u-approver-1",
          "full_name": "Approver"
        }
      ]
    }
  ]
}
```

## 文控详情返回

文控详情接口返回的 document/revision 结构中，当前实现会带回：

- `document.file_subtype`
- `current_revision.file_subtype`
- `current_revision.matrix_snapshot`
- `current_revision.position_snapshot`

审批详情接口返回的 `workflow_snapshot.steps[]` 中，当前实现会带回：

- `step_name`
- `step_semantic`
- `position_name`
- `members[]`

前端可据此展示：

- 当前步骤属于会签还是批准
- 当前步骤对应岗位
- 当前步骤展开到的审批人

## matrix_snapshot_json 结构

`matrix_snapshot_json` 由解析器在提交审批时冻结，当前结构至少包含：

```json
{
  "file_subtype": "设计验证方案/报告",
  "compiler_check": {
    "position_name": "项目负责人",
    "matched": true,
    "matched_user_ids": ["u-submitter"]
  },
  "signoff_steps": [
    {
      "step_name": "cosign",
      "step_semantic": "signoff",
      "position_name": "QA",
      "matrix_mark": "●",
      "member_source": "position",
      "approvers": [
        {
          "user_id": "u-qa-1",
          "source": "position"
        }
      ]
    }
  ],
  "approval_steps": [
    {
      "step_name": "approve",
      "step_semantic": "approval",
      "position_name": "编制部门负责人或授权代表",
      "matrix_mark": "●",
      "member_source": "position",
      "approvers": [
        {
          "user_id": "u-approver-1",
          "source": "position"
        }
      ]
    }
  ],
  "optional_positions": [
    {
      "position_name": "检测中心",
      "matrix_mark": "○"
    }
  ]
}
```

## position_snapshot_json 结构

`position_snapshot_json` 用于冻结当次提交时的岗位展开结果，避免后续岗位配置变更影响历史审批实例。

当前结构：

```json
{
  "positions": {
    "QA": ["u-qa-1", "u-qa-2"],
    "文档管理员": ["u-doc-admin-1"],
    "编制部门负责人或授权代表": ["u-approver-1"]
  }
}
```

## 审计事件建议

当前文控生命周期审计使用：

- `action = "document_control_transition"`
- `source = "document_control"`

建议前端审计页重点展示：

- `event_type`
- `after.file_subtype`
- `after.current_approval_step_name`
- `meta.matrix_mode`

## 关键错误码

- `document_control_matrix_file_subtype_required`
- `document_control_matrix_file_subtype_not_found`
- `document_control_matrix_missing`
- `document_control_matrix_compiler_mismatch`
- `document_control_matrix_usage_scope_required`
- `document_control_matrix_position_missing:<position_name>`
- `document_control_matrix_position_unassigned:<position_name>`

## 已知边界

- 当前自动审批链只会执行矩阵中的 `●`
- `○` 仅保留在快照里，不会自动进入审批链
- “根据使用区域”当前只保留在快照里，不驱动自动分支
- “注册针对注册产品进行会签”当前以 `registration_ref` 是否为空作为触发条件
