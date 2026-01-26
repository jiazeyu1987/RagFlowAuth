# 实现计划：备份完成后自动复制到局域网Windows机器（优化版）

## 需求概述

在备份任务成功完成后，自动将备份数据复制到局域网内的另一台Windows机器上。

**用户需求：**
- ✅ 备份完成后立即复制
- ✅ 目标机器：Windows（使用SMB共享）
- ✅ 网络稳定，一直在线
- ✅ 复制失败也保留本地备份
- ✅ 复制失败：备份仍成功，但记录“同步失败”告警（message/detail）

**优化方案：**
- ✅ **优先：宿主机挂载SMB共享**（不用容器内处理UNC路径）
- ✅ **Docker bind mount**（容器内当作普通目录复制）
- ✅ **原子性复制**（临时目录 + DONE标记 + 重命名）
- ✅ **分离的配置项**（`replica_*`，不混用`upload_*`）

---

## 重要前提：宿主机类型

本文的“宿主机挂载 SMB → bind mount 进容器”方案**只适用于 Linux 宿主机**，或者你是在 **WSL/Linux 环境里运行 docker**（docker 命令与挂载目录处于同一 Linux 环境）。

如果你的宿主机是 **Windows + Docker Desktop（Linux containers）** 且你在 PowerShell 里运行 `tool/scripts/quick-deploy.ps1`：
- 你无法直接在 PowerShell 下把 `/mnt/replica:/replica` 这样的 Linux 路径 bind mount 进容器（路径语义不一致）。
- 这时更建议采用“容器内直连 SMB 复制”（见下文 *Windows 宿主机方案*）。

---

## 方案设计

### 技术方案：宿主机SMB挂载 + Docker Bind Mount

**为什么这个方案更稳定？**
1. ✅ **容器内无网络操作** - 直接拷贝文件，无需处理UNC路径
2. ✅ **无需额外依赖** - 不需要在容器内安装`smbprotocol`
3. ✅ **权限简单** - 宿主机统一管理，容器只需读写权限
4. ✅ **原子性保证** - 临时目录 + 重命名，避免半成品
5. ✅ **调试方便** - 可以直接在宿主机查看挂载状态

---

## 实现步骤

### 第一步：Windows目标机器准备（10分钟）

#### 1.1 创建专用备份账号

在Windows机器上：
1. 创建用户：`backup_user`
2. 设置强密码
3. 记录账号密码

#### 1.2 创建共享文件夹

1. 创建文件夹：`C:\Backups`
2. 右键 → "属性" → "共享" → "高级共享"
3. 勾选"共享此文件夹"
4. 点击"权限" → 添加 `backup_user`
5. 勾选"完全控制"

#### 1.3 配置防火墙

```powershell
# 管理员PowerShell
Enable-NetFirewallRule -DisplayGroup "File and Printer Sharing"
```

**验证共享：**
```
\\<Windows机器IP>\Backups
```

---

### 第二步：Linux宿主机挂载SMB共享（15分钟）

> 推荐：直接使用仓库内工具脚本一键完成挂载与校验：`tool/scripts/setup-smb-replica.sh`（需要在 Linux 服务器上执行）。

#### 2.1 安装cifs-utils

```bash
sudo apt-get update
sudo apt-get install cifs-utils
```

#### 2.2 创建凭据文件

```bash
sudo mkdir -p /root/.smbcreds
sudo nano /root/.smbcreds/ragflow_backup
```

**内容：**
```
username=backup_user
password=<你的密码>
domain=WORKGROUP
```

**设置权限：**
```bash
sudo chmod 600 /root/.smbcreds/ragflow_backup
```

#### 2.3 创建挂载点

```bash
sudo mkdir -p /mnt/replica
```

#### 2.4 测试挂载

```bash
sudo mount -t cifs //"<Windows机器IP>"/Backups /mnt/replica \
  -o credentials=/root/.smbcreds/ragflow_backup,iocharset=utf8,uid=1000,gid=1000,vers=3.0
```

**验证挂载：**
```bash
ls -la /mnt/replica
# 应该能看到共享内容

sudo touch /mnt/replica/test.txt
# 应该能创建文件
```

#### 2.5 配置开机自动挂载

```bash
sudo nano /etc/fstab
```

**添加：**
```
//"<Windows机器IP>"/Backups /mnt/replica cifs \
  credentials=/root/.smbcreds/ragflow_backup,iocharset=utf8,uid=1000,gid=1000,vers=3.0,_netdev,nofail 0 0
```

---

## Windows 宿主机方案（Docker Desktop / PowerShell 部署推荐）

