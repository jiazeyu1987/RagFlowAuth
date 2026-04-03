# Tenant DB Migration Plan

更新时间: 2026-04-02  
范围: `R9 不同公司对应不同数据库`（P4-1）

## 1. 目标
- 将当前单库 `data/auth.db` 拆分为公司维度数据库: `data/tenants/company_<company_id>/auth.db`。
- 确保不同公司在以下数据上物理隔离:
`users`、`kb_documents`、`audit_events`、`data_security_settings`。

## 2. 前置条件
- 源库存在且可读: `data/auth.db`。
- 源库中 `users.company_id` 已维护完整，且不存在无归属公司用户需要继续使用的场景。
- 停止写入流量（维护窗口执行），避免迁移期间产生增量不一致。

## 3. 执行步骤
1. 先做 dry-run，确认公司列表与目标路径:
```powershell
powershell -File scripts/migrate_single_db_to_tenant_dbs.ps1 -DryRun
```
2. 正式迁移:
```powershell
powershell -File scripts/migrate_single_db_to_tenant_dbs.ps1
```
3. 如需覆盖重跑（目标库已存在）:
```powershell
powershell -File scripts/migrate_single_db_to_tenant_dbs.ps1 -Force
```

## 4. 迁移规则
- 按 `users.company_id` 分组生成目标库。
- 每个公司库只保留本公司用户及其关联:
  - `users`（仅 company_id=当前公司）
  - `user_permission_groups`
  - `auth_login_sessions`
  - `kb_documents`
  - `download_logs` / `deletion_logs`
  - `chat_sessions`
  - `audit_events`（按 `company_id` 或 `actor` 清理）
- 将目标库 `data_security_settings.auth_db_path` 回写为本库绝对路径。

## 5. 验证步骤
1. 后端单测:
```powershell
python -m unittest backend.tests.test_tenant_db_isolation_unit
```
2. 核查不同公司库文件存在:
```powershell
Get-ChildItem data\\tenants -Recurse -Filter auth.db
```
3. 抽检 API（使用不同公司账号），确认跨公司不可见。

## 6. 回滚策略
- 保留迁移前单库文件快照（建议外部备份目录）。
- 回滚时停止服务，恢复 `data/auth.db` 与 `data/tenants/` 到迁移前状态。
- 回滚完成后执行:
```powershell
python -m backend ensure-schema --db-path data/auth.db
```
