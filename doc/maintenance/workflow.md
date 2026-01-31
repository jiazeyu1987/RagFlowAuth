# 工作、测试、发布与备份流程（SOP）

更新日期：2026-02-01

适用物理架构：
- 本地开发机：Windows（用于开发调试 + 本机发布到测试）
- 测试服务器（TEST）：`http://172.30.30.58/`（Docker 环境）
- 正式服务器（PROD）：`http://172.30.30.57/`（Docker 环境）

账号/密码等敏感信息统一放在：`doc/maintenance/current/server_config.md`

工具入口：`tool/maintenance/tool.py`（本地 Windows 上运行，通过 SSH 操作服务器）

相关细节文档：
- 工具发布页签说明：`doc/maintenance/tool_release.md`
- 工具备份/还原页签说明：`doc/maintenance/tool_backup_restore.md`
- 发布/同步问题复盘：`doc/maintenance/release_publish_lessons.md`

---

## 1. 本地开发（Windows）

目标：快速迭代与自测，不影响服务器环境。

建议流程：
1) 拉取/更新代码
2) 本地跑前端/后端（或联调测试后端）
3) 自测通过后，再进入测试服务器验证

本地自测清单（最小集）：
- 登录/刷新 token
- 文档上传（大文件/多文件/格式校验）
- 文档预览（pdf/docx/xlsx/csv）
- 管理端功能（用户管理/改密等）

---

## 2. 测试服务器验证（Staging/Test）

目标：在“与生产一致”的 Docker 环境验证功能、配置与依赖。

建议流程（每次准备进生产前）：
1) 将版本发布到测试服务器（推荐使用工具“本机 -> 测试”，保证可追溯版本号）
2) 冒烟测试（smoke）
3) 通过后，才能进入生产发布

冒烟测试清单（建议固定 checklist）：
- 页面可访问、静态资源加载无报错（含 `.mjs` MIME）
- 登录正常（无 500；数据库可用）
- 上传正常（无 413；大小限制符合预期）
- 预览正常（pdf/docx/xlsx/csv）
- 审核/下载/删除权限校验正常
- 备份功能能跑通一次（产出 migration_pack 目录 / `replication_manifest.json`）

---

## 3. 生产服务器发布（Production）

目标：最小风险上线，支持快速回滚。

核心原则：
- 生产只发布“已在测试验证通过”的同一版本（同 tag/镜像）
- 保留上一版可用镜像与配置，出问题可快速回滚
- 发布前后必须确认 `ragflow_config.json` 的 `base_url` 指向本机环境（防止测试读生产/生产读测试）

建议流程（一次生产发布）：
1) 在测试服务器确认版本已验证通过（记录工具展示的版本号/镜像 tag）
2) 用工具执行“测试 -> 正式（镜像发布）”
3) 发布后做生产冒烟测试（同测试清单，但更保守）
4) 记录发布信息（时间/版本/变更点/回滚点）

回滚策略（建议固定）：
- 保留上一版镜像 tag（不要删除旧镜像）
- 如遇严重问题：将上一版镜像重新发布到生产（或手工 docker run/compose 切回），再重启服务

---

## 4. 定时备份策略

目标：满足“可恢复”，而不是“有备份文件”。

建议备份内容分层：
- 每日数据备份（Daily）：
  - `auth.db`
  - RAGFlow volumes（MySQL/ES/MinIO/Redis）
  - 关键配置文件（`ragflow_config.json`、compose/.env 等）
- 每周镜像备份（Weekly）：
  - `docker save` 导出的 images 包（体积大，频率低）

建议保留策略（示例）：
- Daily：保留 14~30 天
- Weekly：保留 4~8 周

恢复演练（强烈建议）：
- 每月至少抽查 1 次：从备份恢复到测试环境并验证：可登录/可查询/可预览/可上传

---

## 5. 重要防呆（强制）

1) 数据同步/还原必须“停干净再做快照”
- 快照前必须确认目标业务容器都已停止（RagflowAuth + RAGFlow compose）
- `node-exporter`、`portainer` 不属于业务链路，不需要停止

2) base_url 必须与环境一致
- TEST：`base_url` 必须包含 `172.30.30.58`（或 localhost）
- PROD：`base_url` 必须包含 `172.30.30.57`（或 localhost）
