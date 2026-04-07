# 数据库结构说明

## 1. 生成依据

本文件基于以下两类真实来源整理：

- 代码中的 schema 定义：`backend/database/schema/*.py`
- 当前主库：`data/auth.db`

当前主库路径解析规则由 `backend/database/paths.py` 管理；多租户库路径由 `backend/database/tenant_paths.py` 推导。

## 2. 总体结构

当前 `data/auth.db` 体现出一个“单库承载多个业务域”的 SQLite 模型，主要业务域包括：

- 身份认证与会话
- 权限、组织与目录
- 知识库、文档与聊天
- 审批、通知与电子签名
- 数据安全与审计
- 合规扩展
- 专用工具与下载任务

## 3. 身份认证与会话

| 表 | 关键字段 | 说明 | 来源 |
| --- | --- | --- | --- |
| `users` | `user_id`, `username`, `role`, `status`, `company_id`, `department_id`, `managed_kb_root_node_id` | 用户主表，同时承载会话策略、密码策略、电子签名开关和 tenant 组织字段 | `users.py` |
| `password_history` | `user_id`, `password_hash`, `created_at_ms` | 最近密码历史，支撑密码重复检查 | `users.py` |
| `auth_login_sessions` | `session_id`, `user_id`, `refresh_jti`, `last_activity_at_ms`, `expires_at_ms` | 登录 session 与 refresh 关联表 | `auth_sessions.py` |

关系说明：

- `password_history.user_id -> users.user_id`
- `auth_login_sessions.user_id -> users.user_id`

## 4. 权限、组织与目录

| 表 | 关键字段 | 说明 | 来源 |
| --- | --- | --- | --- |
| `permission_groups` | `group_id`, `group_name`, `accessible_kbs`, `accessible_tools`, `can_upload`, `can_review` | 权限组主表，当前权限真相源之一 | `permission_groups.py` |
| `user_permission_groups` | `user_id`, `group_id`, `created_at_ms` | 用户与权限组多对多映射 | `permission_groups.py` |
| `permission_group_folders` | `folder_id`, `name`, `parent_id` | 权限组管理树 | `permission_group_folders.py` |
| `companies` | `company_id`, `name`, `source_key` | 组织中的公司节点 | `org_directory.py` |
| `departments` | `department_id`, `company_id`, `parent_department_id`, `path_name` | 部门树 | `org_directory.py` |
| `org_employees` | `employee_id`, `employee_user_id`, `company_id`, `department_id` | 员工目录与组织映射 | `org_directory.py` |
| `org_directory_audit_logs` | `entity_type`, `action`, `entity_id`, `actor_user_id` | 组织目录审计 | `org_directory.py` |
| `kb_directory_nodes` | `node_id`, `name`, `parent_id` | 知识库目录树节点 | `kb_directory.py` |
| `kb_directory_dataset_bindings` | `dataset_id`, `node_id` | RAGFlow 数据集到目录节点的绑定 | `kb_directory.py` |

关系说明：

- `user_permission_groups.user_id -> users.user_id`
- `user_permission_groups.group_id -> permission_groups.group_id`
- `departments.company_id -> companies.company_id`
- `org_employees.company_id -> companies.company_id`
- `org_employees.department_id -> departments.department_id`
- `kb_directory_dataset_bindings.node_id -> kb_directory_nodes.node_id`

## 5. 知识库、文档与聊天

| 表 | 关键字段 | 说明 | 来源 |
| --- | --- | --- | --- |
| `kb_documents` | `doc_id`, `filename`, `kb_dataset_id`, `logical_doc_id`, `version_no`, `effective_status` | 本地文档记录、版本链和归档字段 | `kb_documents.py` |
| `download_logs` | `doc_id`, `downloaded_by`, `kb_dataset_id`, `is_batch` | 下载审计 | `audit_logs.py` |
| `deletion_logs` | `doc_id`, `deleted_by`, `kb_dataset_id`, `ragflow_deleted` | 删除审计 | `audit_logs.py` |
| `search_configs` | `id`, `name`, `config_json` | 搜索配置 | `search_configs.py` |
| `upload_settings` | `key`, `value_json` | 上传扩展名等配置 | `upload_settings.py` |
| `chat_sessions` | `session_id`, `chat_id`, `user_id`, `is_deleted` | 聊天会话记录 | `chat_sessions.py` |
| `chat_ownerships` | `chat_id`, `created_by` | 聊天归属 | `chat_management.py` |
| `chat_message_sources` | `chat_id`, `session_id`, `content_hash`, `sources_json` | 聊天消息来源引用 | `chat_message_sources.py` |
| `approval_workflows` | `workflow_id`, `kb_ref`, `is_active` | 旧版文档审批流程主表 | `approval_workflow.py` |
| `approval_workflow_steps` | `workflow_id`, `step_no`, `approver_user_id`, `approver_role` | 旧版审批步骤 | `approval_workflow.py` |
| `document_approval_instances` | `instance_id`, `doc_id`, `workflow_id`, `status` | 旧版审批实例 | `approval_workflow.py` |
| `document_approval_actions` | `instance_id`, `step_no`, `action`, `actor` | 旧版审批动作 | `approval_workflow.py` |

