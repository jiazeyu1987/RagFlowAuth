# 工具页签：发布（Release）

更新日期：2026-02-01

工具：`tool/maintenance/tool.py`

固定目标（工具内写死，不弹配置）：
- TEST：`172.30.30.58`
- PROD：`172.30.30.57`

本页包含两个发布流 + 一个数据发布流：
1) 本机 -> 测试（镜像）
2) 测试 -> 正式（镜像）
3) 测试 -> 正式（数据：db + volumes）

本地日志：`tool/maintenance/tool_log.log`

---

## A. 本机 -> 测试（发布镜像到 TEST）

按钮：发布本机到测试

目标：
- 把当前本地代码构建的前后端镜像发布到测试服务器
- 发布前/后展示测试服务器版本信息（便于确认发布是否生效）

版本号规则：
- 使用时间戳 tag（例如 `20260131_170801`）
- 后端镜像：`ragflowauth-backend:<tag>`
- 前端镜像：`ragflowauth-frontend:<tag>`

流程（工具内部）：
1) 本地 `docker build` 构建后端镜像
2) 本地 `docker build` 构建前端镜像
3) 本地 `docker save` 打包为一个 tar
4) 本地 `scp` 把 tar 传到 TEST：`/tmp/ragflowauth_release_<tag>.tar`
5) TEST `docker load` 加载镜像
6) TEST 重建容器：
   - 若 TEST 已存在 `ragflowauth-backend/frontend`：从 `docker inspect` 复刻参数并重建（docker run 模式）
   - 若 TEST 不存在（首次部署）：进入 bootstrap（固定目录规范）创建容器
7) TEST backend `/health` 健康检查通过后判定成功

前置条件（bootstrap 会校验）：
- TEST 上必须存在：
  - `/opt/ragflowauth/ragflow_config.json`
  - `/opt/ragflowauth/ragflow_compose`（目录）

常见失败与处理：
- `bootstrap failed: missing required deployment artifacts under app_dir`
  - 说明测试机缺少 `/opt/ragflowauth` 下关键文件/目录，需要先按部署规范准备好

---

## B. 测试 -> 正式（发布镜像到 PROD）

按钮：从测试发布到正式

目标：
- 把 TEST 当前运行的前后端镜像发布到 PROD（保证“测试通过的同一版本”进生产）

流程（工具内部）：
1) 在 TEST 读取当前运行镜像 tag（`docker inspect` 获取容器镜像）
2) TEST `docker save` 导出镜像到 `/tmp/ragflowauth_release_<tag>.tar`
3) 本机 `scp -3` 直连转发 TEST -> PROD（不落地本机）
4) PROD `docker load` 加载镜像
5) PROD 重建容器：
   - 若 PROD 已存在 `ragflowauth-backend/frontend`：从 `docker inspect` 复刻参数并重建
   - 若 PROD 不存在（容器被删/首次部署）：进入 bootstrap（固定目录规范）创建容器
6) PROD backend `/health` 健康检查通过后判定成功

注意：
- 发布镜像并不会自动复制 volumes/db（数据发布是另一个按钮）

---

## C. 测试 -> 正式（发布数据到 PROD：db + volumes）

按钮：从测试发布数据到正式（有二次确认）

目标：
- 把 TEST 的业务数据快照同步到 PROD（auth.db + RAGFlow volumes）
- 发布时自动修正 PROD 的 `ragflow_config.json.base_url` 为 PROD（防止生产读测试）

流程（工具内部，高风险）：
1) PRECHECK：
   - 检查 TEST 的 `ragflow_config.json.base_url` 指向 TEST（或 localhost）
   - 检查 PROD 的 `ragflow_config.json.base_url` 指向 PROD（或 localhost）
2) 在 TEST 停止业务相关容器（做一致性快照）：
   - RagflowAuth：`ragflowauth-backend`、`ragflowauth-frontend`
   - RAGFlow：`ragflow_compose-*`（仅业务栈；`node-exporter`、`portainer` 不需要停止）
   - 关键：必须确认已停止后才进入下一步，否则会中止（避免不一致快照）
3) 在 TEST 导出：
   - `auth.db`
   - RAGFlow volumes（`ragflow_compose_*`：esdata/mysql/minio/redis）
4) 打包成 data tar
5) `scp -3` TEST -> PROD
6) PROD apply：
   - 停止业务相关容器
   - 备份当前数据（防回滚）
   - 还原 auth.db + volumes
7) PROD 重启服务并做健康检查：
   - `docker compose up -d`（在 `/opt/ragflowauth/ragflow_compose`）
   - 检查 `ragflow_compose-ragflow-cpu-1` 是否 running 且网络正常
   - 检查 RAGFlow HTTP
   - 检查 RagflowAuth backend `/health`（会重试）

常见失败与定位：
- 工具 UI “卡住不出日志”
  - 以 `tool/maintenance/tool_log.log` 为准；工具已做逐行日志回调，出现卡住通常是 SSH/scp 阻塞（例如密码交互/网络问题）
- 健康检查失败（`curl: (56) Recv failure: Connection reset by peer`）
  - 需要看 `docker logs ragflowauth-backend`，通常是后端启动失败或依赖不通
