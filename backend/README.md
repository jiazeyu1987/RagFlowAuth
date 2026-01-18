# RagflowAuth Backend (FastAPI + AuthX)

该后端提供：登录鉴权（AuthX JWT）、知识库/Chat/RAGFlow 的权限控制（基于权限组 resolver），以及与 RAGFlow 的对接。

## 快速开始

### 1) 安装依赖

```bash
pip install -r backend/requirements.txt
```

### 2) 初始化数据库

```bash
python -m backend.database.init_db
```

默认管理员：
- 用户名：`admin`
- 密码：`admin123`

### 3) 启动服务

推荐（项目内入口）：

```bash
python -m backend
```

或使用 uvicorn：

```bash
uvicorn backend.app.main:app --host 0.0.0.0 --port 8001 --reload
```
服务地址：`http://localhost:8001`（Swagger：`/docs`）

## 权限模型（重要）

业务权限彻底以 **permission group resolver** 为准，`scopes` 仅作为兼容字段保留（当前接口返回 `scopes: []`，不参与业务授权）。

- 管理员（`role=admin`）：拥有全部知识库可见、所有上传/下载/审核/删除审批权限，以及所有管理端点权限。
 - 非管理员：权限来自「权限组（resolver）」。
- 默认拒绝：用户“无组/组不存在”时，KB/Chat 默认都是 `NONE`，并且 `accessible_kbs` / `accessible_chats` 返回空数组（语义仍表示 `NONE`）。

你可以通过 `GET /api/auth/me` 查看后端计算出的权限快照（KB/Chat 可见范围与 `can_*` 操作权限）。

## 常用 API

### 认证（`/api/auth`）

- `POST /api/auth/login` / `POST /api/auth/refresh` / `POST /api/auth/logout`
- `GET /api/auth/me`

登录响应示例（`scopes` 为兼容字段）：

```json
{
  "access_token": "...",
  "refresh_token": "...",
  "token_type": "bearer",
  "scopes": []
}
```

### 知识库与文档（`/api/knowledge`）

- `POST /api/knowledge/upload`（需要 resolver 允许上传）
- `GET /api/knowledge/documents` / `GET /api/knowledge/stats`（需要 KB 可见）
- `DELETE /api/knowledge/documents/{doc_id}`（需要 resolver 允许删除）
- 审批：`/api/knowledge/documents/{doc_id}/approve|reject`（需要 resolver 允许审核）

### RAGFlow（`/api/ragflow`）

- `GET /api/ragflow/datasets` / `GET /api/ragflow/documents` 等（需要 KB 可见 + resolver 的下载/删除等权限）

### 管理端点（仅管理员）

- `GET/POST/PUT/DELETE /api/users...`
- `GET/POST/DELETE /api/me/kbs...`（按用户 KB 授权管理）
- `GET/POST/DELETE /api/me/chats...`（按用户 Chat 授权管理）

## RAGFlow 配置

后端从仓库根目录读取配置文件：`ragflow_config.json`（也就是 `backend/` 的上一层目录）。

示例：

```json
{
  "api_key": "your-ragflow-api-key",
  "base_url": "http://localhost:9380"
}
```

## 故障排查

- “暂无知识库可用”：优先检查用户是否被分配权限组/按用户授权；其次检查 `ragflow_config.json` 的 `base_url` 是否能连通对应的 RAGFlow 服务。
