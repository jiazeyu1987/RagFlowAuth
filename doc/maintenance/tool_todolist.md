# tool.py 缺口功能 TODO（对齐 workflow.md）

说明：
- 本文件对应 `doc/maintance/workflow.md` 的 SOP 要求，用于列出 `tool/maintenance/tool.py` 目前未覆盖/需要补齐的能力。
- 仓库中已存在 `doc/maintance/`（注意拼写），但本文件按需求写入 `doc/maintaince/`（本目录为新建）。

---

## P0（建议优先做）

已由前后端实现（无需在 tool.py 里重复实现）：
- 手动触发增量/全量备份 + 进度/日志展示（前端 DataSecurity 页面 → 后端 job 机制）
- 定时增量/全量备份（后端 scheduler v2，cron 表达式）
- 全量备份可包含 `images.tar`（等价于“每周镜像备份”，配合“全量备份时间=每周”）

### 1) “版本/回滚”工作流（保留上一版本并一键切回）
- 现状：工具支持快速部署/重启、清理镜像，但没有“选择历史版本/镜像 -> 回滚”的标准流程；清理镜像功能可能误删回滚所需镜像。
- 目标能力：
  - 记录每次部署：tag、时间、变更说明（可手填）、目标环境（测试/生产）。
  - 一键回滚：选择上一 tag 或指定 tag，重建容器并验证。
  - 镜像清理改为：保留最近 N 个发布版本 + 当前运行版本（避免破坏回滚点）。
- SOP 对应：`doc/maintance/workflow.md:56`、`doc/maintance/workflow.md:66`
- 相关代码参考：部署 `tool/maintenance/tool.py:1658`；清理镜像 `tool/maintenance/tool.py:2123`

---

## P1（建议补齐）

### 2) 测试/生产“冒烟测试”一键执行（Checklist 自动化）
- 现状：SOP 有 checklist，但工具未提供自动跑检查的按钮（目前更多是日志/容器状态查看）。
- 目标能力：
  - 一键 smoke：静态资源（含 `.mjs`）、登录、上传（含 413 检测）、预览、权限校验、备份跑通。
  - 输出可复制的报告（成功/失败/建议动作）。
- SOP 对应：`doc/maintance/workflow.md:41`

### 3) “compose 部署”与“docker run 快速部署”的统一
- 现状：SOP 偏向 docker compose；工具当前快速部署走 `docker run`，与 compose 管理方式不一致。
- 目标能力：
  - 提供两种部署策略可选，并把“生产/测试一致性”固化到流程里：
    - compose：拉取版本/更新镜像/`docker compose up -d`
    - run：保留现有快速部署，但明确适用场景与风险
- SOP 对应：`doc/maintance/workflow.md:37`

### 4) 备份留存策略可配置化
- 现状：工具提供“一键清理 30 天前旧备份”，但 SOP 建议 Daily/Weekly 不同保留策略。
- 目标能力：
  - Daily 保留 14~30 天、Weekly 保留 4~8 周（可配置）。
  - 分类型清理（数据备份 vs 镜像备份）。
- SOP 对应：`doc/maintance/workflow.md:84`
- 相关代码参考：清理旧备份 `tool/maintenance/tool.py:1197`

---

## P2（增强体验/可选）

### 5) 发布记录与审批流（轻量化）
- 目标能力：发布前确认“测试环境已通过”的 tag/commit；发布后自动写一条发布记录（时间、版本、回滚点）。
- SOP 对应：`doc/maintance/workflow.md:60`、`doc/maintance/workflow.md:64`

### 6) 通知（可选）
- 目标能力：备份/部署/还原完成或失败时，通过邮件/企业微信/钉钉/Telegram 等通知。
