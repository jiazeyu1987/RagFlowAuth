# 计划与路线说明

## 1. 这份文件的作用

本仓库当前同时存在三种“计划载体”，它们职责不同：

- `docs/tasks/`
  使用 spec-driven-delivery 流程保存任务级 PRD、测试计划、执行日志和测试报告
- `docs/exec-plans/active/`
  适合保存仍在推进中的跨文件、跨模块执行计划
- `docs/exec-plans/completed/`
  适合归档已经完成的执行计划

## 2. 当前事实状态

截至 2026-04-07，当前工作区中：

- `docs/tasks/` 已经开始承载实际任务工件
- `docs/exec-plans/active/` 和 `docs/exec-plans/completed/` 仅完成基础目录引导
- 旧的 `doc/` 计划树并不在当前工作区内

因此，任何“历史执行路线”都不应被编造成既成事实。

## 3. 推荐使用方式

### 3.1 什么时候用 `docs/tasks/`

当一项工作需要：

- 明确 PRD
- 明确测试计划
- 分阶段执行
- 可回溯的交付证据

优先进入 `docs/tasks/`。

### 3.2 什么时候用 `docs/exec-plans/active/`

当你已经明确要做一项中等以上范围的工程工作，但还不需要单独的 spec-driven 工件，或者想先沉淀人工执行路线时，可以在 `active/` 下新增计划文档。

### 3.3 什么时候移动到 `completed/`

只有在满足以下条件后才建议移动：

- 实现已落地
- 关键验证已完成
- 风险和后续动作已记录

## 4. 当前建议关注项

基于当前仓库状态，最值得形成正式执行计划的主题有：

- 修复 `VALIDATION.md` 与已删除 `doc/e2e` 路径的漂移
- 梳理 `fronted` 目录名与脚本/部署绑定的长期处置方案
- 审视 `approval_workflows` 旧表与 `operation_approval_*` 新表并存带来的迁移边界
- 审视本地存储 token 的长期安全替代方案

## 5. 配套入口

- 活跃计划目录：[docs/exec-plans/active/README.md](docs/exec-plans/active/README.md)
- 已完成计划目录：[docs/exec-plans/completed/README.md](docs/exec-plans/completed/README.md)
- 技术债台账：[docs/exec-plans/tech-debt-tracker.md](docs/exec-plans/tech-debt-tracker.md)
