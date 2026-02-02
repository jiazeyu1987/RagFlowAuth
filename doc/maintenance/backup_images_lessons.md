# 全量备份镜像（images.tar，曾被误称为 image.rar）问题与经验

更新日期：2026-02-01

本文记录“全量备份包含 Docker 镜像”在测试/生产环境中遇到的典型问题、根因、定位方式与防再发措施。

> 说明：备份产物实际是 `images.tar`（`docker save` 输出），不是 `image.rar`。

---

## 1) 现象清单（你会看到什么）

### A. 勾选了“全量备份包含镜像”，但备份包里没有 `images.tar`
- UI 表现：备份耗时很久，但 `migration_pack_*/` 目录里只看到 `auth.db`、`volumes/`，没有 `images.tar`。
- 常见误判：以为“镜像备份没执行”，或“备份一定在服务器别的目录”。

### B. 镜像备份执行很久，UI 卡在某个百分比/某个 step 不动
- UI 表现：长期停在 `running`，消息显示“备份镜像/备份 volume …”，很久没有更新。
- 常见误判：以为是网络慢，但其实可能已经失败/卡死。

### C. 接口偶发 500 / 409
- 500：轮询 `/api/admin/data-security/backup/jobs/<id>` 时偶发 500。
- 409：点击“开始全量备份”直接返回 409（Conflict），提示“已有任务占用”。

---

## 2) 最重要的根因与解决方案（按优先级）

### 2.1 服务器根分区空间不足（最常见）

#### 根因
- 测试服务器根分区 `/` 只有 50GB，长期运行后常见只剩 5~10GB。
- `images.tar` 常见 5GB~10GB+，写到根分区会直接失败（或写到一半失败）。

#### 如何确认
- 在服务器上执行：
  - `df -h /`
- 如果可用空间低于预估镜像大小（尤其 < 10GB），大概率会失败。

#### 解决方案（推荐）
- **备份目标目录统一放到大盘/共享盘：`/mnt/replica/RagflowAuth`**
  - CIFS 挂载容量大（例如 653GB），适合存放 `images.tar`。
- 后端已增加 precheck：当目标在 `/mnt/replica` 下，会验证 `/mnt/replica` 必须是 `cifs` 且可写；否则直接失败，避免“写到本地盘”。

---

### 2.2 `docker save -o` 输出路径错误（容器内/宿主机路径混淆）

#### 根因
- 备份逻辑运行在 `ragflowauth-backend` 容器内，通过 docker.sock 调用 docker。
- `docker save -o <path>` 的 `<path>` 是 **docker CLI 所在机器的文件系统路径**。
  - 在本项目架构下：docker CLI 在后端容器里执行，因此必须写到**容器内可见路径**（且最好是 bind mount）。
- 如果把路径错误地“转换成宿主机路径”（例如 `/opt/...`）但容器内不存在，会导致：
  - “勾选了但不生成 images.tar”
  - 或 `docker save` 失败但 UI 没有清晰提示（历史版本日志不足）

#### 解决方案
- `docker save` 输出路径必须是容器可见路径（例如：`/mnt/replica/RagflowAuth/migration_pack_*/images.tar`）。
- 已修复：不再把 `images.tar` 输出路径转换为宿主机路径。

---

### 2.3 镜像列表取不到（compose 名称/容器前缀不匹配）

#### 根因
- `docker compose config --images` 在某些环境会失败（缺 env、compose 不完整、portainer stack、compose 文件找不到等）。
- fallback 会用 `docker ps` 推导镜像列表，但早期版本对容器名前缀匹配不兼容：
  - compose 容器常见：`ragflow_compose-es01-1`（中划线）
  - 而部分逻辑误用：`ragflow_compose_`（下划线）
  - 导致“镜像列表为空”，最终跳过 `docker save`。

#### 解决方案
- 已增强：镜像 fallback 前缀匹配同时支持 `-`/`_`。
- 备份日志应能看到：
  - `镜像列表fallback(docker ps)：共 N 个`

---

### 2.4 `/mnt/replica` 未挂载或挂载掉线（最危险的“静默失败”）

#### 根因
- `/mnt/replica` 是固定 mount point；如果未挂载 CIFS，Linux 会把它当普通目录。
- 此时写 `/mnt/replica/...` 实际写到本地磁盘（50GB），最终导致：
  - 镜像备份失败
  - 或后续服务异常（磁盘打满）

#### 解决方案
- 备份前必须做 **挂载验证**：
  - `mount | grep /mnt/replica` 且文件系统类型为 `cifs`
- 已增强：后端 precheck 会强制校验 `/proc/mounts`，不是 `cifs` 直接失败。

---

### 2.5 备份卡死：sqlite 直接写 CIFS / 子进程输出 EOF busy-loop

#### 根因 1：sqlite 写 CIFS 卡死
- sqlite online backup 会写大量小页，某些 CIFS 场景会“卡死/极慢”。
- 解决：sqlite 先写 `/tmp`，再 copy 到 `/mnt/replica`（已实现）。

#### 根因 2：长命令输出处理不当导致后端 CPU 100%
- 为了让 UI 不“没日志”，引入了长命令 heartbeat；但如果 stdout 到 EOF 后处理不当，会导致 selector busy-loop，后端 CPU 100%，任务永远卡住。
- 解决：已修复 `run_cmd_live` 的 EOF 处理，避免 busy-loop。

---

### 2.6 409 Conflict：残留 backup lock（任务被中断后遗留）

#### 根因
- 备份系统使用 sqlite 表 `backup_locks` 做跨进程互斥。
- 如果备份过程中强制重启容器/kill 进程，锁可能残留，导致后续触发备份直接 409。

#### 解决方案
- 服务器侧紧急处理：删除 `backup_locks` 里的 `backup` 锁（工具/运维脚本已执行过）。
- 代码增强：当“无 queued/running job，但 lock 存在”时，会尝试清理一次 stale lock 后再启动。

---

## 3) 推荐的排障步骤（最短路径）

当你发现“勾选了镜像但没有 `images.tar`/卡住”时，按顺序做：

1) 确认 `/mnt/replica` 是 CIFS 且可写：
   - `mount | grep /mnt/replica`
   - `df -h /mnt/replica`
2) 确认根分区空间（防止写错盘）：
   - `df -h /`
3) 看备份包目录是否生成：
   - `/mnt/replica/RagflowAuth/migration_pack_*/`
4) 看后端容器日志（是否有镜像列表/保存开始/错误）：
   - `docker logs ragflowauth-backend --tail 300`
5) 如出现 409：检查锁表：
   - `sqlite3 /opt/ragflowauth/data/auth.db 'select * from backup_locks;'`

---

## 4) 结论：如何避免未来再次出现

- 备份输出统一使用：`/mnt/replica/RagflowAuth`（大盘 + 可离线恢复）
- 备份前强制校验：`/mnt/replica` 必须是 `cifs`，并做写入探针（已落地）
- sqlite 备份先落本地再复制到 CIFS（已落地）
- 长任务必须有心跳日志，但要避免 EOF busy-loop（已修复）
- 备份互斥锁必须可自动清理 stale lock（已增强）

