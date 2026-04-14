# 电子签名责任与授权矩阵

版本: v1.0
更新时间: 2026-04-14

## 1. 目的

定义 FDA-01 在仓库内的责任闭环：谁可以签、何时可以签、系统如何阻断未授权签名，以及哪些证据仍需线下归档。

## 2. 授权矩阵

| 业务动作 | 路由/模块 | 允许签名人 | 关键系统校验 | 关键证据 |
|---|---|---|---|---|
| 审批步骤通过 | `backend/app/modules/operation_approvals/router.py` | 当前步骤被授权审批人 | `operation_request_not_current_approver`、`signature_context_user_mismatch`、`signature_user_disabled`、`signature_user_inactive` | `backend.tests.test_operation_approval_service_unit.py`, `backend.tests.test_electronic_signature_unit.py` |
| 审批步骤驳回 | `backend/app/modules/operation_approvals/router.py` | 当前步骤被授权审批人 | `operation_request_not_current_approver`、`signature_user_disabled`、`signature_user_inactive` | `backend.tests.test_operation_approval_service_unit.py` |
| 申请撤回 | `backend/services/operation_approval/service.py` | 申请人本人或管理员 | `operation_request_not_withdrawable`、`operation_request_withdraw_forbidden` | `backend.tests.test_operation_approval_service_unit.py` |

## 3. 签名责任字段

签名记录必须至少证明：

- 签名人
- 签名用户名
- 签名时间
- 目标动作
- 签名含义
- 签名原因
- 业务对象与签名前后状态

## 4. 仓库外残余项

- 离岗/转岗签名权限回收的 HR/QA 纸质记录
- 账号唯一性与禁共用培训签收
- 线下批准版责任矩阵