如果你的后端运行在 Linux 容器里、宿主机是 Windows（Docker Desktop），最可落地的方案是：

### 方案 W1：容器内直连 SMB（推荐）

核心思想：**不做宿主机挂载**，在容器内通过 SMB 客户端把 `pack_dir` 推送到 `\\WIN-PC\Backups`。

- 优点：不依赖宿主机挂载；PowerShell 运行 `quick-deploy.ps1` 不受路径影响
- 缺点：需要容器里具备 SMB 客户端工具（例如 `smbclient`），或用 Python SMB 库

建议做法：
- 在后端镜像里加入 `smbclient`（Debian/Ubuntu 基础镜像一般是 `apt-get install -y smbclient`）
- 在备份完成后执行：
  - 先上传到目标临时目录（例如 `Backups/RagflowAuth/_tmp/job_<id>/...`）
  - 上传完成写 `DONE`/`manifest.json`
  - 最后服务端（目标机）侧无需额外动作；如需“原子切换”，可以用“目录名包含时间戳 + DONE”来规避半成品

> 注意：Windows 侧共享权限要给专用账号写入权限；容器内保存账号密码应使用环境变量/secret，而不是写死。

### 方案 W2：WSL2 内挂载 + 在 WSL 里运行 docker

核心思想：在 WSL2（Ubuntu）里按上面的 Linux 步骤挂载到 `/mnt/replica`，并在 WSL 里运行 docker/compose，让 `-v /mnt/replica:/replica` 生效。

- 优点：仍然是“容器内普通文件复制”，实现简单稳定
- 缺点：需要把部署流程迁移到 WSL（PowerShell 下的 `quick-deploy.ps1` 不直接适用）

---

### 第三步：修改Docker部署脚本（10分钟）

**文件：** `tool/scripts/quick-deploy.ps1`

**在启动容器时添加bind mount：**

```powershell
# 启动backend容器时添加：
$BackendCmd += " -v /mnt/replica:/replica"
```

**完整示例：**
```powershell
$BackendCmd = "docker run -d --name ragflowauth-backend"
$BackendCmd += " --network $NetworkName"
$BackendCmd += " -p ${BackendPort}:${BackendPort}"
$BackendCmd += " -v ${DataDir}/data:/app/data"
$BackendCmd += " -v ${DataDir}/uploads:/app/uploads"
$BackendCmd += " -v ${DataDir}/ragflow_config.json:/app/ragflow_config.json:ro"
$BackendCmd += " -v ${DataDir}/ragflow_compose:/app/ragflow_compose:ro"
$BackendCmd += " -v /var/run/docker.sock:/var/run/docker.sock:ro"
$BackendCmd += " -v /mnt/replica:/replica"  # ← 新增
$BackendCmd += " --restart unless-stopped"
```

> 注意：上述 `/mnt/replica` 仅适用于“Linux 宿主机 / 在 WSL 的 Linux 环境中运行 docker”。
> 若你是在 Windows PowerShell 里运行该脚本，请使用上面的 *方案 W1（容器内直连 SMB）*。

**重启容器：**
```bash
# 重新执行部署脚本
pwsh -File tool/scripts/quick-deploy.ps1
```

---

### 第四步：后端 - 添加复制配置到数据库（15分钟）

**文件：** `backend/database/schema/data_security.py`

**新增字段：**
```python
def add_replica_columns_to_data_security(conn: sqlite3.Connection) -> None:
    """Add automatic replication settings."""
    if not table_exists(conn, "data_security_settings"):
        return
    add_column_if_missing(conn, "data_security_settings", "replica_enabled INTEGER NOT NULL DEFAULT 0")
    add_column_if_missing(conn, "data_security_settings", "replica_target_path TEXT")
    add_column_if_missing(conn, "data_security_settings", "replica_subdir_format TEXT DEFAULT 'flat'")
```

**字段说明：**
- `replica_enabled`: 是否启用自动复制
- `replica_target_path`: 容器内目标路径（如：`/replica/RagflowAuth`）
- `replica_subdir_format`: 子目录格式（`flat`=平铺，`date`=按日期分桶 `YYYY/MM/DD`）

---

### 第五步：后端 - 添加复制配置到模型和Store（10分钟）

**文件：** `backend/services/data_security/models.py`

**在 `DataSecuritySettings` 添加：**
```python
# Automatic replication settings
replica_enabled: bool
replica_target_path: str | None
replica_subdir_format: str  # 'flat' or 'date'
```

**文件：** `backend/services/data_security/store.py`

