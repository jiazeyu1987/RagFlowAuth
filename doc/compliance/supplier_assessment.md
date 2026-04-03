# 供应商与第三方组件评估

版本: v1.0  
更新时间: 2026-04-03  
适用范围: GBZ-04  
AVL: 系统以 `supplier_component_qualifications` 作为仓库内“已批准供应商/组件清单”数据源，记录 `component_code / supplier_name / approved_version / supplier_approval_status`。  
OTSS: 现成软件与第三方组件范围至少包括 `RAGFlow`、`ONLYOFFICE`、`SQLite`、邮件/钉钉通知通道，以及受控接口类组件。  
供应商审核: 通过 `supplier_audit_summary` 记录供应商尽调、批准状态、支持能力和是否需要现场审核；不能满足要求时应保持 `pending_review` 或 `rejected`。  
已知问题: 通过 `known_issue_review` 记录当前版本缺陷清单、影响评估、规避措施和是否接受当前版本。  
再确认触发: 当 `current_version != approved_version` 时，`qualification_status` 必须变为 `requalification_required`，并通过 `revalidation_trigger` 记录新版本迁移和再确认原因。  

## 1. 仓库内实现边界

- 组件/供应商主数据由 `backend/services/supplier_qualification.py` 维护。
- 管理员通过 `POST /api/supplier-qualifications/components` 维护组件确认基线。
- 新版本变化通过 `POST /api/supplier-qualifications/components/{component_code}/version-change` 触发再确认。
- 环境级 IQ/OQ/PQ 记录通过 `POST /api/supplier-qualifications/environment-records` 写入。

## 2. 最小确认字段

| 字段 | 说明 |
|---|---|
| `component_code` | 组件唯一标识 |
| `component_category` | `vendor_service / off_the_shelf_software / database / infrastructure / interface` |
| `deployment_scope` | `shared_service / tenant_database / server / workstation` |
| `current_version` | 当前运行版本 |
| `approved_version` | 已批准版本 |
| `supplier_approval_status` | `pending_review / approved / conditional / rejected` |
| `qualification_status` | `pending_review / approved / requalification_required / rejected` |
| `supplier_audit_summary` | 供应商审核/尽调摘要 |
| `known_issue_review` | 已知问题与影响评估 |
| `migration_plan_summary` | 版本迁移与回退计划 |
| `revalidation_trigger` | 触发再确认的原因 |

## 3. 当前纳入控制的典型组件

| 组件 | 类别 | 预期用途 | 当前仓库内控制点 |
|---|---|---|---|
| RAGFlow | `vendor_service` | 检索、问答、知识库能力 | 供应商评估、版本变更再确认、接口兼容性复核 |
| ONLYOFFICE | `off_the_shelf_software` | Office 文档受控预览 | 供应商测试套件评估、版本变更再确认、环境 IQ/OQ/PQ |
| SQLite | `database` | 租户鉴权、审计与备份存储 | 租户数据库版本批准、环境确认、升级再确认 |
| SMTP / 钉钉 | `interface` | 审批通知发送 | 供应商/通道配置评估、已知问题与兼容性复核 |

## 4. 仓库外残余项

- 线下供应商审核报告、现场审核记录和正式批准签字
- 供应商质量体系年度复评记录
- 真实生产环境的签字版 IQ/OQ/PQ 协议、报告和偏差关闭记录
- 资产/基础设施台账、校准记录和线下变更签字