说明：

- `kb_documents` 是当前本地受控文档记录的核心表。
- `approval_workflows` 这一组表与 `operation_approval_*` 新体系并存，属于需要专门梳理的迁移边界。

## 6. 审批、通知与电子签名

| 表 | 关键字段 | 说明 | 来源 |
| --- | --- | --- | --- |
| `operation_approval_workflows` | `operation_type`, `name`, `is_active` | 新版审批工作流定义 | `operation_approval.py` |
| `operation_approval_workflow_steps` | `workflow_step_id`, `operation_type`, `step_no`, `step_name` | 新版审批步骤 | `operation_approval.py` |
| `operation_approval_step_approvers` | `workflow_step_id`, `approver_user_id`, `member_type`, `member_ref` | 步骤审批人或成员映射 | `operation_approval.py` |
| `operation_approval_requests` | `request_id`, `operation_type`, `status`, `workflow_snapshot_json`, `company_id`, `department_id` | 审批请求主表 | `operation_approval.py` |
| `operation_approval_request_steps` | `request_step_id`, `request_id`, `step_no`, `status`, `approval_rule` | 请求展开后的步骤状态 | `operation_approval.py` |
| `operation_approval_request_step_approvers` | `request_step_id`, `approver_user_id`, `status`, `signature_id` | 具体审批动作人 | `operation_approval.py` |
| `operation_approval_events` | `request_id`, `event_type`, `actor_user_id`, `payload_json` | 审批事件流 | `operation_approval.py` |
| `operation_approval_artifacts` | `request_id`, `artifact_type`, `file_path`, `sha256` | 审批附件与产物 | `operation_approval.py` |
| `operation_approval_legacy_migrations` | `legacy_instance_id`, `request_id`, `source_db_path`, `status` | 旧审批实例迁移记录 | `operation_approval.py` |
| `notification_channels` | `channel_id`, `channel_type`, `enabled`, `config_json` | 通知渠道配置 | `notification.py` |
| `notification_jobs` | `job_id`, `event_type`, `status`, `recipient_user_id`, `dedupe_key` | 通知任务主表 | `notification.py` |
| `notification_delivery_logs` | `job_id`, `channel_id`, `status`, `attempted_at_ms` | 通知投递日志 | `notification.py` |
| `notification_event_rules` | `event_type`, `enabled_channel_types_json` | 事件到渠道的启用规则 | `notification.py` |
| `user_inbox_notifications` | `inbox_id`, `recipient_user_id`, `title`, `link_path`, `status` | 站内信/待办收件箱 | `operation_approval.py` |
| `electronic_signature_challenges` | `token_id`, `user_id`, `expires_at_ms`, `consumed_at_ms` | 电子签名 challenge token | `electronic_signatures.py` |
| `electronic_signatures` | `signature_id`, `record_type`, `record_id`, `signed_by`, `record_hash` | 电子签名记录 | `electronic_signatures.py` |

关系说明：

- 审批新体系围绕 `operation_approval_requests` 展开，事件、步骤、附件都围绕它关联。
- `user_inbox_notifications` 是站内信与待办统一收件箱。
- `electronic_signatures.signature_id` 会被审批动作和审计事件引用。

## 7. 数据安全、审计与运行控制

