# 00 目标与准则（稳定优先）

本文给运维与发布流程定“统一目标”，避免因为习惯不同导致系统不稳定。

## 1) 目标

- 稳定运行：优先保证系统可用、数据不丢、可快速恢复
- 易运维：尽量减少“只能程序员才能做”的操作
- 可迁移：Windows 测试通过后，发布到服务器（私有云）不需要改一堆配置
- 可回滚：升级失败或上线后异常，能快速回到上一版本

## 2) 三条底线（必须遵守）

1) 数据不能丢
   - 任何升级/更新前先做备份（迁移包）
   - 绝不使用 `docker compose down -v`（会删除 volumes，等于删库）

2) 改动可追溯
   - 每次发布产物必须是一个 ZIP（可保存到版本库/归档目录）
   - 迁移包必须保留 `manifest.json`（用于定位是哪一次备份）

3) 操作可重复
   - 所有操作尽量用“固定脚本/固定工具”完成
   - 不依赖手工点来点去、也不依赖某台机器上的临时环境

## 3) 我们维护的边界

- 我们系统（前端+后端）属于同一发布单元：用发布 ZIP 部署/更新
- RAGFlow 属于独立系统：可由 installer 负责“启动/恢复数据”，但升级策略可独立
- 权限/账号/审核：以我们系统 `auth.db` 为准
- 知识库/文档/索引：以 RAGFlow 的 volumes 为准

## 4) 约定的标准流程

### 备份（迁移包）

- 用“数据安全”生成迁移包 `migration_pack_...`
- 迁移包必须包含：
  - `auth.db`
  - `ragflow/volumes/*.tar.gz`
  - （可选但推荐）`ragflow/images/*.tar`（离线部署/内网无外网时）

### 发布（ZIP）

- 用 `tool/release_packager_ui.py` 打出一个发布 ZIP
- 发布 ZIP 建议包含：
  - 我们系统代码与 compose
  - `ragflow_compose/`（完整目录，含它引用的 yml/.env）
  - `migration_pack/`（用于新机一键恢复）

### 部署/更新（服务器）

- 用 `tool/release_installer_ui.py` 一键部署
- 默认顺序（稳定优先）：
  1) 解压 ZIP
  2) 写入配置（`ragflow_config.json`、`docker/.env`）
  3) 先启动一次 RAGFlow 创建 volumes → stop
  4) 恢复迁移包（覆盖 `auth.db` + 恢复 RAGFlow volumes/镜像）
  5) 启动 RAGFlow
  6) 启动我们系统

## 5) 蓝绿（A/B）升级策略（建议）

当你准备把系统部署到私有云并长期运行时，建议采用蓝绿升级（见 `doc/maintenance/06_blue_green.md`）：

- 线上永远保持 A/B 两套
- 更新只在“非活跃槽位”进行
- 验证通过再切换入口，失败不影响当前线上

