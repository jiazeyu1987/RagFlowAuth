# Backup Lock Bug Fix

## Issue
备份完成后显示 "备份任务已被其他进程占用"，无法再次启动备份。

## Root Cause
`DataSecurityStore._release_lock()` 方法检查 `owner` 字段：
```python
conn.execute("DELETE FROM backup_locks WHERE name = ? AND owner = ?", (name, self._lock_owner))
```

问题：
- 主线程创建锁时使用 `store._lock_owner = "instance_id_1"`
- Worker线程调用 `release_backup_lock()` 时创建新的 store 实例，`_lock_owner = "instance_id_2"`
- Owner 不匹配，锁不会被删除
- 导致后续备份请求被拒绝

## Solution
修改 `_release_lock()` 方法，移除 owner 检查：
```python
conn.execute("DELETE FROM backup_locks WHERE name = ?", (name,))
```

## Files Modified
- `backend/services/data_security/store.py` - Line 66

## Date
2026-01-26

## Verification
1. 启动备份 → 任务完成
2. 再次点击"立即备份" → 应该正常启动（不再提示占用）
