# 发布/同步/还原：问题复盘与经验教训（必读）

更新日期：2026-02-01

本文记录近期在“发布镜像 / 同步数据 / 还原数据”链路里遇到的真实问题、根因与修复方式，目的是：
- 避免未来改代码/改环境导致链路失效
- 一旦失败，能通过日志快速定位到具体一步、具体原因

适用环境：
- TEST：`172.30.30.58`
- PROD：`172.30.30.57`
- RagflowAuth：`ragflowauth-backend` / `ragflowauth-frontend`
- RAGFlow compose：`/opt/ragflowauth/ragflow_compose`

工具本地日志：`tool/maintenance/tool_log.log`

---

## 1) 问题：发布（测试 -> 正式，镜像）失败：找不到 docker-compose / compose label 为空

### 现象
- 工具日志提示找不到 `/opt/ragflowauth/docker-compose.yml` 或 `.yaml`
- 或者 `ragflowauth-backend` 容器没有 `com.docker.compose.*` labels（`config_files`/`working_dir` 为空）

### 根因
- 服务器上的 RagflowAuth 可能不是用 `docker compose` 启动，而是 `docker run`（或 Portainer 非 stack/compose 方式）
- 因此无法依赖 compose 文件路径/label 来做发布

### 解决策略（工具侧）
工具必须支持 **docker run 发布模式**：
1) 在 TEST 读取当前运行镜像 tag（通过 `docker inspect`）
2) `docker save` 导出镜像 tar
3) `scp -3` 直接 TEST -> PROD 传输 tar（不落地本机）
4) PROD `docker load`
5) 在 PROD 用 `docker run` 方式重建容器（从现有容器 `docker inspect` 复刻参数）

### 关键经验
- “compose 模式”是锦上添花；生产环境常见会出现“没有 compose 文件/label”的情况，发布链路必须能在 run-mode 下工作

---

## 2) 问题：PROD 上 ragflow_compose-ragflow-cpu-1 启动后很快退出/无法访问 ES（No route to host）

### 现象
- `ragflow_compose-ragflow-cpu-1` 容器启动后退出（或 inspect 看到网络 Endpoint/IP 异常）
- 容器内访问 `http://es01:9200` 报 `No route to host` / 超时
- 但宿主机上 `curl http://<容器IP>:9200` 可能是 OK（不走 docker FORWARD 链）

### 根因（已验证）
PROD 机器存在残留的防火墙 nft 规则（`nft table inet firewalld`），即使 `firewalld` 服务不在运行，规则仍可能挂在 forward hook 上生效：
- 容器间通信依赖 Linux `FORWARD`，被这套规则拦截后，会导致 docker bridge 内部转发失败
- 表现就是容器间互相“路由不通”，RAGFlow 访问 ES/Redis/MySQL 失败

为什么 TEST 没问题但 PROD 有问题？
- 两台机器防火墙历史状态不一致：PROD 曾启用过 firewalld（或被系统/运维工具配置过），残留 nft 规则未清理；TEST 没有这类残留

### 修复（推荐方案 A：一次性根除干扰）
在 PROD 执行（谨慎操作，建议先备份规则）：
1) 备份：`nft list ruleset > /root/nft.ruleset.bak.<时间戳>`
2) 禁用/屏蔽服务：`systemctl disable --now firewalld; systemctl mask firewalld`
3) 删除残留表（如存在）：`nft delete table inet firewalld`（以及可能的 `ip6 firewalld`）

### 验证方法（必须做）
进入 ragflow-cpu 容器执行：
- `curl -sS -m 2 http://es01:9200/ >/dev/null && echo ES_OK || echo ES_FAIL`
并在宿主机确认 ragflow http 可用（本项目默认容器暴露到 80）：
- `curl -fsS http://127.0.0.1:80 >/dev/null && echo RAGFLOW_OK`

---

## 3) 问题：测试环境“文档浏览/知识库”读到了生产数据（或生产读测试）

### 现象
- 测试服务器上的前端/工具，读取知识库时看到的是生产服务器的数据

### 根因
- `/opt/ragflowauth/ragflow_config.json` 的 `base_url` 指向了错误的 RAGFlow（例如测试指向生产 `http://172.30.30.57:9380`）

### 解决策略（强制防呆）
发布/还原链路必须强制校验与修正：
- 发布到 TEST / 还原到 TEST：确保 `base_url` 包含 `172.30.30.58`（或 localhost）
- 发布到 PROD / 同步数据到 PROD：确保 `base_url` 包含 `172.30.30.57`（或 localhost）

关键经验：
- 这个问题不是“发布镜像/复制数据”本身的问题，而是“配置跨环境污染”，必须在工具链路中自动纠正

---

## 4) 问题：删除 PROD 的 ragflowauth-backend/frontend 后，镜像发布无法继续

### 现象
- 工具提示：`PROD containers not found (ragflowauth-backend/frontend). Cannot recreate safely.`

### 根因
- run-mode 的“复刻发布”需要从 PROD 当前容器 `docker inspect` 读取端口/挂载/网络等参数
- 删除容器后，无法复刻

### 解决策略（工具侧：bootstrap 首次部署）
当 PROD 不存在 `ragflowauth-backend/frontend` 时，走 bootstrap：
- 依赖固定目录规范（`/opt/ragflowauth/...`）创建容器
- 仍然使用“从 TEST docker save -> scp -3 -> docker load”的镜像来源，保证版本一致

---

## 5) 关键原则：数据同步/还原必须“停干净再做快照”

