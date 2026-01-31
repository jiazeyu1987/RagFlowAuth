# Windows 共享挂载：流程、关键不变量、改动禁区

## 1. 关键不变量（Do Not Change）

### 1.1 固定挂载点与目标目录

- 挂载点（必须固定）：`/mnt/replica`
- 目标目录（必须固定）：`/mnt/replica/RagflowAuth`
- 后端复制目录被强制固定：`backend/services/data_security/store.py:161`

### 1.2 “挂载是否成功”的判定标准

必须以 **CIFS mount 类型** 为准，而不是仅凭 `ls` 能看到文件。

- 允许出现“有历史文件但不是 CIFS 挂载”的情况（本地目录残留），所以 `ls` 只能作为辅助。
- 可靠判定：`mount` 输出中包含 `type cifs` 并覆盖 `/mnt/replica`。
- 相关实现：
  - 脚本检查：`tool/maintenance/scripts/check-mount-status.ps1:58`
  - 后端复制前强校验：`backend/services/data_security/replica_service.py:66`

---

## 2. tool.py 的职责（只做挂载/卸载/检查）

入口：`tool/maintenance/tool.py` 三个按钮，分别调用 PowerShell 脚本：
- 挂载：`tool/maintenance/tool.py:1244` → `tool/maintenance/scripts/mount-windows-share.ps1:1`
- 卸载：`tool/maintenance/tool.py:1443` → `tool/maintenance/scripts/unmount-windows-share.ps1:1`
- 检查：`tool/maintenance/tool.py:1508` → `tool/maintenance/scripts/check-mount-status.ps1:1`

### 2.1 固定 Windows 共享信息（不弹框）

目前设计为“环境固定、写死”：
- Windows 共享：`//192.168.112.72/backup`
- 固定挂载点：`/mnt/replica`
- 固定目标目录：`/mnt/replica/RagflowAuth`

对应常量（未来改动必须同步本文件）：`tool/maintenance/tool.py:85`

注意：账号/密码目前写在代码常量中（存在敏感信息暴露风险）。如未来要“去硬编码”，必须同时更新：
- `tool/maintenance/tool.py:85`（固定值来源）
- `tool/maintenance/scripts/mount-windows-share.ps1:1`（参数与凭据写入逻辑）
- 并保证仍满足“无弹框”需求（例如改为从安全存储/环境变量注入）。

---

## 3. mount-windows-share.ps1：挂载流程（必须按步骤）

脚本：`tool/maintenance/scripts/mount-windows-share.ps1:1`

### Step 1：检测当前是否已是 CIFS 挂载

- 使用 `mount | grep -E 'type.*cifs|/mnt/replica.*type'`
- 若检测到 `type cifs`，直接退出（避免重复挂载/覆盖）：`tool/maintenance/scripts/mount-windows-share.ps1:66`

### Step 2：写入服务器凭据文件

- 写入 `/root/.smbcredentials`，并 `chmod 600`：`tool/maintenance/scripts/mount-windows-share.ps1:90`
- 本机日志会对 username/password 做脱敏（避免本地泄露）：`tool/maintenance/scripts/mount-windows-share.ps1:29`

### Step 3：停止后端容器

原因：避免容器占用挂载点导致 `mount/umount` 不稳定。  
命令：`docker stop ragflowauth-backend`：`tool/maintenance/scripts/mount-windows-share.ps1:109`

### Step 4：创建挂载点

`mkdir -p /mnt/replica`：`tool/maintenance/scripts/mount-windows-share.ps1:121`

### Step 5：执行 CIFS 挂载（带 fallback）

第一次尝试（最简）：`credentials=/root/.smbcredentials`：`tool/maintenance/scripts/mount-windows-share.ps1:126`  
若失败，再尝试兼容参数：`vers=3.0,sec=ntlmssp,iocharset=utf8`：`tool/maintenance/scripts/mount-windows-share.ps1:128`

### Step 6：验证挂载

使用 `df -h | grep /mnt/replica`：`tool/maintenance/scripts/mount-windows-share.ps1:154`

### Step 6.1：确保固定目标目录存在

`mkdir -p /mnt/replica/RagflowAuth`：`tool/maintenance/scripts/mount-windows-share.ps1:165`

### Step 7：启动后端容器

`docker start ragflowauth-backend`：`tool/maintenance/scripts/mount-windows-share.ps1:173`

### Step 8：写入 /etc/fstab（持久化）

- 追加一条挂载记录：`tool/maintenance/scripts/mount-windows-share.ps1:181`
- 风险：如果服务器重启后需要自动挂载，这一步是必要的；如果不希望落盘凭据/自动挂载，必须成对移除该步骤并更新运维 SOP。

---

## 4. check-mount-status.ps1：检查输出应包含什么

脚本：`tool/maintenance/scripts/check-mount-status.ps1:1`

重点看两类输出：
- `Mount Command: ... Detected CIFS mount (type cifs)`
- `Disk Usage` 段能看到 `//192.168.112.72/backup ... /mnt/replica`

以及目录可访问性：
- `ls /mnt/replica/RagflowAuth` 能看到 `migration_pack_...` 或 `_tmp`

---

## 5. unmount-windows-share.ps1：卸载注意事项

脚本：`tool/maintenance/scripts/unmount-windows-share.ps1:1`

行为：
- 停止 `ragflowauth-backend` → `umount /mnt/replica` → 启动容器 → 验证 mount 表中不含 `/mnt/replica`

建议：
- 如出现 “target is busy”，应先检查是否有进程占用挂载点，再卸载（tool.py 内有诊断辅助函数）。