**在 `get_settings()` 添加：**
```python
return DataSecuritySettings(
    # ... 现有字段 ...
    replica_enabled=bool(get_col("replica_enabled", 0)),
    replica_target_path=get_col("replica_target_path"),
    replica_subdir_format=get_col("replica_subdir_format") or "flat",
)
```

**在 `update_settings()` 的 `allowed` 添加：**
```python
allowed = {
    # ... 现有字段 ...
    "replica_enabled",
    "replica_target_path",
    "replica_subdir_format",
}
```

---

### 第六步：后端 - 创建复制服务（60分钟）

**文件：** `backend/services/data_security/replica_service.py`（新建）

**完整实现：**
```python
from __future__ import annotations

import os
import shutil
import time
import json
from pathlib import Path
from datetime import datetime

from .common import ensure_dir
from .store import DataSecurityStore


class BackupReplicaService:
    """Service to replicate backups to mounted SMB share."""

    def __init__(self, store: DataSecurityStore) -> None:
        self.store = store

    def replicate_backup(self, pack_dir: Path, job_id: int) -> bool:
        """
        Replicate backup directory to replica target.

        Args:
            pack_dir: Local backup directory (e.g., /opt/backups/migration_pack_20250125_183000)
            job_id: Backup job ID (for progress updates)

        Returns:
            True if replication succeeded, False otherwise
        """
        settings = self.store.get_settings()

        # Check if replication is enabled
        if not getattr(settings, 'replica_enabled', False):
            return True  # Not enabled, skip

        target_path = settings.replica_target_path
        if not target_path:
            self.store.update_job(job_id, message="复制未配置目标路径")
            return False

        target_base = Path(target_path)
        if not target_base.is_absolute():
            self.store.update_job(job_id, message="复制目标路径必须是绝对路径")
            return False

        try:
            # Generate subdirectory based on format
            subdir = self._generate_subdir(pack_dir.name, settings.replica_subdir_format)
            target_final_dir = target_base / subdir
            target_tmp_dir = target_base / "_tmp" / f"job_{job_id}_{int(time.time())}"

            # Step 1: Copy to temporary directory
            self.store.update_job(job_id, message="开始复制（临时目录）", progress=92)
            self._copy_directory(pack_dir, target_tmp_dir, job_id)

            # Step 2: Write manifest and DONE marker
            self._write_replication_manifest(target_tmp_dir, pack_dir.name, job_id)
            done_marker = target_tmp_dir / "DONE"
            done_marker.touch()
            self.store.update_job(job_id, message="复制完成（验证中）", progress=97)

            # Step 3: Atomic rename to final directory
            if target_final_dir.exists():
                shutil.rmtree(target_final_dir)
            target_final_dir.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(target_tmp_dir), str(target_final_dir))

            # Step 4: Update job message
            self.store.update_job(
                job_id,
                message="备份完成（已同步）",
                progress=100
            )
            return True

        except Exception as e:
            # Replication failed, but backup is still completed
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Replication failed: {e}", exc_info=True)

            self.store.update_job(
                job_id,
                message=f"备份完成（同步失败：{str(e)}）",
                detail=str(e),
                progress=100
            )
            return False

    def _generate_subdir(self, pack_name: str, format_type: str) -> str:
        """Generate subdirectory based on format."""
        if format_type == "date":
            # YYYY/MM/DD/migration_pack_xxx
            now = datetime.now()
            date_path = now.strftime("%Y/%m/%d")
            return str(Path(date_path) / pack_name)
        else:
            # flat: migration_pack_xxx
            return pack_name

    def _copy_directory(self, src: Path, dst: Path, job_id: int):
        """Copy directory recursively with progress updates."""
        ensure_dir(dst)

        total_files = sum(len(files) for _, _, files in os.walk(src))
        if total_files == 0:
            return

        copied_files = 0
        for root, dirs, files in os.walk(src):
            for file in files:
                src_file = Path(root) / file
                rel_path = src_file.relative_to(src)
                dst_file = dst / rel_path

                # Create parent directory if needed
                dst_file.parent.mkdir(parents=True, exist_ok=True)

                # Copy file
                shutil.copy2(src_file, dst_file)

                copied_files += 1
                if total_files > 0:
                    progress = 92 + int(5 * copied_files / total_files)
                    self.store.update_job(job_id, progress=progress)

    def _write_replication_manifest(self, target_dir: Path, pack_name: str, job_id: int):
        """Write replication manifest file."""
        manifest = {
            "pack_name": pack_name,
            "replicated_at_ms": int(time.time() * 1000),
            "replicated_at": datetime.now().isoformat(),
            "job_id": job_id,
            "source_hostname": os.uname().nodename,
        }

        manifest_file = target_dir / "replication_manifest.json"
        manifest_file.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
```

