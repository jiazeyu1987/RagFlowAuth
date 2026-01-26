# 自动复制功能实施完成总结

## 功能概述

已成功实现**备份完成后自动复制到局域网Windows机器**功能。该功能采用**宿主机挂载SMB共享 + Docker bind mount**方案，确保稳定性和原子性。

---

## 已完成的修改

### 后端修改

1. **数据库Schema** (`backend/database/schema/data_security.py`)
   - 新增 `add_replica_columns_to_data_security()` 函数
   - 添加三个字段：
     - `replica_enabled`: 是否启用自动复制
     - `replica_target_path`: 容器内目标路径
     - `replica_subdir_format`: 子目录格式（'flat' 或 'date'）

2. **数据库迁移注册** (`backend/database/schema/ensure.py`)
   - 导入 `add_replica_columns_to_data_security`
   - 在 `ensure_schema()` 中调用该迁移函数

3. **数据模型** (`backend/services/data_security/models.py`)
   - `DataSecuritySettings` dataclass 新增三个字段：
     - `replica_enabled: bool`
     - `replica_target_path: str | None`
     - `replica_subdir_format: str`

4. **数据存储层** (`backend/services/data_security/store.py`)
   - `get_settings()`: 从数据库读取复制配置
   - `update_settings()`: 允许更新复制配置（添加到 `allowed` 集合）

5. **复制服务** (`backend/services/data_security/replica_service.py`) **[新建]**
   - `BackupReplicaService` 类
   - `replicate_backup()`: 主复制方法
     - 原子性操作：临时目录 → 复制 → DONE标记 → 重命名
     - 支持两种子目录格式：flat 和 date
     - 错误处理：复制失败不影响备份状态
   - `_generate_subdir()`: 生成子目录路径
   - `_copy_directory()`: 递归复制目录（带进度更新）
   - `_write_replication_manifest()`: 写入复制清单文件

6. **备份服务** (`backend/services/data_security/backup_service.py`)
   - `run_job()`: 备份完成后自动调用复制服务
   - 进度更新：90%（备份完成）→ 92-97%（复制中）→ 100%（完成）
   - 错误处理：复制失败时更新消息为"备份完成（同步失败：xxx）"

7. **API路由** (`backend/app/modules/data_security/router.py`)
   - `GET /admin/data-security/settings`: 返回复制配置
   - `PUT /admin/data-security/settings`: 接受复制配置更新

### 前端修改

8. **数据安全页面** (`fronted/src/pages/DataSecurity.js`)
   - 新增"自动复制设置"Card（位于"备份设置"之后，"备份进度"之前）
   - UI组件：
     - 启用复选框：`replica_enabled`
     - 目标路径输入框：`replica_target_path`
     - 子目录格式下拉框：`replica_subdir_format`
     - 配置说明面板
   - 所有控件均添加 `data-testid` 属性以便测试

---

## 使用指南

### 第一步：Windows目标机器准备

1. **创建专用备份账号**
   - 在Windows机器上创建用户 `backup_user`
   - 设置强密码

2. **创建共享文件夹**
   - 创建文件夹：`C:\Backups`
   - 右键 → "属性" → "共享" → "高级共享"
   - 勾选"共享此文件夹"
   - 权限 → 添加 `backup_user`，勾选"完全控制"

3. **配置防火墙**
   ```powershell
   # 管理员PowerShell
   Enable-NetFirewallRule -DisplayGroup "File and Printer Sharing"
   ```

4. **验证共享**
   ```
   \\<Windows机器IP>\Backups
   ```

### 第二步：Linux宿主机挂载SMB共享

1. **安装cifs-utils**
   ```bash
   sudo apt-get update
   sudo apt-get install cifs-utils
   ```

2. **创建凭据文件**
   ```bash
   sudo mkdir -p /root/.smbcreds
   sudo nano /root/.smbcreds/ragflow_backup
   ```
   内容：
   ```
   username=backup_user
   password=<你的密码>
   domain=WORKGROUP
   ```
   设置权限：
   ```bash
   sudo chmod 600 /root/.smbcreds/ragflow_backup
   ```

3. **创建挂载点**
   ```bash
   sudo mkdir -p /mnt/replica
   ```

4. **测试挂载**
   ```bash
   sudo mount -t cifs //"<Windows机器IP>"/Backups /mnt/replica \
     -o credentials=/root/.smbcreds/ragflow_backup,iocharset=utf8,uid=1000,gid=1000,vers=3.0
   ```

5. **配置开机自动挂载**
   ```bash
   sudo nano /etc/fstab
   ```
   添加：
   ```
   //<Windows机器IP>/Backups /mnt/replica cifs \
     credentials=/root/.smbcreds/ragflow_backup,iocharset=utf8,uid=1000,gid=1000,vers=3.0,_netdev,nofail 0 0
   ```

