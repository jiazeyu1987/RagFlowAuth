# 变更控制 SOP

版本: v1.1  
更新时间: 2026-04-03

## 1. 触发条件

- 需求变更
- 缺陷修复
- 第三方组件升级
- 配置策略调整

## 2. 标准流程

1. 提出变更申请，说明范围、原因、风险、回滚方案。
2. 评估对 `R1-R10` 和 `FDA/GBZ` 合规条目的影响及所需测试。
3. 实施代码或配置变更。
4. 执行对应自动化测试和必要文档更新。
5. 由 QA/合规复核证据。
6. 批准后发布，并保留发布记录。

## 3. 紧急变更流程

- 紧急变更必须先授权，后部署，再补齐事后评审。
- 紧急变更最少需要记录 `authorization_basis`、`risk_assessment`、`risk_control`、`rollback_plan`、`training_notification_plan`。
- 关闭前必须补齐 `post_review_summary`、`impact_assessment_summary`、`capa_actions`、`verification_summary`。
- 未完成授权不得部署，未完成事后评审不得关闭。

## 4. 最低要求

- 不允许未经验证直接上线。
- 不允许以回退兼容逻辑替代明确缺陷修复，除非变更单明确批准。
