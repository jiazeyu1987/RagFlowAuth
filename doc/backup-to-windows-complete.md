# RagflowAuth 自动备份到 Windows - 完整配置文档

## ✅ 已完成配置

### 1. Windows 共享配置 ✅
- **共享路径**: `D:\datas`
- **网络路径**: `\\192.168.112.72\backup`
- **用户名**: BJB110
- **密码**: showgood87

### 2. Linux 服务器挂载 ✅
```bash
# 挂载命令（已执行）
mount -t cifs '//192.168.112.72/backup' /mnt/replica \
  -o 'credentials=/root/.smbcreds/ragflow_backup,iocharset=utf8,uid=0,gid=0,file_mode=0660,dir_mode=0770,vers=3.0,_netdev'
```

### 3. Docker 容器配置 ✅
```bash
# 容器挂载点
-v /mnt/replica:/replica
-v /opt/ragflowauth/backend/services/data_security:/app/backend/services/data_security
-v /opt/ragflowauth/backend/app/modules/data_security:/app/backend/app/modules/data_security
```

### 4. 数据库配置 ✅
```sql
replica_enabled = 1
replica_target_path = "/replica/RagflowAuth"
replica_subdir_format = "flat"
```

### 5. 锁释放修复 ✅
- 修改了 `_release_lock` 方法，移除 owner 检查
- 文件位置：`/opt/ragflowauth/backend/services/data_security/store.py`

### 6. 文件位置
- **主机代码**: `/opt/ragflowauth/backend/services/data_security/`
- **容器挂载**: `/app/backend/services/data_security/` (bind mount)

## ⚠️ 当前问题

### Worker 线程问题
**症状**:
- 备份任务卡在 "queued" 状态
- 点击"立即备份"后任务不会自动执行

**临时解决方案**:
```bash
# SSH 到服务器并执行
docker exec ragflowauth-backend /usr/local/bin/python << 'EOF'
from backend.app.modules.data_security.runner import start_job_if_idle
import sqlite3
conn = sqlite3.connect("/app/data/auth.db")
conn.execute("DELETE FROM backup_locks")
conn.commit()
job_id = start_job_if_idle(reason="手动")
print(f"Started job {job_id}")
EOF
```

### Volumes 备份问题
**症状**:
- 备份只包含 `auth.db`
- `volumes/` 目录为空，缺少 RAGFlow volumes

**根本原因**: Worker 线程问题导致备份无法完整执行

## 🔧 手动备份步骤（临时方案）

### 方案1: 通过容器直接备份
```bash
# 在服务器上执行
docker exec ragflowauth-backend /usr/local/bin/python << 'EOF'
from backend.services.data_security.store import DataSecurityStore
from backend.services.data_security.backup_service import DataSecurityBackupService

store = DataSecurityStore()
job = store.create_job_v2(kind='incremental', status='running', message='手动备份')
print(f"Started job {job.id}")

svc = DataSecurityBackupService(store)
svc.run_incremental_backup_job(job.id)

job = store.get_job(job.id)
print(f"Status: {job.status}")
print(f"Output: {job.output_dir}")
EOF
```

### 方案2: 手动复制 Volumes
```bash
# 备份每个 RAGFlow volume
for vol in ragflow_compose_esdata01 ragflow_compose_minio_data ragflow_compose_mysql_data ragflow_compose_redis_data; do
  docker run --rm \
    -v ${vol}:/data:ro \
    -v /opt/ragflowauth/backups/manual:/backup \
    ragflowauth-backend:local \
    tar czf /backup/${vol}.tar.gz /data
done

# 复制到 Windows
cp -r /opt/ragflowauth/backups/manual/* /mnt/replica/RagflowAuth/
```

## 📝 需要修复的问题

### 1. Worker 线程不工作
**文件**: `/opt/ragflowauth/backend/app/modules/data_security/runner.py`
**问题**: Daemon thread 可能被容器环境限制
**优先级**: 高

### 2. Volumes 备份需要验证
**问题**: 备份过程中 volumes 是否被正确备份
**优先级**: 中

## 🎯 下一步计划

1. **修复 worker 线程** - 改用进程池或定时任务替代 daemon thread
2. **测试完整备份** - 确保 volumes 被正确备份和复制
3. **验证自动复制** - 确认文件被复制到 Windows

## 📞 快速测试命令

```bash
# 测试 volumes 列表
docker volume ls --format '{{.Name}}' | grep ragflow

# 测试单个 volume 备份
docker run --rm \
  -v ragflow_compose_redis_data:/data:ro \
  -v /opt/ragflowauth/backups/test:/backup \
  ragflowauth-backend:local \
  tar czf /backup/redis.tar.gz /data

# 检查 Windows 复制
ls -la /mnt/replica/RagflowAuth/
```

## 📅 最后更新
2026-01-26 11:30
状态: 配置完成，worker 线程问题待修复
