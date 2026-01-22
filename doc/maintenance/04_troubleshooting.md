# 04 常见问题排查

本页按“你看到的报错/现象”来找原因与处理方法。

## 1) 前端登录报 CORS / localhost:8001

现象：

- 浏览器提示从 `http://x.x.x.x:8080` 访问 `http://localhost:8001` 被拦截

原因：

- 前端被打包进了 `REACT_APP_AUTH_URL=http://localhost:8001`

处理：

- 重新构建前端镜像并部署（使用新发布包即可）

## 2) Docker Desktop Linux 引擎 pipe 找不到

现象：

- `open //./pipe/dockerDesktopLinuxEngine: The system cannot find the file specified`

原因：

- Docker Desktop 未启动或当前是 Windows containers

处理：

- 打开 Docker Desktop，等待运行
- 切换到 Linux containers

## 3) RAGFlow 启动报容器名冲突

现象：

- `Conflict. The container name "/ragflow_compose-es01-1" is already in use`

处理：

在 `ragflow_compose` 目录运行：

- `docker compose down`
- 再 `docker compose up -d`

## 4) “账号能登录但知识库不对/像没恢复”

最常见原因：

- 迁移包恢复进了 `docker_*`，但 RAGFlow 实际使用的是 `ragflow_compose_*`（或反过来）

处理建议：

- 先启动一次 RAGFlow 创建 volumes → stop → 恢复迁移包 → start
- 使用新版 `tool/release_installer_ui.py`（已按正确顺序处理）

## 5) RAGFlow compose 缺文件（docker-compose-base.yml / .env）

现象：

- 启动时报缺 `docker-compose-base.yml` 或环境变量缺失

原因：

- 只拷了一个 `docker-compose.yml`，但它引用了同目录其他文件

处理：

- 打包/拷贝“完整的 RAGFlow compose 目录”，不要只复制一个 yml 文件

