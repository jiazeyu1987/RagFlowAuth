# 02 备份与恢复（含 RAGFlow 数据）

## 1) 数据分别存在哪里

### 我们系统

- 数据库：`data/auth.db`
  - 账号、权限、审核记录、备份设置等

### RAGFlow

RAGFlow 的知识库数据不是 `auth.db`，而是在它自己的持久化存储里（Docker Compose 场景通常是 volumes）：

- MySQL volume：元数据/用户/知识库配置
- MinIO volume：原始文件（上传文件对象存储）
- ES/向量引擎 volume：索引/向量/检索数据
- Redis volume：缓存/队列（也建议一起带走）

你在 Docker Desktop 里通常会看到类似：

- `*_mysql_data`
- `*_minio_data`
- `*_esdata01`
- `*_redis_data`

## 2) 备份方式（推荐：迁移包 migration_pack）

你们系统提供“迁移包”备份，产物形如：

```
migration_pack_YYYYMMDD_HHMMSS/
  auth.db
  manifest.json
  ragflow/
    volumes/
      <volume>_YYYYMMDD_HHMMSS.tar.gz
    images/               (可选：离线镜像包)
      ragflow_images_YYYYMMDD_HHMMSS.tar
```

### 如何生成迁移包

在你们系统的前端“数据安全”页面：

- 配置好备份目标目录（本机目录或共享目录）
- 选择 RAGFlow 的 `docker-compose.yml`
- 点击“立即备份”

## 3) 恢复方式（迁移包恢复）

### A. 使用一键部署器自动恢复（推荐）

使用发布包 ZIP 部署时，在 `tool/release_installer_ui.py`：

- 选择发布包 ZIP
- （如果 ZIP 内包含 `migration_pack/` 会自动识别）
- 勾选“部署后自动恢复迁移包”
- 一键部署

### B. 使用手动恢复工具

在新机器运行：

- `python tool/migration_restore_ui.py`
- 选择迁移包目录（`migration_pack_...`）
- 选择项目目录（如 `C:\Users\xxx\RagflowAuth`）
- 点击“数据恢复”

## 4) 关键注意事项（非常重要）

### 1) 恢复前要停止写入

恢复 RAGFlow volumes 前，建议先停止 RAGFlow（避免写入冲突）。

### 2) volume 前缀问题（最容易踩坑）

同一套 RAGFlow，volume 名可能因为 compose 项目名不同而出现不同前缀，例如：

- 旧机器：`docker_mysql_data`
- 新机器：`ragflow_compose_mysql_data`

只要恢复进了“不是 RAGFlow 当前使用的那套 volumes”，就会出现：

- 账号能登录但知识库不对
- 看到“像没恢复”

因此推荐顺序：

1) 在新机器先启动一次 RAGFlow（让它创建 `ragflow_compose_*` 这一套 volumes）
2) 停止 RAGFlow
3) 再把迁移包里的 tar 解压恢复到这套 volumes
4) 再启动 RAGFlow

你们的 `tool/release_installer_ui.py` 已按这个顺序处理。

### 3) 不要用 `down -v`

`docker compose down -v` 会删除 volumes（等于删库），不要使用。

