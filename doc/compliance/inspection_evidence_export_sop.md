# 检查取证导出 SOP

版本: v1.0  
更新时间: 2026-04-02  
适用条目: FDA-02  
人可读副本: CSV  
便携格式: ZIP + JSON  
仓库外残余项: 线下交付签收、检查员实际取证介质流转记录仍需在线下受控体系归档

## 1. 目的

在检查、稽查或内部取证场景下，系统必须能够导出可直接阅览的人可读副本，以及可跨系统留存和校验的便携格式副本，并对导出包完整性提供系统生成的摘要。

## 2. 受控导出入口

- 接口: `/api/audit/evidence-export`
- 权限: 仅管理员可调用；非管理员必须返回 `403 admin_required`
- 过滤条件: 支持 `from_ms`、`to_ms`、`doc_id`、`actor`、`signature_id`、`request_id`、`event_type`、`filename`

## 3. 导出包组成

- `README.txt`
  说明导出时间、导出人、过滤条件、记录副本定义和分项计数。
- `audit_events.json` / `audit_events.csv`
  审计日志副本，覆盖动作、操作者、组织信息、事件类型、原因、签名关联、请求 ID、hash 链等字段。
- `electronic_signatures.json` / `electronic_signatures.csv`
  电子签名副本，覆盖签名人、含义、原因、签名时间、record hash、signature hash。
- `approval_actions.json` / `approval_actions.csv`
  审批动作副本，覆盖实例、步骤、动作、操作者、备注和时间。
- `notification_jobs.json` / `notification_jobs.csv`
  通知任务与投递回执副本，覆盖接收人、通道、payload、重试状态、delivery logs。
- `backup_jobs.json` / `backup_jobs.csv`
  备份任务副本，覆盖 package hash、复制状态、验证状态和最后一次恢复演练关联。
- `restore_drills.json` / `restore_drills.csv`
  恢复演练副本，覆盖 backup hash、实际 hash、比对结果、验收状态和验证报告。
- `manifest.json`
  系统生成的导出包清单，列出各文件 `sha256`、`size_bytes`、计数和导出元数据。
- `checksums.json`
  从 `manifest.json` 派生的完整性摘要，供检查员快速核对单文件摘要。

## 4. 记录副本定义

- 人可读副本:
  CSV 文件，便于检查员直接打开、打印或归档。
- 便携格式:
  ZIP 包内的 JSON 文件，适用于跨系统留存、机器复核和后续再处理。
- 完整性摘要:
  由系统生成 `manifest.json` 与 `checksums.json`；检查时必须核对摘要，不得人工改写导出内容后继续作为通过证据。

## 5. 操作步骤

1. 管理员按检查范围调用 `/api/audit/evidence-export`。
2. 系统生成 ZIP 包，并在响应头中返回 `X-Evidence-Package-Sha256`。
3. 系统写入 `audit_evidence_export` 审计事件，留痕导出人、导出包名、包 hash、过滤条件和记录计数。
4. 检查员收到包后，先核对 `X-Evidence-Package-Sha256`、`manifest.json` 与 `checksums.json`，再查看 CSV/JSON 内容。

## 6. 异常处置

- 无权限用户请求导出:
  拒绝导出，不生成取证包。
- 导出包缺文件或摘要不一致:
  该包不得作为检查取证通过证据，必须重新导出。
- 需要线下介质交付:
  线下交付签收必须在线下受控体系中补充归档，仓库内不伪造签收记录。