| 表 | 关键字段 | 说明 | 来源 |
| --- | --- | --- | --- |
| `data_security_settings` | `enabled`, `incremental_schedule`, `full_backup_schedule`, `replica_enabled` | 备份与复制策略配置 | `data_security.py` |
| `backup_jobs` | `status`, `kind`, `output_dir`, `verification_status`, `replication_status` | 备份作业执行记录 | `data_security.py` |
| `backup_locks` | `name`, `owner`, `job_id` | 备份互斥锁 | `data_security.py` |
| `restore_drills` | `drill_id`, `job_id`, `backup_hash`, `acceptance_status` | 恢复演练记录 | `restore_drills.py` |
| `audit_events` | `action`, `actor`, `resource_type`, `request_id`, `event_hash` | 审计主表 | `audit_logs.py` |
| `config_change_logs` | `config_domain`, `before_json`, `after_json`, `change_reason` | 配置修改日志 | `config_change_logs.py` |
| `watermark_policies` | `policy_id`, `text_template`, `opacity`, `rotation_deg`, `is_active` | 水印策略 | `watermark_policy.py` |

说明：

- `audit_events` 是跨业务域审计汇聚点。
- `config_change_logs` 与备份/通知/审批等配置变化的追踪有关。
- `backup_jobs` 字段已经覆盖校验、复制与恢复演练引用，说明该子系统相对成熟。

## 8. 合规与扩展业务

| 表 | 关键字段 | 说明 | 来源 |
| --- | --- | --- | --- |
| `emergency_changes` | `change_id`, `status`, `requested_by_user_id`, `authorized_by_user_id` | 紧急变更主表 | `emergency_changes.py` |
| `emergency_change_actions` | `change_id`, `action`, `actor_user_id`, `details_json` | 紧急变更动作记录 | `emergency_changes.py` |
| `supplier_component_qualifications` | `component_code`, `supplier_name`, `qualification_status` | 供应商组件资质 | `supplier_qualification.py` |
| `environment_qualification_records` | `record_id`, `component_code`, `environment_name`, `qualification_status` | 环境资质记录 | `supplier_qualification.py` |
| `training_requirements` | `requirement_code`, `role_code`, `controlled_action`, `active` | 培训要求定义 | `training_compliance.py` |
| `training_records` | `record_id`, `requirement_code`, `user_id`, `training_outcome` | 培训执行记录 | `training_compliance.py` |
| `operator_certifications` | `certification_id`, `requirement_code`, `user_id`, `certification_status` | 操作员资质 | `training_compliance.py` |

## 9. 专用工具与下载任务

| 表 | 关键字段 | 说明 | 依据 |
| --- | --- | --- | --- |
| `patent_download_sessions` | `session_id`, `created_by`, `keywords_json`, `status` | 专利下载任务会话 | `patent_downloads.py` |
| `patent_download_items` | `session_id`, `title`, `status`, `file_path`, `added_doc_id` | 专利下载结果项 | `patent_downloads.py` |
| `paper_download_sessions` | `session_id`, `created_by`, `keywords_json`, `status` | 论文下载任务会话 | `paper_downloads.py` |
| `paper_download_items` | `session_id`, `title`, `status`, `analysis_text`, `added_doc_id` | 论文下载结果项 | `paper_downloads.py` |
| `package_drawing_records` | `model`, `barcode`, `parameters_json` | 包装图纸主记录 | `package_drawings.py` |
| `package_drawing_images` | `image_id`, `model`, `source_type`, `image_url` | 包装图纸图片 | `package_drawings.py` |
| `nas_import_tasks` | `task_id`, `folder_path`, `kb_ref`, `status` | NAS 导入任务 | 运行库观察到，当前主库存在 |

说明：

- `nas_import_tasks` 已在 `data/auth.db` 中观察到，说明 NAS 导入会把任务持久化到主库。
- 下载会话与结果项通常还会和知识库文档表发生间接关联，例如 `added_doc_id`。

## 10. 当前 schema 观察

- 主库承载的业务域很多，说明它既是认证库，也是平台工作库。
- 旧审批链和新审批链并存，是当前 schema 最需要被持续标注的边界。
- `users` 表已经不只是账号表，还承载会话策略、tenant 组织信息和管理根节点等平台字段。
- 备份、通知、审批、培训等模块都已经有自己的持久化表，不应再被视作“临时功能”。

## 11. 使用建议

- 查权限问题：先看 `users`、`permission_groups`、`user_permission_groups`
- 查知识库目录问题：先看 `kb_directory_nodes`、`kb_directory_dataset_bindings`
- 查审批问题：优先看 `operation_approval_requests` 及其步骤/事件表
- 查通知问题：看 `notification_jobs`、`notification_delivery_logs`、`user_inbox_notifications`
- 查 backup 问题：看 `data_security_settings`、`backup_jobs`、`restore_drills`
