# 风险评估

版本: v1.0
更新时间: 2026-04-14

| 风险 ID | 风险描述 | 影响 | 控制措施 | 证据 |
|---|---|---|---|---|
| RA-001 | 管理员越权执行文件操作 | 高 | RBAC 收口、前端显隐、单测/E2E 回归 | `test_permission_resolver_admin_restrict_unit.py`, `rbac.*.spec.js` |
| RA-002 | 未授权用户查看文档或结果 | 高 | 统一权限校验、可见边界回归 | `test_knowledge_visibility_guard_unit.py` |
| RA-003 | 文档预览缺少身份标识 | 中 | 动态水印、受控预览标识 | `test_preview_watermark_unit.py`, `document.watermark.spec.js` |
| RA-004 | 审批流程绕过层级控制 | 高 | 审批工作流、状态机、接口校验 | `test_approval_workflow_unit.py`, `test_review_workflow_api_unit.py` |
| RA-005 | 审批消息未送达或不可追溯 | 中 | 邮件/钉钉适配器、失败重试、管理接口 | `test_notification_dispatch_unit.py`, `review.notification.spec.js` |
| RA-006 | 关键审批动作无法归因到个人 | 高 | 电子签名挑战、签名含义/原因、验签记录 | `test_electronic_signature_unit.py`, `review.signature.spec.js` |
| RA-007 | 审计记录字段不全或不可查询 | 高 | 扩展审计字段、统一日志入口、查询过滤 | `test_audit_trail_fields_unit.py`, `audit.logs.filters-combined.spec.js` |
| RA-008 | 不同公司数据串读 | 高 | 租户分库、tenant 路由、迁移脚本 | `test_tenant_db_isolation_unit.py`, `company.data-isolation.spec.js` |
| RA-009 | 备份包不可验证或恢复演练无证据 | 高 | `package_hash`、恢复演练表、SOP、演练模板 | `test_backup_restore_audit_unit.py`, `admin.data-security.restore-drill.spec.js` |
| RA-010 | GMP 合规资料、版本、基线或周期复核状态不一致，导致无法支撑审计与发布门禁 | 高 | 受控归档、版本链保留、配置变更原因与独立日志、GMP 基线文档、周期复核状态、R7 仓库内门禁脚本 | `backend/tests/test_r7_compliance_gate_unit.py`, `test_document_versioning_unit.py`, `test_config_change_log_unit.py`, `document.version-history.spec.js`, `admin.config-change-reason.spec.js`, `python scripts/validate_r7_repo_compliance.py` |

结论:

- `RA-001` 至 `RA-009` 由代码控制与自动化测试覆盖。
- `RA-010` 的仓库内缺口通过本次 R7 基线文档、周期复核状态和门禁脚本补齐。
- `RA-010` 仍保留仓库外 residual gap：线下签字版执行证据与真实环境周期复核记录需由 QA/合规在线下体系归档。
