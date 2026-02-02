# 重构计划（Tool + DataSecurity Backup/Release）

更新日期：2026-02-02

目标：在不改变现有业务行为（尤其是备份/还原/发布）的前提下，把代码拆分成可维护模块，并用单元测试/集成测试减少“改代码导致链路失效”的风险。

---

## 已完成（✅）

### ✅ Tool：UI 模块化（低风险拆分）
- 已把各页签 UI 拆到 `tool/maintenance/ui/*`，`tool/maintenance/tool.py` 只保留“入口 + 回调/业务调用”：
  - `release_tab.py`（发布：①本机→测试 ②测试→正式(镜像) ③测试→正式(数据)）
  - `backup_tab.py`、`restore_tab.py`（还原强调“只到测试服务器”）
  - `smoke_tab.py`（新增冒烟测试）
  - `tools_tab.py`、`web_links_tab.py`、`backup_files_tab.py`、`logs_tab.py`
- 已补齐 UI import 单测，避免未来重构破坏入口：
  - `tool/maintenance/tests/test_ui_backup_restore_tabs_import_unit.py`
  - `tool/maintenance/tests/test_ui_release_tab_import_unit.py`

### ✅ 发布链路：可回滚 + 防误删
- 正式环境回滚能力：`tool/maintenance/features/release_rollback.py`
- 发布页签②增加“版本回滚（正式）”
- “清理 Docker 镜像”改为保留回滚点（默认保留最近 N=5 个 backend/frontend 镜像 + 当前运行镜像）

### ✅ 冒烟测试（只读）
- 新增：`tool/maintenance/features/smoke_test.py` + `tool/maintenance/ui/smoke_tab.py`
- 单测：`tool/maintenance/tests/test_smoke_test_unit.py`

### ✅ 备份留存策略可配置
- `备份文件`页签支持“保留天数”输入（默认 30）并清理超过 N 天的备份目录

---

## 下一步（⏳）

### ✅ Milestone C：后端备份流程分步化
- 已落地：把后端 `backup_service.py` 的备份主流程拆分为 steps（precheck/sqlite/volumes/images/settings_snapshot），降低改动风险并提升可观测性。
- 代码位置：`backend/services/data_security/backup_steps/*`
- 单测护栏：`backend/tests/test_data_security_backup_steps_unit.py`

### ✅ Milestone D：Runner/Lock/Cancel 机制完善
- 已落地：支持“协作取消”备份任务（避免卡住/409 后只能重启容器）
  - 后端：`backup_jobs` 增加 cancel 字段，runner/steps 在 checkpoint 与 heartbeat 中检查取消并中断长命令
  - 工具：备份管理页签增加“取消当前备份任务”按钮（SSH + docker exec，无需 HTTP 登录态）

### ⏳ Tool：TaskRunner 抽象（降耦合）
- 目标：统一后台线程执行、UI 安全回调、异常处理（减少 `threading.Thread(...)` 分散在各处）。

---

## 验收标准（最低）
- 单测：`D:\miniconda3\python.exe -m unittest discover tool/maintenance/tests -v` 通过（destructive E2E 可选）
- UI：启动 `D:\miniconda3\python.exe tool/maintenance/tool.py`，发布/还原/冒烟测试/备份文件页签可正常使用
