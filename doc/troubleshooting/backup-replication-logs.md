# 备份复制日志查看指南

## 日志位置

备份复制的详细日志记录在 Docker 容器的日志中：

```bash
ssh root@172.30.30.57 "docker logs ragflowauth-backend --since '1 hour ago' | grep -E '\[REPLICATION|\[Step |\[Copy\]|\[Mount Check\]|\[Verify\]'"
```

## 日志格式说明

### 1. 复制开始标记

```
============================================================
[REPLICATION START] Job ID: 735, Pack: migration_pack_20260130_112629_496
============================================================
```

### 2. 步骤日志

每个步骤都有清晰的成功（✓）或失败（✗）标记：

```
[Step 0] Checking if replication is enabled...
[Step 0] ✓ Replication enabled

[Step 1] Getting target path...
[Step 1] ✓ Target path: /mnt/replica/RagflowAuth
[Step 1] ✓ Target path is absolute

[Step 2] Checking if target is mounted to Windows share...
[Step 2] ✗ FAILED: /mnt/replica/RagflowAuth is NOT a mounted CIFS share
[Step 2] Files will be copied to local disk, NOT to Windows share!
[Step 2] Please mount Windows share first:
[Step 2]   mount -t cifs //192.168.112.72/backup /mnt/replica -o username=...,password=...
```

### 3. 复制过程日志

```
[Copy] Starting: /opt/ragflowauth/backups/migration_pack_20260130_112629_496 -> /mnt/replica/RagflowAuth/_tmp/job_735_1769743597
[Copy] Created destination: /mnt/replica/RagflowAuth/_tmp/job_735_1769743597
[Copy] Total files to copy: 5
[Copy] Phase 1: Copying container-visible files...
[Copy] Phase 1 complete: 1 files copied
[Copy] Phase 2: Checking volumes on host...
[Copy] Phase 2: Copying volumes from host path...
[Copy] Phase 2 complete: volumes copied from host
[Copy] Phase 3: Using docker run to copy volumes...
[Copy] Phase 3: Found 4 volume files
[Copy] Phase 3 complete: 4 volume files copied via docker
[Copy] Complete: 5/5 files copied
```

### 4. 挂载检查日志

```
[Mount Check] Found CIFS mount: /mnt/replica (type: cifs)
[Mount Check] Target /mnt/replica/RagflowAuth is under CIFS mount
```

或失败时：

```
[Mount Check] No CIFS mount found for /mnt/replica/RagflowAuth
```

### 5. 验证日志

```
[Verify] Checking /mnt/replica/RagflowAuth/migration_pack_20260130_112629_496...
[Verify] ✓ Directory exists
[Verify] ✓ DONE marker exists
[Verify] ✓ Manifest exists
[Verify] ✓ auth.db exists (size: 344064 bytes)
[Verify] ✓ Pack: migration_pack_20260130_112629_496
[Verify] ✓ Replicated at: 2026-01-30T11:26:37.841001
[Verify] ✓ All checks passed
```

### 6. 成功/失败总结

**成功**：
```
============================================================
[REPLICATION SUCCESS] Job ID: 735
[REPLICATION SUCCESS] Target: /mnt/replica/RagflowAuth/migration_pack_20260130_112629_496
============================================================
```

**失败**：
```
[REPLICATION FAILED] Exception: /mnt/replica/RagflowAuth is not a mounted CIFS share
[REPLICATION FAILED] Job ID: 735
[REPLICATION FAILED] Error: Target path not mounted to Windows share
============================================================
```

## 常见问题诊断

### 问题 1: "目标路径未挂载到Windows共享"

**日志**：
```
[Step 2] ✗ FAILED: /mnt/replica/RagflowAuth is NOT a mounted CIFS share
```

**原因**：
- Windows共享没有挂载
- `/mnt/replica` 是本地目录，不是网络共享

**解决方案**：
```bash
# 挂载Windows共享
mount -t cifs //192.168.112.72/backup /mnt/replica \
  -o username=BJB110,password=showgood87,domain=.,uid=0,gid=0,rw

# 或使用工具中的"挂载 Windows 共享"按钮
```

### 问题 2: "复制目标路径必须是绝对路径"

**日志**：
```
[Step 1] ✗ FAILED: Target path is not absolute: relative/path
```

**原因**：
- 配置的复制目标路径不是绝对路径

**解决方案**：
- 在"数据安全"页面配置绝对路径：`/mnt/replica/RagflowAuth`

### 问题 3: 复制超时

**日志**：
```
[Copy] Phase 3 failed: timeout...
```

**原因**：
- 网络连接慢
- Windows共享响应慢

**解决方案**：
- 检查网络连接
- 检查Windows电脑是否开机

### 问题 4: 验证失败

**日志**：
```
[Verify] ✗ auth.db missing
[Verify] ✗ DONE marker missing
```

**原因**：
- 复制过程中出错
- 目标磁盘空间不足

**解决方案**：
- 检查Windows共享磁盘空间
- 查看完整错误日志

## 实时监控备份过程

```bash
# 实时查看日志
ssh root@172.30.30.57 "docker logs -f ragflowauth-backend | grep -E '\[REPLICATION|\[Step |\[Copy\]'"

# 或使用工具查看
# 1. 打开 tool.py
# 2. 点击"查看日志"按钮
# 3. 过滤 "REPLICATION" 或 "Step"
```

## 查看特定备份任务的日志

```bash
# 按任务ID过滤
ssh root@172.30.30.57 "docker logs ragflowauth-backend 2>&1 | grep -A 50 'Job ID: 735'"

# 按备份包名过滤
ssh root@172.30.30.57 "docker logs ragflowauth-backend 2>&1 | grep -A 50 'migration_pack_20260130_112629'"
```

## 日志级别

- `INFO` - 正常操作步骤（✓ 表示成功）
- `WARNING` - 警告但不影响功能（⚠ 表示警告）
- `ERROR` - 错误导致失败（✗ 表示失败）
- `DEBUG` - 详细调试信息（每10个文件记录一次进度）

## 最佳实践

1. **每次备份后查看日志**
   - 确认所有步骤都是 ✓ 状态
   - 检查是否有 ERROR 或 WARNING

2. **保存关键日志**
   ```bash
   # 导出备份日志到文件
   ssh root@172.30.30.57 "docker logs ragflowauth-backend --since '24 hours' > backup_logs.txt"
   ```

3. **定期检查挂载状态**
   - 使用"检查挂载状态"按钮
   - 或运行：`ssh root@172.30.30.57 "mount | grep replica"`

4. **监控磁盘空间**
   ```bash
   # Windows共享空间
   ssh root@172.30.30.57 "df -h /mnt/replica/"
   ```
