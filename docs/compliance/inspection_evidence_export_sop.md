# 检查取证导出 SOP

版本: v1.0
更新时间: 2026-04-14
适用条目: FDA-02
人可读副本: CSV
便携格式: ZIP + JSON
仓库外残余项: 线下交付签收、检查员实际取证介质流转记录仍需在线下受控体系归档

## 1. 目的

在检查、稽查或内部取证场景下，系统必须能够导出可直接阅览的人可读副本，以及可跨系统留存和校验的便携格式副本，并对导出包完整性提供系统生成的摘要。

## 2. 受控导出入口

- 接口: `/api/audit/evidence-export`
- 权限: 当前实现仅管理员可调用；未授权访问必须返回明确拒绝。
- 过滤条件: 支持 `from_ms`、`to_ms`、`doc_id`、`actor`、`signature_id`、`request_id`、`event_type`、`filename`

## 3. 导出包组成

- `README.txt`
- `audit_events.json` / `audit_events.csv`
- `electronic_signatures.json` / `electronic_signatures.csv`
- `approval_actions.json` / `approval_actions.csv`
- `notification_jobs.json` / `notification_jobs.csv`
- `backup_jobs.json` / `backup_jobs.csv`
- `restore_drills.json` / `restore_drills.csv`
- `manifest.json`
- `checksums.json`

## 4. 记录副本定义

- 人可读副本: CSV 文件，便于检查员直接打开、打印或归档。
- 便携格式: ZIP 包内的 JSON 文件，适用于跨系统留存、机器复核和后续再处理。
- 完整性摘要: 由系统生成 `manifest.json` 与 `checksums.json`；检查时必须核对摘要，不得人工改写导出内容后继续作为通过证据。

## 5. 操作步骤

1. 管理员按检查范围调用 `/api/audit/evidence-export`。
2. 系统生成 ZIP 包，并返回导出包摘要。
3. 系统写入 `audit_evidence_export` 审计事件，留痕导出人、导出包名、包 hash、过滤条件和记录计数。
4. 检查员收到包后，先核对 `manifest.json` 与 `checksums.json`，再查看 CSV/JSON 内容。

## 6. 异常处置

- 无权限用户请求导出：拒绝导出，不生成取证包。
- 导出包缺文件或摘要不一致：该包不得作为检查取证通过证据，必须重新导出。
- 需要线下介质交付：线下交付签收必须在线下受控体系中补充归档，仓库内不伪造签收记录。
