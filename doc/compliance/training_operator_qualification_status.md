# 培训与操作员认证状态

版本: v1.0  
更新时间: 2026-04-03  
最后仓库复核日期: 2026-04-03  
下次仓库复核截止日期: 2026-10-03  
仓库内证据状态: complete  
仓库外证据状态: pending_archive  
Residual gap 边界: 线下培训签到、考试签字页、岗位资格矩阵、例外放行审批单仍需在仓库外受控体系归档。

## 1. 仓库内闭环

- `training_requirements`：维护 `requirement_code`、`controlled_action`、`curriculum_version`、复训周期与是否要求有效性评价。
- `training_records`：维护培训完成记录、培训结果、有效性评价结果、评价人和评价时间。
- `operator_certifications`：维护上岗认证结果、认证人、有效期和例外放行引用。
- 关键动作门禁：
  - `document_review`
  - `restore_drill_execute`

## 2. 当前受控动作

| requirement_code | controlled_action | 角色 | 当前 curriculum_version | 当前门禁 |
|---|---|---|---|---|
| TR-001 | `document_review` | reviewer | 2026.04 | 未培训、培训版本过期、有效性未通过、认证缺失或认证过期均阻断 |
| TR-002 | `restore_drill_execute` | admin | 2026.04 | 未培训、培训版本过期、有效性未通过、认证缺失或认证过期均阻断 |

## 3. 仓库外残余项

- 纸质或签字版培训签到表
- 纸质考试或实操考核签字页
- 岗位资格矩阵批准页
- 例外放行单和偏差批准记录
