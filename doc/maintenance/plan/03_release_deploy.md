# 03 发布包 ZIP 一键部署/更新

目标：在 Windows 测试通过后，把一个 ZIP 拷到新机器，执行一次“安装/更新”，完成：

- 部署我们系统（前端+后端）
- （可选）恢复迁移包数据
- （可选）启动 RAGFlow（如果 Docker 里不存在）

## 1) 发布包包含什么

建议把下面内容打进同一个 ZIP（“一个包搞定”）：

- 我们系统：`docker/`、`backend/`、`fronted/`、`data/auth.db`、`ragflow_config.json`
- 运维脚本：`tool/`
- RAGFlow 的 compose 目录：`ragflow_compose/`（必须是“完整目录”，包含它引用的其它 yml/.env）
- 迁移包：`migration_pack/`（用于恢复数据）

## 2) 如何打包

在旧机器运行：

- `python tool/release_packager_ui.py`

建议勾选：

- 包含 RAGFlow（compose 目录）
- 包含迁移包（migration_pack）

## 3) 如何在新机器部署

在新机器解压 ZIP 后运行：

- `python tool/release_installer_ui.py`

安装器会做：

- 解压
- 写入 `ragflow_config.json`（base_url/api_key）
- 写入 `docker/.env`（JWT_SECRET_KEY）
- （可选）恢复迁移包（覆盖 `data/auth.db`，恢复 RAGFlow volumes/镜像）
- （可选）启动 RAGFlow（若 Docker 里没检测到）
- 启动我们系统 compose

## 4) 离线/内网环境注意事项

如果新机器不能访问外网拉镜像：

- 需要迁移包里包含 `ragflow/images/*.tar`（镜像离线导入）
- 否则 `docker compose up` 会在拉镜像阶段失败

## 5) 更新（只更新我们系统）

稳定优先建议：

- 更新时先做一次迁移包备份（防止回滚需要）
- 再用新 ZIP 覆盖部署目录或用“版本化目录/蓝绿方案”（见 `doc/maintenance/06_blue_green.md`）

