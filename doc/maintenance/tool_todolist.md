# tool.py 功能对齐 TODO（对齐 `doc/maintenance/workflow.md`）

更新日期：2026-02-02

本文用于追踪维护工具 `tool/maintenance/tool.py` 需要补齐/已落地的能力，避免后续改动导致发布/备份/还原链路失效。

固定环境（工具内写死，不弹窗）：
- TEST：`172.30.30.58`
- PROD：`172.30.30.57`
- Windows 共享：`//192.168.112.72/backup`
- 服务器挂载点：`/mnt/replica`，项目子目录固定：`/mnt/replica/RagflowAuth`

---

## 已完成（✅）

### ✅ 1) “版本回滚”工作流（PROD）
- 已落地：发布页签②增加“版本回滚（正式）”
  - 刷新可回滚版本：列出 PROD 上 backend/frontend 同 tag 镜像
  - 一键回滚：按 `docker inspect` 复刻参数重建容器 + `/health` 检查
- 同时增强：清理镜像不会再删除回滚点
  - 默认保留最近 N(=5) 个 `ragflowauth-backend`/`ragflowauth-frontend` 镜像 + 当前运行镜像

### ✅ 2) 测试/生产“冒烟测试”一键执行（只读）
- 已落地：新增页签 `冒烟测试`
- 覆盖检查：docker 可用、容器状态、后端 `/health`、前端/ RAGFlow HTTP、`/mnt/replica` 挂载与空间

### ✅ 3) 备份留存策略“可配置化”
- 已落地：`备份文件`页签支持输入“保留天数”（默认 30）并清理超过 N 天的备份目录

### ✅ 3.1) 取消当前备份任务（解除 409/卡住）
- 已落地：`备份管理`页签增加“取消当前备份任务”按钮
- 用途：当备份长期卡住（例如卡在 volume 或镜像保存）或再次触发返回 409（Conflict）时，可释放占用并允许下一次备份启动
- 机制：协作取消（best-effort），长命令会在 heartbeat 检查点中断；状态会从 `running/queued` -> `canceling` -> `canceled`

### ✅ 4) compose 部署与 docker run 快速部署共存（工具侧）
- 已落地：发布链路优先走 compose 检测；当 compose 不可用/label 为空时，自动 fallback 为 run-mode（从 `docker inspect` 复刻参数重建容器）
- 已落地：TEST/PROD `ragflow_config.json.base_url` 防呆校验与自动修正（防止跨环境读错知识库）

### ✅ 5) 工具 UI 模块化（降低改动风险）
- 已落地：UI 拆分到 `tool/maintenance/ui/*`
  - `release_tab.py`、`backup_tab.py`、`restore_tab.py`、`smoke_tab.py`、`tools_tab.py`、`web_links_tab.py`、`backup_files_tab.py`、`logs_tab.py`
- 已落地：对应 import 单测，防止未来重构破坏入口

### ✅ 6) “发布记录”可视化（只读）
- 已落地：工具会把成功的发布/数据同步/回滚记录追加到 `doc/maintenance/release_history.md`
- 已落地：发布页签新增“发布记录”子页签：支持刷新查看 + 复制到剪贴板（便于粘贴到运维群/工单）

---

## 待办（⏳）

### ⏳ B) 自动化通知（可选）
- 目标：备份/发布/还原成功或失败时，支持通知（企业微信/钉钉/邮件等）
- 说明：需要明确通知渠道与凭据管理方式（否则不建议硬编码）

---

## 参考文档（必读）
- 发布/数据同步问题复盘：`doc/maintenance/release_publish_lessons.md`
- 镜像备份问题复盘：`doc/maintenance/backup_images_lessons.md`
- 工具页签说明：`doc/maintenance/tool_release.md`、`doc/maintenance/tool_backup_restore.md`