### 第三步：Docker容器配置

在启动backend容器时添加bind mount：

```bash
docker run -d \
  --name ragflowauth-backend \
  -v /mnt/replica:/replica \
  ...其他参数...
```

### 第四步：前端配置

1. 访问数据安全页面：`http://<服务器IP>:3001/data-security`
2. 找到"自动复制设置"Card
3. 配置：
   - ✅ 勾选"启用自动复制"
   - **容器内目标路径**：`/replica/RagflowAuth`
   - **子目录格式**：
     - `flat`：平铺（所有备份在同一目录）
     - `date`：按日期分桶（YYYY/MM/DD）
4. 点击"保存设置"

### 第五步：测试

1. 点击"立即备份"或"立即全量备份"
2. 观察备份进度：
   - 0-90%：备份进行中
   - 92%：开始复制（临时目录）
   - 92-97%：复制文件
   - 97%：验证中
   - 100%：完成
3. 查看备份消息：
   - 成功：`备份完成（已同步）`
   - 失败：`备份完成（同步失败：<原因>）`
4. 验证目标机器：
   ```bash
   # 在宿主机上
   ls -la /mnt/replica/RagflowAuth/
   # 或者
   ls -la /mnt/replica/RagflowAuth/2025/01/25/
   ```
   应该能看到新的备份目录，且包含 `DONE` 标记文件和 `replication_manifest.json`

---

## 技术特性

### 原子性保证
- 复制到临时目录：`/replica/RagflowAuth/_tmp/job_<id>_<timestamp>/`
- 写入完成后创建 `DONE` 标记文件
- 原子性重命名到最终目录
- 避免目标机器看到半成品备份

### 错误处理
- **复制失败不影响备份状态**
- 备份始终标记为 `completed`
- 消息字段显示详细错误信息
- 便于监控和告警

### 进度跟踪
- 实时更新复制进度（92%-97%）
- 通过job message通知当前状态
- 支持前端实时显示

### 清单文件
每个复制的备份都包含 `replication_manifest.json`：
```json
{
  "pack_name": "migration_pack_20250125_183000",
  "replicated_at_ms": 1737790800000,
  "replicated_at": "2025-01-25T18:00:00",
  "job_id": 123,
  "source_hostname": "ragflow-server"
}
```

---

## 数据库迁移

数据库字段会在应用启动时自动添加（通过 `ensure_schema`）。无需手动执行SQL。

如需检查字段是否已添加：
```bash
sqlite3 data/auth.db "PRAGMA table_info(data_security_settings);"
```

应该能看到：
- `replica_enabled` (INTEGER, DEFAULT 0)
- `replica_target_path` (TEXT)
- `replica_subdir_format` (TEXT, DEFAULT 'flat')

---

## 故障排查

### 复制未触发
- 检查 `replica_enabled` 是否为 `true`
- 检查 `replica_target_path` 是否配置
- 查看后端日志：`docker logs ragflowauth-backend`

### 复制失败：权限不足
- 检查宿主机挂载点权限：`ls -la /mnt/replica`
- 检查容器内路径权限：`docker exec ragflowauth-backend ls -la /replica`
- 确保容器内进程有写权限

### 复制失败：目标路径不存在
- 检查容器是否正确bind mount：`docker inspect ragflowauth-backend | grep replica`
- 应该能看到：`"/mnt/replica:/replica"`

### 复制速度慢
- 检查网络带宽
- 考虑使用更快的网络（千兆以太网）
- 大文件复制可能需要较长时间

---

## 优势总结

✅ **简单稳定** - 容器内只需普通文件操作，无需处理SMB协议
✅ **无需额外依赖** - 不需要安装smbclient或smbprotocol
✅ **原子性保证** - 临时目录 + 重命名，避免半成品
✅ **失败容错** - 复制失败不影响本地备份
✅ **易于调试** - 可直接在宿主机和容器内查看
✅ **灵活性** - 支持平铺和按日期分桶两种模式

---

## 后续优化建议

1. **监控告警**：集成到监控系统，对复制失败发送告警
2. **断点续传**：对于超大备份，支持断点续传
3. **压缩传输**：在复制前压缩备份以减少网络传输
4. **多目标复制**：支持同时复制到多个目标位置
5. **复制验证**：复制完成后自动校验文件完整性

---

## 相关文档

- [完整实施计划](./backup_to_windows.md)
- [备份系统架构](../README.md)
- [Docker部署说明](../docker/DOCKER_DEPLOY.md)

---

**实施日期**：2025-01-25
**实施人员**：Claude Code
**版本**：v1.0.0
