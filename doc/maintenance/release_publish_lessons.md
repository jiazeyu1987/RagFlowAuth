# 发布（测试 -> 正式）故障复盘与经验教训

更新日期：2026-01-31

本文记录一次“工具发布按钮”失败的根因与改进点，避免后续改代码/改环境后导致发布流程不可用或难以排障。

## 1) 现象（Symptoms）

在工具的“发布”页签点击“从测试发布到正式”后失败，日志提示：

- 找不到测试服务器上的 `docker-compose.yml`（例如：`/opt/ragflowauth/docker-compose.yml: No such file or directory`）
- Docker 容器上缺失 Docker Compose label（`com.docker.compose.project.config_files` / `working_dir` 为空）
- Windows OpenSSH 偶发噪声：`close - IO is still pending on closed socket...`（会污染输出，影响定位）

## 2) 根因（Root Cause）

### 2.1 测试服务器并不是用 docker compose 启动

测试服务器上的 `ragflowauth-backend` / `ragflowauth-frontend` 容器是通过 **`docker run`**（工具的“快速部署/快速重启”）启动的，而不是通过 `docker compose up -d` 启动：

- 因此容器没有 `com.docker.compose.*` 的 label
- 也就无法“自动推导”compose 文件路径
- 同时服务器上也可能根本不存在 `/opt/ragflowauth/docker-compose.yml`

结论：**发布流程如果强依赖 compose 文件，在 docker run 启动模式下必然失败。**

### 2.2 初版发布逻辑对环境做了错误假设

初版“发布”功能默认认为：

- 测试服务器上存在固定位置的 `docker-compose.yml`、`.env`
- 并以此作为“发布到正式的配置来源”

但实际环境是 docker run 模式，配置并不在 compose 文件中，而是隐含在容器的 `docker inspect` 结果里（端口、挂载、环境变量、网络、restart 策略等）。

## 3) 改进（Fix & Improvements）

### 3.1 发布流程支持“docker run 发布模式”

当无法定位 compose 时，发布流程应切换为 “docker run 模式”：

1) 在测试服务器 `docker save` 当前运行的前/后端镜像（确保版本一致）
2) 通过 `scp -3` 把镜像 tar 直接转发到正式服务器（不落盘到本机）
3) 正式服务器 `docker load`
4) 用正式服务器当前容器的 `docker inspect` 生成等价的 `docker run` 参数
5) 删除旧容器后，用测试镜像 tag 重建容器
6) 做 healthcheck（例如 `http://127.0.0.1:8001/health`）通过才算成功

这样发布不再依赖 compose 文件是否存在。

### 3.2 日志必须能“单步定位失败点”

发布日志至少应包含：

- 目标信息：TEST/PROD IP、版本号（tag）、检测到的镜像名
- 关键路径：检测到的 `compose_path` / `env_path`（若存在）
- 每一步执行到哪（step N/M）
- 每个关键动作的参数（如 scp 源/目标路径、最终 docker run 命令）
- 失败时的原始输出（stdout/stderr），并过滤已知噪声行

建议统一以 `[ReleaseFlow] ...` 的形式落盘到 `tool/maintenance/tool_log.log`，方便第二天追查。

### 3.3 未来建议：统一运行方式（推荐）

为了让“发布/回滚/可追溯”更简单、更可靠，建议长期将测试/正式统一到 docker compose（或 Portainer Stack）：

- 让容器带有 `com.docker.compose.project.config_files` 等 label
- 并把 compose 文件固定存放在 `/opt/ragflowauth/docker-compose.yml`（或其它固定路径，但必须一致且可读）

这样发布可以直接“复制 compose + 镜像”进行重启，变更点更清晰。

## 4) 排障 Checklist（失败时先看这里）

1) 测试服务器容器启动方式是什么？
   - 如果 label 为空，基本就是 docker run（或非 compose 启动）
2) 测试服务器是否存在 compose 文件？
   - `ls -l /opt/ragflowauth/docker-compose.yml`（如不存在不要再走 compose 发布模式）
3) 正式服务器当前容器是否存在？
   - `docker ps | grep ragflowauth-`（如果容器名不一致，发布脚本需要同步修改）
4) 正式服务器 network 是否存在？
   - `docker network ls | grep ragflowauth`（如果 run 模式依赖特定 network）
5) 健康检查失败时看什么？
   - `docker logs ragflowauth-backend --tail 200`
   - `docker ps -a | grep ragflowauth`

