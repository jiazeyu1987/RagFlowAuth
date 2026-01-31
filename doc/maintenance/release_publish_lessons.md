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