原因：
- volumes/db 快照如果在服务仍写入时进行，会导致数据不一致（最坏情况：ES/MySQL/MinIO/Redis 之间版本不一致）

强制要求：
- 数据发布（测试数据 -> 正式）在 TEST 做快照前：必须确认目标服务容器都已停止
- 数据发布在 PROD apply 前：同样必须确认已停止

说明：
- `node-exporter`、`portainer` 不属于业务数据链路，不需要停止

---

## 6) 问题：全量备份勾选“包含 Docker 镜像”，但备份包没有 `images.tar`

### 现象
- 在“数据安全”页面执行全量备份，并勾选“全量备份包含 Docker 镜像（体积较大，但可离线恢复）”
- 备份目录 `migration_pack_*/` 内只有：`auth.db`、`volumes/`，没有 `images.tar`

### 根因（架构点，必须记住）
`docker save -o <path>` **会在“执行 docker CLI 的机器/容器”上写文件**。

当前架构里：
- `ragflowauth-backend` 容器内运行备份代码
- 通过挂载的 `/var/run/docker.sock` 调用 Docker（docker CLI 在容器里执行）

因此 `-o` 的输出路径必须是 **容器内可见且可写** 的路径（例如 `/app/data/backups/...`）。

如果错误地把输出路径“转换成宿主机路径”（例如 `/opt/ragflowauth/backups/...`），容器内往往不存在这个目录：
- 结果：`docker save` 失败，典型报错：`invalid output path: ... no such file or directory`
- 最终备份包不会生成 `images.tar`

### 修复策略（代码侧）
- 镜像备份统一使用容器路径（`/app/data/backups/.../images.tar`）
- “生成成功检查”也必须在容器路径上检查（不要再按 `/opt/...` 去找）
- 若容器内没有 `docker compose`（常见）：需要 fallback 从 `docker ps -a` 推导镜像列表；注意 RAGFlow compose 的容器名通常是 `ragflow_compose-xxx`（中划线 `-`），不要错误按 `ragflow_compose_`（下划线 `_`）过滤，否则会误判“未找到可备份镜像”并跳过 `images.tar`。
 - 镜像备份会占用大量磁盘空间：如果备份目录落在服务器根分区（测试机 50GB，常常只剩几 GB），`docker save` 会因为空间不足无法生成 `images.tar`。推荐把目标目录直接改到大盘（例如 `/mnt/replica/RagflowAuth`）。

### 快速定位方法（只要 30 秒）
在目标服务器执行：
- `docker logs ragflowauth-backend --tail 200 | grep -E \"Saving .* images|docker save|images.tar\"`

关键日志应该能看到：
- `Saving <N> images to /app/data/backups/migration_pack_.../images.tar`
- 如果失败：会打印 docker save 的错误输出

---

## 7) 问题：备份作业轮询 `/api/admin/data-security/backup/jobs/{id}` 偶发 500

### 现象
- 前端轮询作业状态时报：`GET .../backup/jobs/<id> 500 (Internal Server Error)`
- 后端日志里可见 `sqlite3.OperationalError: unable to open database file`

### 推断根因（常见于挂载/IO 波动）
- SQLite 文件在 bind mount 上（`/app/data/auth.db`）
- 备份/还原/容器重建等动作可能造成短时 IO 抖动或路径短暂不可用
- 直接抛异常会导致接口返回 500，前端以为“系统崩了”

### 修复策略（代码侧）
- SQLite 连接增加短暂重试窗口（避免瞬时抖动造成 500）
- 授权依赖（authz）捕获 sqlite OperationalError，返回 **503**（可重试）而不是 500

### 运维建议
- 遇到 503/备份卡住时：先看 `ragflowauth-backend` 日志是否有 DB 打开失败/权限问题
- 同步/还原时尽量减少“频繁 stop/start + 同时轮询”的时间窗口（先做完关键数据步骤再开放 UI 操作）

---

## 8) 工具侧新增“防呆能力”（建议使用）

### 8.1 冒烟测试页签（只读）
工具新增页签：`冒烟测试`，用于一键检查：
- docker 可用、容器列表
- RagflowAuth 后端健康检查（`/health`）
- 前端可访问（HTTP 200/301/302）
- RAGFlow 可访问（9380）
- `/mnt/replica` 挂载状态与磁盘空间

当发布/还原/同步后出现“看起来都启动了，但实际不可用”的情况，先跑一次冒烟测试，能快速确定问题在哪一层。

### 8.2 正式环境版本回滚（保留回滚点 + 一键回滚）
工具在发布页签（测试 -> 正式，镜像）增加了：
- `刷新可回滚版本`：列出正式服务器上可用的历史版本（要求 backend/frontend 同 tag 都存在）
- `回滚到此版本`：用 `docker inspect` 复刻参数重建容器（保持挂载/端口/网络一致），再做健康检查

注意：
- 如果你手动把 `ragflowauth-backend/frontend` 容器删除了，工具无法从 `inspect` 推导运行参数，会提示先走发布/部署流程再回滚。

### 8.3 “清理 Docker 镜像”不会再删除最近版本
之前“清理 Docker 镜像”会删除所有非运行中的 ragflowauth 镜像，导致无法回滚。

工具已调整策略：
- 永远保留：当前运行中的镜像
- 额外保留：最近 N 个 `ragflowauth-backend` 和 `ragflowauth-frontend` 镜像（默认 N=5）

这样即使需要回滚，也不会因为清理镜像而丢失回滚点。
