# Docker 部署（方式 A：后端 Python + 前端 Nginx）

适用：在局域网里把“本系统（前端+后端）”部署到一台新机器上。RAGFlow 仍按你们自己的 `docker-compose.yml` 单独部署（可在同一台机器上）。

## 1) 准备

- 目标机器安装并启动 Docker Desktop（建议使用 Linux containers）
- 把项目目录拷贝到目标机器（包含 `docker/`、`data/`、`ragflow_config.json`）

建议目录结构（项目根目录）：

- `docker/docker-compose.yml`
- `ragflow_config.json`
- `data/auth.db`
- `data/uploads/`（可选）
- `backups/`（推荐：数据安全/迁移包输出目录，避免备份文件落到“容器不可见的宿主机路径”）

## 2) 配置 RAGFlow 地址

编辑项目根目录的 `ragflow_config.json`：

```json
{
  "api_key": "your-ragflow-api-key",
  "base_url": "http://127.0.0.1:9380"
}
```

如果 RAGFlow 在另一台机器，把 `base_url` 改成那台机器 IP，例如：`http://192.168.1.50:9380`。

## 3) 启动本系统（前端+后端）

在项目根目录运行：

```bash
docker compose -f docker/docker-compose.yml up -d --build
```

## 4) 访问

- 前端：`http://目标机器IP:8080`
- 后端：`http://目标机器IP:8001/docs`

## 5) 生产环境要改的

- `JWT_SECRET_KEY`：部署时请在 `docker/.env` 里改成一串随机值（不要用默认值）
