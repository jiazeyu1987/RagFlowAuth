# 故障排查：第二天 Windows 上没有备份怎么办

场景：你设置了“凌晨 4 点”定时备份；第二天早上发现 Windows 共享目录没有新的 `migration_pack_...`。

目标：通过日志快速定位“问题发生在：定时没触发 / 备份失败 / 复制失败 / 挂载失败”。

---

## 0. 先确认两件事（不确认会白查）

1) Windows 共享是否就是 `//192.168.112.72/backup`，并且最终目录固定为：`/mnt/replica/RagflowAuth`  
2) 服务器选择的环境（生产 57 / 测试 58）是否正确（你可能在错的服务器上看结果）

---

## 1. 判断：定时是否触发

### 1.1 看后端容器日志（最直接）

在目标服务器执行：
- `docker logs --since 12h ragflowauth-backend | grep -E \"Backup scheduler V2 started|Running (full|incremental) backup|Started (full|incremental) backup\"`

对应代码日志点：`backend/services/data_security_scheduler_v2.py:235`

### 1.2 看 “上次定时触发” 时间（last_run_at_ms）

后端在触发定时时会写入 `last_run_at_ms`：`backend/services/data_security_scheduler_v2.py:219`

如果 `last_run_at_ms` 仍是旧时间：
- 要么后端容器当时不在运行
- 要么 `enabled=false` 或 schedule 未设置
- 要么同一窗口内被判定“已尝试/完成”（避免重复触发）

---

## 2. 判断：备份任务是否执行成功（即使没复制也能看出来）

查看最近 job（前端“数据安全”页面会显示，或调用接口）：
- `GET /api/admin/data-security/backup/jobs`

关键字段：
- `status`：`queued/running/completed/failed`
- `message`：当前阶段（例如“备份完成，准备同步”）
- `detail`：失败原因（最重要）
- `output_dir`：备份包目录（pack_dir）

备份阶段的关键 message 变化见：`backend/services/data_security/backup_service.py:53`

### 2.1 若 status=failed

直接看 `detail`，通常能定位：
- Docker 不可用
- 找不到 compose 路径
- 找不到数据库文件
- volumes 备份失败等

失败最终写入点：`backend/app/modules/data_security/runner.py:64`

### 2.2 若 status=completed 但 Windows 无文件

高概率是“同步失败”，看 message/detail 是否包含：
- `同步失败：目标路径未挂载到Windows共享`
- `replica_target_path is empty`

同步失败写入点：`backend/services/data_security/replica_service.py:74` 或 `backend/services/data_security/backup_service.py:173`

---

## 3. 判断：是否挂载失败（最常见）

复制要求：`/mnt/replica` 必须是 CIFS mount，且目标目录为 `/mnt/replica/RagflowAuth`。后端会强校验：`backend/services/data_security/replica_service.py:66`

### 3.1 用 tool.py 检查（推荐）

在本机运行 `tool/maintenance/tool.py`：
- 选择正确环境（57/58）
- 点 “检查挂载状态”

脚本输出日志在本机：
- `%TEMP%\\check_mount_status.log`

期望看到：
- `Mount Command: ... Detected CIFS mount (type cifs)`
- `Disk Usage` 中出现 `//192.168.112.72/backup ... /mnt/replica`

### 3.2 服务器端手动检查（无需 tool.py）

在目标服务器执行：
- `mount | grep /mnt/replica`
- `df -h | grep /mnt/replica`
- `ls -l /mnt/replica/RagflowAuth | head`

如果 `mount` 没有 `type cifs`，那复制必然失败（即使目录里有历史文件，也可能是本地残留）。

---

## 4. 典型原因 → 对应你能看到的日志线索

### 4.1 Windows 共享没挂载（最常见）

现象：
- job `completed`，但 message/detail 提示 “同步失败：目标路径未挂载到Windows共享”
- 或 `check_mount_status.log` 显示 Not Mounted

解决：
- 先用 tool.py 点 “挂载 Windows 共享”
- 再点 “检查挂载状态”

### 4.2 挂载到了错误的 WindowsHost（例如误填成 172.30.30.58）

现象：
- mount 脚本 `Exit Code: 32`，并且 Output 会包含更具体的 mount 错误（已将 stderr 合并到输出）

解决：
- 当前实现为写死 `192.168.112.72`，不应再发生；如果发生，说明代码被改坏了（回滚 `tool/maintenance/tool.py:85` 与 `tool/maintenance/scripts/mount-windows-share.ps1:1`）

### 4.3 备份执行了，但复制过程异常中断

现象：
- Windows 目录里出现 `_tmp/job_...` 但没有最终 `migration_pack_...` 目录

解释：
- 复制采用“临时目录 + rename”的原子流程：`backend/services/data_security/replica_service.py:84`

解决：
- 看 job.detail（异常堆栈）
- 看后端容器日志：`docker logs ragflowauth-backend | grep REPLICATION`

---

## 5. 必做自检（防止“静默失效”）

建议每天早上自动/手动检查以下 3 项（任一失败都要处理）：

1) CIFS 挂载存在：`mount | grep /mnt/replica` 且包含 `type cifs`
2) Windows 目录存在：`ls -ld /mnt/replica/RagflowAuth`
3) 最近一次 job 为 `completed` 且 message 包含 “已同步”：
   - `message="备份完成（已同步）"`：`backend/services/data_security/replica_service.py:141`

