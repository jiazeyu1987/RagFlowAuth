# RagflowAuth Backend (FastAPI + AuthX)

本后端提供：登录鉴权（AuthX JWT）、知识库/Chat/RAGFlow 的权限控制（以权限组 resolver 为准）、以及对接 RAGFlow 的接口。

## 快速开始

### 1) 安装依赖

```bash
pip install -r backend/requirements.txt
```

### 2) 初始化数据库

```bash
python -m backend init-db
```

默认管理员：
- 用户名：`admin`
- 密码：`admin123`

### 3) 启动服务

推荐（项目内入口）：

```bash
python -m backend
```

如果你之前使用过旧版本（数据在 `backend/data/`），先执行一次迁移：

```bash
python -m backend migrate-data-dir
```

## 备份（推荐）

你需要同时备份两部分：
1) RAGFlow（Docker Compose）：按官方迁移/备份文档执行。
2) 本项目自己的数据库：`data/auth.db`（用户/权限组/审批/审计等）。

本项目提供一键备份命令（支持备份到另一台电脑的共享目录）：

1) 生成配置文件（只需要做一次）：
```bash
python -m backend init-backup
```
然后用记事本打开项目根目录的 `backup_config.json`，把 `target_dir` 改成另一台电脑的共享目录（例如 `\\\\192.168.1.100\\backup\\RagflowAuth`）。

2) 立刻执行一次备份：
```bash
python -m backend backup
```

也可以直接双击项目根目录的 `backup_now.bat`。

### 备份（带 UI，单文件）

如果你希望“填 IP/方式 -> 点按钮生成迁移包（包含 auth.db + 可选 RAGFlow）”，可以使用项目根目录的单文件工具：

```bash
python backup_ui.py
```

第一次打开后可点击“保存配置”，会生成 `backup_ui_config.json`，以后直接打开就会自动加载。

UI 里你可以选择：
- 本地输出到某个文件夹
- 或者填写“目标电脑 IP + 共享名 + 子目录”，输出到网络共享路径（UNC）

如果自动找不到 RAGFlow 的 `docker-compose.yml`，请在 UI 里点击“选择...”手动指定。

或使用 uvicorn：

```bash
uvicorn backend.app.main:app --host 0.0.0.0 --port 8001 --reload
```

服务地址：`http://localhost:8001`（Swagger：`/docs`）

## 权限模型（重要）

业务权限彻底以 **permission group resolver** 为准，`scopes` 仅作为兼容字段保留（接口返回 `scopes: []`，不参与业务授权）。

- 管理员（`role=admin`）：拥有全部知识库可见、所有上传/审核/下载/删除权限，以及所有管理端点权限。
- 非管理员：权限仅来自“权限组（resolver）”。
- 默认拒绝：用户“无组/组不存在”时，KB/Chat 默认为 `NONE`，并且 `accessible_kbs` / `accessible_chats` 返回空数组（语义表示 `NONE`）。

历史的“按用户单独授权”表（`user_kb_permissions` / `user_chat_permissions`）已从业务链路中移除，不再参与授权决策；现仅建议作为历史/审计数据保留（后端不会读取/写入它们）。

你可以通过 `GET /api/auth/me` 查看后端计算出的权限快照（KB/Chat 可见范围 + `can_*` 操作权限）。

## RAGFlow 配置

后端从仓库根目录读取：`ragflow_config.json`（也就是 `backend/` 的上一层目录）。

示例：
```json
{
  "api_key": "your-ragflow-api-key",
  "base_url": "http://127.0.0.1:9380"
}
```

## 调试日志（PERMDBG）

权限排查日志使用 `[PERMDBG]` 前缀，可通过环境变量开关：
- 开启：`PERMDBG_ENABLED=true`
- 关闭（默认）：不输出 `[PERMDBG]` 日志

## 常见问题

- “暂无知识库可用”：优先检查用户是否被分配正确的权限组；其次检查 `ragflow_config.json` 的 `base_url` 是否连通 RAGFlow 服务。
