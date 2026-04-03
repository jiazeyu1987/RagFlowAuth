# 恢复演练记录模板

> 本模板用于归档系统执行后的恢复演练证据。演练是否通过以系统生成状态为准，不允许人工直接填写 `success/failed` 代替校验结果。

## 1. 基本信息

- 演练编号 (`drill_id`):
- 演练日期:
- 执行人 (`executed_by`):
- 复核人:
- 恢复目标环境 (`restore_target`):

## 2. 关联备份任务

- 备份任务 ID (`job_id`):
- 备份目录 (`backup_path`):
- 备份任务登记 hash (`backup_hash`):
- 系统重算实际 hash (`actual_backup_hash`):
- 备份生成时间:

## 3. 系统校验结果

- 备份目录存在性:
- 必要文件存在性:
  - `auth.db`
  - `backup_settings.json`
- 提交 hash 与任务登记 hash 一致 (`hash_match`):
- 恢复后 `auth.db` 路径 (`restored_auth_db_path`):
- 恢复后 `auth.db` hash (`restored_auth_db_hash`):
- 源/恢复 `auth.db` 比对一致 (`compare_match`):
- 包校验状态 (`package_validation_status`):
- 验收状态 (`acceptance_status`):
- 最终结果 (`result`):

## 4. 备注与异常

- 操作备注 (`verification_notes`):
- 异常现象:
- 处置措施:
- 是否需要重做演练:

## 5. 归档附件

- `verification_report_json` 导出副本:
- 相关审计事件 ID:
- 截图/日志路径:

## 6. 接口录入示例

```json
{
  "job_id": 101,
  "backup_path": "/mnt/replica/RagflowAuth/migration_pack_20260402_010203",
  "backup_hash": "f4e0b3c7...",
  "restore_target": "qa-staging",
  "verification_notes": "执行恢复演练并归档结果"
}
```

## 7. 归档示例字段

```json
{
  "drill_id": "restore_drill_20260402_010203",
  "job_id": 101,
  "backup_hash": "f4e0b3c7...",
  "actual_backup_hash": "f4e0b3c7...",
  "hash_match": true,
  "restored_auth_db_path": "data/restore_drills/qa-staging/job_101_1711999999999/auth.db",
  "restored_auth_db_hash": "9f3a1c...",
  "compare_match": true,
  "package_validation_status": "passed",
  "acceptance_status": "passed",
  "result": "success"
}
```