---

### 第七步：后端 - 集成到备份服务（10分钟）

**文件：** `backend/services/data_security/backup_service.py`

**在 `run_job` 方法末尾添加复制调用：**

```python
def run_job(self, job_id: int, *, include_images: bool | None = None) -> None:
    # ... 现有备份逻辑 ...

    try:
        # ... 备份逻辑 ...

        self.store.update_job(
            job_id,
            status="completed",
            progress=90,
            message="备份完成",
            finished_at_ms=int(time.time() * 1000)
        )

        # ===== 新增：自动复制 =====
        try:
            from .replica_service import BackupReplicaService
            replica_svc = BackupReplicaService(self.store)
            replica_svc.replicate_backup(pack_dir, job_id)
        except Exception as e:
            # 复制失败不影响备份状态
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Replication failed: {e}")

    except Exception as exc:
        # ... 现有错误处理 ...
```

---

### 第八步：后端 - 添加复制配置API（15分钟）

**文件：** `backend/app/modules/data_security/router.py`

**更新 `get_settings` 和 `update_settings`：**

```python
@router.get("/admin/data-security/settings")
async def get_settings(_: AdminOnly) -> dict[str, Any]:
    store = DataSecurityStore()
    s = store.get_settings()
    return {
        # ... 现有字段 ...
        "replica_enabled": getattr(s, 'replica_enabled', False),
        "replica_target_path": getattr(s, 'replica_target_path') or "",
        "replica_subdir_format": getattr(s, 'replica_subdir_format') or "flat",
    }

@router.put("/admin/data-security/settings")
async def update_settings(_: AdminOnly, body: dict[str, Any]) -> dict[str, Any]:
    store = DataSecurityStore()
    s = store.update_settings(body or {})
    return {
        # ... 现有字段 ...
        "replica_enabled": getattr(s, 'replica_enabled', False),
        "replica_target_path": getattr(s, 'replica_target_path') or "",
        "replica_subdir_format": getattr(s, 'replica_subdir_format') or "flat",
    }
```

**确保 `store.update_settings()` 的 `allowed` 包含新字段：**

```python
allowed = {
    # ... 现有字段 ...
    "replica_enabled",
    "replica_target_path",
    "replica_subdir_format",
}
```

---

### 第九步：前端 - 添加复制配置UI（40分钟）

**文件：** `fronted/src/pages/DataSecurity.js`

**在备份设置Card后添加新Card：**

```jsx
<Card title="自动复制设置">
  <label style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
    <input
      type="checkbox"
      checked={!!settings?.replica_enabled}
      onChange={(e) => setSettings(p => ({ ...p, replica_enabled: e.target.checked }))}
    />
    启用自动复制（备份完成后自动复制到挂载目录）
  </label>

  {settings?.replica_enabled && (
    <div style={{ display: 'grid', gap: '12px', marginTop: '16px' }}>
      <label>
        容器内目标路径
        <input
          type="text"
          value={settings?.replica_target_path || ''}
          onChange={(e) => setSettings(p => ({ ...p, replica_target_path: e.target.value }))}
          placeholder="/replica/RagflowAuth"
          style={{ width: '100%', padding: '8px', border: '1px solid #d1d5db', borderRadius: '8px', marginTop: '6px' }}
        />
        <div style={{ color: '#6b7280', fontSize: '0.85rem', marginTop: '4px' }}>
          容器内的绝对路径，该路径已通过Docker bind mount挂载到Windows共享
        </div>
      </label>

      <label>
        子目录格式
        <select
          value={settings?.replica_subdir_format || 'flat'}
          onChange={(e) => setSettings(p => ({ ...p, replica_subdir_format: e.target.value }))}
          style={{ width: '100%', padding: '8px', border: '1px solid #d1d5db', borderRadius: '8px', marginTop: '6px' }}
        >
          <option value="flat">平铺（所有备份在同一目录）</option>
          <option value="date">按日期分桶（YYYY/MM/DD）</option>
        </select>
        <div style={{ color: '#6b7280', fontSize: '0.85rem', marginTop: '4px' }}>
          {settings?.replica_subdir_format === 'date'
            ? '目标路径格式：/replica/RagflowAuth/2025/01/25/migration_pack_xxx'
            : '目标路径格式：/replica/RagflowAuth/migration_pack_xxx'}
        </div>
      </label>

      <div style={{ padding: '10px', background: '#eff6ff', border: '1px solid #93c5fd', borderRadius: '8px', fontSize: '0.85rem' }}>
        <div style={{ fontWeight: 600, marginBottom: '8px' }}>📋 配置说明：</div>
        <div style={{ color: '#1e40af', lineHeight: '1.5' }}>
          1. 此功能需要宿主机已挂载Windows共享到容器内路径<br/>
          2. 复制过程采用原子性操作（临时目录 + 重命名），避免半成品<br/>
          3. 复制失败不影响本地备份，会在消息中标注"同步失败"<br/>
          4. 确保容器内有该路径的写权限
        </div>
      </div>
    </div>
  )}
</Card>
```

