# 运维文档（Maintenance）

本目录面向“运维/管理员”角色，目标是：稳定运行、可备份可恢复、可升级可回滚、可排障。

## 目录

- `doc/maintenance/00_goals_principles.md`：我们的目标与准则（稳定优先）
- `doc/maintenance/01_prerequisites.md`：服务器与网络要求（内网部署优先）
- `doc/maintenance/02_backup_restore.md`：备份/恢复（含 RAGFlow 数据）
- `doc/maintenance/03_release_deploy.md`：发布包 ZIP 一键部署/更新
- `doc/maintenance/04_troubleshooting.md`：常见问题排查（按症状找答案）
- `doc/maintenance/05_ops_tooling.md`：推荐的开源运维工具（Portainer 等）
- `doc/maintenance/06_blue_green.md`：A/B（蓝绿）升级方案（稳定优先）
- `doc/maintenance/07_daily_checklist.md`：运维每日工作清单（建议）
- `doc/maintenance/08_centos8_notes.md`：CentOS 8.1 实机部署注意事项（必读）

## 关键概念（先看这三条）

1) 我们系统的账号/权限数据在 `data/auth.db`（SQLite）。
2) RAGFlow 的知识库/文档/索引数据在它自己的 Docker volumes（常见四个：MySQL/MinIO/ES/Redis）。
3) 最稳的迁移方式：停服务 → 迁移包（`migration_pack`）备份 → 新机恢复 → 启动服务。
