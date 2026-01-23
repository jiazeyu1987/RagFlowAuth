# RagflowAuth 数据恢复指南

## 快速恢复（推荐）

使用自动化恢复脚本：

```powershell
# 恢复最新的备份
cd D:\scripts
.\Restore-RagflowBackup.ps1

# 或者恢复指定的备份
.\Restore-RagflowBackup.ps1 -BackupPath "D:\datas\migration_pack_20260123_045023"
```

脚本会自动：
1. 上传备份到服务器
2. 恢复 auth.db
3. 恢复所有 RAGFlow volumes
4. 验证恢复结果

---

## 手动恢复步骤

如果自动脚本失败，可以按以下步骤手动恢复：

### 1. 上传备份到服务器

```powershell
scp -r "D:\datas\migration_pack_20260123_045023" root@172.30.30.57:/opt/ragflowauth/data/backups/
```

### 2. 恢复 auth.db

```bash
ssh root@172.30.30.57
cp /opt/ragflowauth/data/backups/migration_pack_20260123_045023/auth.db /opt/ragflowauth/data/auth.db
```

### 3. 恢复 RAGFlow volumes

对于每个 volume 文件（如 `ragflow_compose_mysql_data_20260123_045025.tar.gz`）：

```bash
# 恢复 MySQL 数据
docker run --rm \
  -v ragflow_compose_mysql_data:/volume_data \
  -v /opt/ragflowauth/data/backups/migration_pack_20260123_045023/ragflow/volumes:/backup:ro \
  ragflowauth-backend:local \
  sh -c "rm -rf /volume_data/* /volume_data/.??* 2>/dev/null; tar -xzf /backup/ragflow_compose_mysql_data_20260123_045025.tar.gz -C /volume_data"

# 恢复 Elasticsearch 数据
docker run --rm \
  -v ragflow_compose_esdata01:/volume_data \
  -v /opt/ragflowauth/data/backups/migration_pack_20260123_045023/ragflow/volumes:/backup:ro \
  ragflowauth-backend:local \
  sh -c "rm -rf /volume_data/* /volume_data/.??* 2>/dev/null; tar -xzf /backup/ragflow_compose_esdata01_20260123_045023.tar.gz -C /volume_data"

# 恢复 MinIO 数据
docker run --rm \
  -v ragflow_compose_minio_data:/volume_data \
  -v /opt/ragflowauth/data/backups/migration_pack_20260123_045023/ragflow/volumes:/backup:ro \
  ragflowauth-backend:local \
  sh -c "rm -rf /volume_data/* /volume_data/.??* 2>/dev/null; tar -xzf /backup/ragflow_compose_minio_data_20260123_045024.tar.gz -C /volume_data"

# 恢复 Redis 数据
docker run --rm \
  -v ragflow_compose_redis_data:/volume_data \
  -v /opt/ragflowauth/data/backups/migration_pack_20260123_045023/ragflow/volumes:/backup:ro \
  ragflowauth-backend:local \
  sh -c "rm -rf /volume_data/* /volume_data/.??* 2>/dev/null; tar -xzf /backup/ragflow_compose_redis_data_20260123_045030.tar.gz -C /volume_data"
```

### 4. 验证恢复

```bash
# 验证 auth.db
sqlite3 /opt/ragflowauth/data/auth.db ".tables"

# 验证 RAGFlow volumes
docker volume ls | grep ragflow

# 重启 RAGFlow 服务
cd /opt/ragflowauth/ragflow_compose
docker compose restart
```

---

## 完整灾难恢复场景

### 场景：服务器完全宕机，需要在新服务器上恢复

#### 步骤 1: 准备新服务器

```bash
# 1. 安装 Docker 和 Docker Compose
curl -fsSL https://get.docker.com | sh
usermod -aG docker root

# 2. 创建数据目录
mkdir -p /opt/ragflowauth/data
mkdir -p /opt/ragflowauth/ragflow_compose
```

#### 步骤 2: 上传备份和配置

```powershell
# 在 Windows 上执行
scp -r "D:\datas\migration_pack_20260123_045023" root@新服务器IP:/opt/ragflowauth/data/backups/
scp "D:\datas\migration_pack_20260123_045023\ragflow\docker-compose.yml" root@新服务器IP:/opt/ragflowauth/ragflow_compose/
```

#### 步骤 3: 恢复 auth.db

```bash
ssh root@新服务器IP
cp /opt/ragflowauth/data/backups/migration_pack_20260123_045023/auth.db /opt/ragflowauth/data/auth.db
```

#### 步骤 4: 创建并恢复 volumes

```bash
# 创建空的 volumes
docker volume create ragflow_compose_mysql_data
docker volume create ragflow_compose_esdata01
docker volume create ragflow_compose_minio_data
docker volume create ragflow_compose_redis_data

# 恢复数据（使用上面的命令）
```

#### 步骤 5: 拉取镜像并启动服务

```bash
cd /opt/ragflowauth/ragflow_compose
docker compose pull
docker compose up -d
```

#### 步骤 6: 部署 RagflowAuth

```powershell
cd D:\ProjectPackage\RagflowAuth\tool
.\deploy.ps1 -SkipBuild
```

---

## 常见问题

### Q: 恢复后 RAGFlow 服务无法启动？

A: 检查 volume 权限：

```bash
# 检查 volume 内容
docker run --rm -v ragflow_compose_mysql_data:/data alpine ls -la /data

# 如果需要，修复权限
docker run --rm -v ragflow_compose_mysql_data:/data alpine chown -R 999:999 /data
```

### Q: 如何只恢复 auth.db？

```bash
ssh root@172.30.30.57
cp /opt/ragflowauth/data/backups/migration_pack_YYYYMMDD_HHMMSS/auth.db /opt/ragflowauth/data/auth.db
docker restart ragflowauth-backend
```

### Q: 如何只恢复 RAGFlow 数据？

参考上面的"步骤 3"中的命令，只恢复需要的 volume。

### Q: 恢复后数据丢失或不完整？

```bash
# 检查备份完整性
cat /opt/ragflowauth/data/backups/migration_pack_*/manifest.json

# 检查 volume 备份文件
ls -lh /opt/ragflowauth/data/backups/migration_pack_*/ragflow/volumes/
```

---

## 备份文件说明

### manifest.json
包含备份元数据：
- `created_at`: 备份创建时间
- `contains`: 备份内容（auth.db, ragflow）
- `ragflow.volume_archives`: volume 文件列表
- `ragflow.images_note`: 镜像说明（不包含镜像，需从仓库拉取）

### 目录结构
```
migration_pack_YYYYMMDD_HHMMSS/
├── auth.db                          # RagflowAuth 数据库
├── manifest.json                    # 备份元数据
└── ragflow/
    ├── docker-compose.yml           # RAGFlow 配置
    ├── volumes/                     # Docker volumes 备份
    │   ├── ragflow_compose_esdata01_*.tar.gz
    │   ├── ragflow_compose_mysql_data_*.tar.gz
    │   ├── ragflow_compose_minio_data_*.tar.gz
    │   └── ragflow_compose_redis_data_*.tar.gz
    └── images/                      # 空（镜像已禁用导出）
```

---

## 定期恢复测试建议

建议每月测试一次恢复流程，确保备份可用：

1. 在测试环境中恢复最新备份
2. 验证 auth.db 数据完整性
3. 验证 RAGFlow 服务正常运行
4. 检查数据完整性

---

## 联系支持

如遇问题，请提供以下信息：
- 备份文件名和创建时间
- 错误日志（`D:\scripts\backup-restore.log`）
- 服务器状态（`docker ps -a`）
