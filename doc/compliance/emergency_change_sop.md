# 紧急变更 SOP

版本: v1.0  
更新时间: 2026-04-03  
适用范围: GBZ-02  
仓库外残余项: 真实紧急变更执行单、纸质授权签字版、培训签到和产品评审记录仍需在线下受控体系归档

## 1. 触发条件

- 已发布环境出现阻断业务、合规或数据完整性的高优先级缺陷
- 标准变更流程无法满足时效要求，但仍必须受控

## 2. 受控原则

- 紧急变更必须遵循“先授权后部署再复盘”
- 系统内必须落库并保留以下最小字段:
  - `authorization_basis`
  - `risk_assessment`
  - `risk_control`
  - `rollback_plan`
  - `training_notification_plan`
  - `post_review_summary`
  - `impact_assessment_summary`
  - `capa_actions`
  - `verification_summary`
- 未完成授权不得进入部署
- 未完成事后评审与 CAPA 不得关闭

## 3. 角色约束

- `requested_by_user_id`: 仅管理员可发起
- `authorizer_user_id`: 仅指定授权人可执行授权
- `reviewer_user_id`: 仅指定复盘人可完成关闭

## 4. 状态机

1. `requested`
2. `authorized`
3. `deployed`
4. `closed`

## 5. 记录要求

- 每次状态迁移均需记录动作人、时间和结构化动作详情
- 线下真实执行证据不得在仓库内伪造为已完成，只能在状态文档中保留为 residual gap