---

## 关键文件清单

### 需要修改的文件：
1. `backend/database/schema/data_security.py` - 添加复制配置字段
2. `backend/database/schema/ensure.py` - 注册迁移
3. `backend/services/data_security/models.py` - 添加复制配置到模型
4. `backend/services/data_security/store.py` - 添加复制配置到allowed
5. `backend/services/data_security/backup_service.py` - 集成复制调用
6. `backend/app/modules/data_security/router.py` - API返回复制配置
7. `fronted/src/pages/DataSecurity.js` - 添加复制配置UI
8. `tool/scripts/quick-deploy.ps1` - 添加bind mount（宿主机已挂载后）

### 需要新建的文件：
1. `backend/services/data_security/replica_service.py` - 复制服务

---

## 时间估算

| 步骤 | 时间 |
|------|------|
| Windows共享准备 | 10分钟 |
| Linux宿主机挂载SMB | 15分钟 |
| Docker部署脚本修改 | 10分钟 |
| 添加数据库字段 | 15分钟 |
| 添加模型和Store | 10分钟 |
| 创建复制服务 | 60分钟 |
| 集成到备份流程 | 10分钟 |
| 添加API | 15分钟 |
| 前端UI | 40分钟 |
| 测试验证 | 30分钟 |
| **总计** | **约3小时** |

---

## 测试验证

### 1. 宿主机挂载测试

```bash
# 测试挂载
ls -la /mnt/replica

# 测试写入
echo "test" | sudo tee /mnt/replica/test.txt

# 测试容器内访问
docker exec ragflowauth-backend ls -la /replica
```

### 2. 前端配置测试

1. 访问 http://172.30.30.57:3001
2. 进入"数据安全"页面
3. 配置复制设置：
   - 勾选"启用自动复制"
   - 目标路径：`/replica/RagflowAuth`
   - 子目录格式：`flat` 或 `date`
4. 点击"保存设置"

### 3. 完整备份测试

1. 点击"立即备份"
2. 观察进度：90% → 92% → ... → 100%
3. 查看消息：应该显示"备份完成（已同步）"或"备份完成（同步失败：xxx）"
4. 检查目标机器：
   ```bash
   ls -la /mnt/replica/RagflowAuth/
   # 或者
   ls -la /mnt/replica/RagflowAuth/2025/01/25/
   ```
5. 应该能看到新的备份目录，且包含 `DONE` 标记文件

---

## 注意事项

1. **宿主机挂载必须在容器启动前完成**
2. **容器内路径权限**：确保容器内进程有读写权限
3. **磁盘空间**：目标Windows机器需要足够空间
4. **网络稳定性**：虽然网络稳定，但仍建议监控挂载状态
5. **原子性**：临时目录 + 重命名确保目标机器不会看到半成品
6. **错误处理**：复制失败不影响备份完成状态
7. **cron 的周几语义**：请确保前端与后端都使用标准 cron 约定（Sun=0/7，Mon=1...Sat=6），否则“每周几”会跑错

---

## 优势

✅ **简单稳定** - 容器内只需普通文件操作
✅ **无需额外依赖** - 不需要在容器内安装SMB库
✅ **原子性保证** - 临时目录 + 重命名
✅ **失败容错** - 复制失败不影响本地备份
✅ **易于调试** - 可以直接在宿主机和容器内查看
✅ **灵活性** - 支持平铺和按日期分桶两种模式

---

## 与原方案对比

| 特性 | 原方案（容器内SMB） | 新方案（宿主机挂载） |
|------|---------------------|---------------------|
| 容器内依赖 | 需要 smbprotocol | 无需额外依赖 ✅ |
| 复杂度 | 高（需处理UNC） | 低（普通文件操作）✅ |
| 稳定性 | 中等 | 高 ✅ |
| 调试难度 | 较难 | 容易 ✅ |
| 权限管理 | 复杂 | 简单 ✅ |
