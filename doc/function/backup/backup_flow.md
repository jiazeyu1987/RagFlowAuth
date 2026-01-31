# 备份与复制到 Windows：流程、关键不变量、改动禁区

## 1. 关键不变量（Do Not Change）

这些不变量一旦被“优化/重构”，极容易造成**备份成功但未复制到 Windows**，或定时失效但没人发现。

### 1.1 Windows 复制目录（固定）

- **固定目录**：`/mnt/replica/RagflowAuth`
- 后端会强制写入（即使前端/调用方传了别的值也会被覆盖）：`backend/services/data_security/store.py:161`
- 原因：复制服务会检查 CIFS mount，并且工具/运维依赖固定目录进行验证。

### 1.2 挂载点（固定）

- **固定挂载点**：`/mnt/replica`
- 后端复制检查的是“目标目录是否处于 CIFS mount 下”，而不是是否能 `ls`：`backend/services/data_security/replica_service.py:66`

### 1.3 复制动作的触发点

- 备份完成后，复制逻辑由后端在同一个 job 中执行（不是前端复制，也不是容器外复制）：`backend/services/data_security/backup_service.py:167`

### 1.4 复制的原子性

- 复制先写入临时目录：`/mnt/replica/RagflowAuth/_tmp/job_<id>_<ts>`，然后 rename 到最终目录，避免“半成品”目录：`backend/services/data_security/replica_service.py:84`
- 复制完成会写 `DONE` 标记与 `replication_manifest.json`：`backend/services/data_security/replica_service.py:118`

### 1.5 定时触发机制（不是 cron/systemd）

- 定时逻辑是**后端进程内的后台线程**（scheduler v2），以 cron 表达式判定是否到点：`backend/services/data_security_scheduler_v2.py:235`
- 这意味着：后端容器如果长时间不运行/频繁重启，定时行为会受到影响（可通过日志与 `last_run_at_ms` 判断）。

---

## 2. 后端：数据备份流程（生成 migration_pack）

入口：`DataSecurityBackupService.run_job()`：`backend/services/data_security/backup_service.py:29`

### 2.1 目标目录（migration_pack 输出目录）

- **注意：备份输出目录（pack_dir）与“复制到 Windows 的目录”不是一回事。**
- pack_dir 的根目录来自 `settings.target_path()`（由 `target_mode/target_ip/target_share_name/target_local_dir` 决定）：`backend/services/data_security/backup_service.py:40`
- pack_dir 格式：`<target>/migration_pack_<timestamp>`：`backend/services/data_security/backup_service.py:55`

### 2.2 备份内容

1) 本项目数据库 `auth.db`（SQLite 在线备份）  
- `sqlite_online_backup(..., pack_dir/"auth.db")`：`backend/services/data_security/backup_service.py:66`

2) RAGFlow volumes（按 compose 项目名推导 volume 前缀，逐个打 tar.gz）  
- 获取 project/prefix：`read_compose_project_name()`：`backend/services/data_security/backup_service.py:79`
- 列出 volumes：`list_docker_volumes_by_prefix()`：`backend/services/data_security/backup_service.py:89`
- 逐个 `docker_tar_volume()`：`backend/services/data_security/backup_service.py:98`

3)（可选）镜像备份 `images.tar`（全量备份可包含）  
- `docker_save_images()`：`backend/services/data_security/backup_service.py:108`

4) settings 快照（best-effort）  
- `backup_settings.json`：`backend/services/data_security/backup_service.py:142`

### 2.3 失败/状态可见性（重要）

- job 的 `message/progress/detail/output_dir` 会持续更新（前端/接口可读）：`backend/services/data_security/backup_service.py:53`
- 备份完成后会进入“准备同步”的阶段（仍然 status=running）：`backend/services/data_security/backup_service.py:155`
- 如果同步失败，不应把整体 job 标记为 failed，但会写入 message/detail：`backend/services/data_security/backup_service.py:173`

---

## 3. 后端：复制到 Windows（replica）

入口：`BackupReplicaService.replicate_backup(pack_dir, job_id)`：`backend/services/data_security/replica_service.py:25`

### 3.1 启用开关

- 只有 `settings.replica_enabled == True` 才会执行复制：`backend/services/data_security/replica_service.py:44`
- 当前前端已隐藏“自动复制设置”区域（避免误改），但复制仍依赖数据库里的 `replica_enabled` 值。

### 3.2 CIFS mount 强校验（核心）

- 复制前必须确认 `replica_target_path` 所在路径是 CIFS：`backend/services/data_security/replica_service.py:66`
- 若不为 CIFS，会明确写入 job：`message="备份完成（同步失败：目标路径未挂载到Windows共享）"`：`backend/services/data_security/replica_service.py:74`

### 3.3 复制结果的可验证产物

复制成功后，在 Windows 共享对应目录应能看到：
- `migration_pack_.../auth.db`
- `migration_pack_.../replication_manifest.json`
- `migration_pack_.../DONE`
- （如有）`migration_pack_.../volumes/*.tar.gz`
- （如包含镜像）`migration_pack_.../images.tar`

验证逻辑（后端端内验证）：`_verify_replication()`：`backend/services/data_security/replica_service.py:391`

---

## 4. 定时备份（凌晨 4 点）的可追溯性

调度器：`BackupSchedulerV2`：`backend/services/data_security_scheduler_v2.py:25`

### 4.1 触发记录

- 到点触发时会写入：
  - job reason：`定时增量备份@YYYY-MM-DD HH:MM` / `定时全量备份@...`：`backend/services/data_security_scheduler_v2.py:211`
  - `last_run_at_ms`（用于前端显示“上次定时触发”）：`backend/services/data_security_scheduler_v2.py:219`

### 4.2 定时失效常见原因（必须能从日志定位）

1) 后端容器不在运行 / 重启频繁（scheduler 不存在）  
2) 备份被锁占用（已有 queued/running job）  
3) Windows 共享未挂载到 `/mnt/replica`，导致同步失败（备份仍可能成功，但不在 Windows 上）

详细排查见：`doc/function/backup/troubleshooting.md`

---

## 5. 维护者自检清单（改代码前后都要做）

每次修改任意一处“备份/复制/挂载”相关代码，都必须跑完以下自检（否则属于高风险变更）：

1) 固定目录不变量仍存在  
   - `replica_target_path` 强制为 `/mnt/replica/RagflowAuth`：`backend/services/data_security/store.py:161`

2) CIFS 校验仍是硬门槛（不能被改成“能 ls 就算挂载”）  
   - 校验点：`backend/services/data_security/replica_service.py:66`

3) 复制仍为“临时目录 + rename”的原子流程  
   - 关键点：`backend/services/data_security/replica_service.py:84`

4) 定时触发后能在 job 中看见触发时间（便于第二天追责）  
   - `定时增量备份@...` / `定时全量备份@...`：`backend/services/data_security_scheduler_v2.py:211`
   - `last_run_at_ms`：`backend/services/data_security_scheduler_v2.py:219`

5) 挂载脚本仍会创建固定目录（避免误判“挂载失败”）  
   - `mkdir -p /mnt/replica/RagflowAuth`：`tool/maintenance/scripts/mount-windows-share.ps1:165`

