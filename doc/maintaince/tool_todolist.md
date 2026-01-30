# tool.py 缺口功能 TODO（对齐 workflow.md）

说明：
- 本文件对应 `doc/maintance/workflow.md` 的 SOP 要求，用于列出 `tool/maintenance/tool.py` 目前未覆盖/需要补齐的能力。
- 仓库中已存在 `doc/maintance/`（注意拼写），但本文件按需求写入 `doc/maintaince/`（本目录为新建）。

---

## P0（建议优先做）

### 1) 一键“立即备份”（真正执行备份，而不只是查看/删除文件）
- 现状：工具支持查看备份目录、清理旧备份、管理备份文件，但没有触发后端“立即备份”的按钮与进度展示。
- 目标能力：
  - 在工具内触发：全量/增量备份（对应 SOP 的“备份功能能跑通一次”）。
  - 展示：任务状态/日志、生成的 migration_pack 目录与 `replication_manifest.json`。
  - 可选：备份完成后自动同步到 `/mnt/replica/...`（如果已挂载 Windows 共享）。
- SOP 对应：`doc/maintance/workflow.md:47`、`doc/maintance/workflow.md:72`
- 相关代码参考：备份文件管理在 `tool/maintenance/tool.py:694`、`tool/maintenance/tool.py:931`；目前仅有“数据安全页面立即备份”的文字提示但无实现：`tool/maintenance/tool.py:2638`

### 2) “每周镜像备份”能力（在服务器侧生成/管理 weekly images 包）
- 现状：快速部署流程里有 `docker save`，但那是为了部署传输镜像，不是“备份到指定目录并做保留策略”的镜像备份。
- 目标能力：
  - 在服务器端执行 `docker save`，输出到稳定目录（最好容器/宿主都可见或直接到 `/mnt/replica`）。
  - 按周命名与保留：4~8 周（可配置）。
- SOP 对应：`doc/maintance/workflow.md:81`
- 相关代码参考：快速部署导出镜像在 `tool/maintenance/tool.py:1729`

### 3) “版本/回滚”工作流（保留上一版本并一键切回）
- 现状：工具支持快速部署/重启、清理镜像，但没有“选择历史版本/镜像 -> 回滚”的标准流程；清理镜像功能可能误删回滚所需镜像。
- 目标能力：
  - 记录每次部署：tag、时间、变更说明（可手填）、目标环境（测试/生产）。
  - 一键回滚：选择上一 tag 或指定 tag，重建容器并验证。
  - 镜像清理改为：保留最近 N 个发布版本 + 当前运行版本（避免破坏回滚点）。
- SOP 对应：`doc/maintance/workflow.md:56`、`doc/maintance/workflow.md:66`
- 相关代码参考：部署 `tool/maintenance/tool.py:1658`；清理镜像 `tool/maintenance/tool.py:2123`

---

## P1（建议补齐）

### 4) 测试/生产“冒烟测试”一键执行（Checklist 自动化）
- 现状：SOP 有 checklist，但工具未提供自动跑检查的按钮（目前更多是日志/容器状态查看）。
- 目标能力：
  - 一键 smoke：静态资源（含 `.mjs`）、登录、上传（含 413 检测）、预览、权限校验、备份跑通。
  - 输出可复制的报告（成功/失败/建议动作）。
- SOP 对应：`doc/maintance/workflow.md:41`

### 5) “compose 部署”与“docker run 快速部署”的统一
- 现状：SOP 偏向 docker compose；工具当前快速部署走 `docker run`，与 compose 管理方式不一致。
- 目标能力：
  - 提供两种部署策略可选，并把“生产/测试一致性”固化到流程里：
    - compose：拉取版本/更新镜像/`docker compose up -d`
    - run：保留现有快速部署，但明确适用场景与风险
- SOP 对应：`doc/maintance/workflow.md:37`

### 6) 备份留存策略可配置化
- 现状：工具提供“一键清理 30 天前旧备份”，但 SOP 建议 Daily/Weekly 不同保留策略。
- 目标能力：
  - Daily 保留 14~30 天、Weekly 保留 4~8 周（可配置）。
  - 分类型清理（数据备份 vs 镜像备份）。
- SOP 对应：`doc/maintance/workflow.md:84`
- 相关代码参考：清理旧备份 `tool/maintenance/tool.py:1197`

---

## P2（增强体验/可选）

### 7) 发布记录与审批流（轻量化）
- 目标能力：发布前确认“测试环境已通过”的 tag/commit；发布后自动写一条发布记录（时间、版本、回滚点）。
- SOP 对应：`doc/maintance/workflow.md:60`、`doc/maintance/workflow.md:64`

### 8) 通知（可选）
- 目标能力：备份/部署/还原完成或失败时，通过邮件/企业微信/钉钉/Telegram 等通知。
