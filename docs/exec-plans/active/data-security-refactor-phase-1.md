# 数据安全模块重构一期执行计划

## 文档定位

本文档是 [系统重构修改计划](./system-refactor-plan-2026-04.md) 中“阶段 2：数据安全模块治理”的第一期执行版本，用于约束本轮 `data_security` 前后端重构的边界、步骤和验收标准。

放在 `docs/exec-plans/active/` 的原因：

- 这是跨后端 store、调度/运行链路、前端页面和 Hook 的持续执行计划，不是单点技术债备忘录
- 它需要跟随后续 PR、测试结果和阶段状态持续更新，不适合只放进 `docs/tasks/`
- 它是系统重构路线里的分阶段实施文档，粒度高于单次任务工件

## 背景与目标

当前数据安全模块已经具备备份、复制、恢复演练和计划调度能力，但热点代码仍然集中在少数超大文件上：

- `backend/services/data_security/store.py` 同时承载锁管理、设置读写、环境策略、备份任务持久化、恢复演练持久化
- `fronted/src/features/dataSecurity/useDataSecurityPage.js` 同时承载初始加载、轮询、保存设置、保存保留策略、立即备份、恢复演练提交流程
- `fronted/src/pages/DataSecurity.js` 同时承载页面布局、展示规则、格式化、交互确认、局部组件和响应式处理

一期目标不是重写数据安全模块，而是在不改动对外接口和核心行为的前提下，把这条链路从“还能跑但继续加需求很危险”收敛到“职责明确、可继续演进”的状态。

## 当前问题边界

### 1. `DataSecurityStore` 混合了持久化和运行环境策略

当前 `store.py` 不只是读写 SQLite：

- 它直接决定标准副本挂载场景下的路径覆盖策略
- 它同时维护 backup lock、settings、job、restore drill 四类状态
- 它把设置规整、容错和日志写入耦合在同一个类中

这导致后续任意一类需求变更，几乎都要继续修改同一个超大 store。

### 2. 锁语义存在脆弱路径

当前 `_release_lock()` 直接按名称删除锁，owner 检查被移除。这样虽然绕过了 worker 线程/进程交接问题，但也带来两个风险：

- 容易误删非当前任务持有的锁
- stale lock 清理和正常任务释放共享同一条“无条件删除”路径，难以精确验证

### 3. 错误传播不够明确

`get_active_job_id()` 当前吞掉异常并返回 `None`，会把“查询失败”和“确实没有活动任务”混成一种结果，增加运行链路诊断成本。

### 4. 前端 Hook 和页面职责耦合过重

`useDataSecurityPage.js` 当前同时负责：

- 初始加载
- 活动作业轮询
- 设置表单状态
- 变更原因确认
- 备份触发
- 恢复演练表单和提交

`DataSecurity.js` 当前同时负责：

- 大量格式化和状态标签逻辑
- 多块卡片 UI
- 移动端布局细节
- 交互确认入口

这使得任何一个局部需求调整都会放大为 Hook 和页面同时修改。

## 本期范围

### 纳入范围

- `backend/services/data_security/store.py`
- `backend/services/data_security/models.py`
- `backend/services/data_security/*`
- `backend/app/modules/data_security/runner.py`
- `fronted/src/features/dataSecurity/*`
- `fronted/src/pages/DataSecurity.js`
- 数据安全模块相关前后端测试

### 明确不在本期范围

- 不改数据安全 API 路径和返回结构
- 不改备份任务状态枚举、恢复演练结果语义和现有审计字段
- 不引入 fallback、兼容分支或静默降级
- 不扩散到通知中心、权限模型、文档预览等其他系统重构阶段
- 不重做调度器算法和备份业务规则

## 不可破坏的外部契约

### 1. `DataSecurityStore` 继续作为稳定外观存在

虽然内部会拆分，但以下依赖方本期不应感知结构变化：

- `backend/app/dependencies.py`
- `backend/app/modules/data_security/runner.py`
- `backend/services/data_security_scheduler_v2.py`
- 现有后端测试和工具脚本

### 2. 数据安全路由契约保持不变

以下接口的路径、字段语义和返回 envelope 本期保持稳定：

- `GET /admin/data-security/settings`
- `PUT /admin/data-security/settings`
- `POST /admin/data-security/backup/run`
- `POST /admin/data-security/backup/run-full`
- `GET /admin/data-security/backup/jobs`
- `GET /admin/data-security/backup/jobs/{job_id}`
- `POST /admin/data-security/backup/jobs/{job_id}/cancel`
- `POST /admin/data-security/restore-drills`
- `GET /admin/data-security/restore-drills`

### 3. 前端页面现有测试选择器保持稳定

本期优先保留已有 `data-testid`、按钮含义和页面分区名称，确保现有页面/Hook 回归测试继续作为行为基线。

## 目标结构

一期结束后，目标结构如下：

```text
backend/services/data_security/
  store.py                        # 稳定 facade，只保留组合与委托
  settings_policy.py              # 标准挂载环境策略
  repositories/
    __init__.py
    lock_repository.py
    settings_repository.py
    job_repository.py
    restore_drill_repository.py

fronted/src/features/dataSecurity/
  dataSecurityHelpers.js
  useDataSecuritySettingsForm.js
  useDataSecurityJobs.js
  useRestoreDrillForm.js
  components/
    DataSecurityCard.js
    DataSecurityRetentionSection.js
    DataSecuritySettingsSection.js
    DataSecurityActiveJobSection.js
    DataSecurityJobListSection.js
    DataSecurityRestoreDrillsSection.js
```

说明：

- `DataSecurityStore` 继续保留公开方法，但内部退化为 facade
- 环境挂载策略从持久化实现中剥离，收敛到专门策略对象
- 前端页面只负责拼装 UI 和触发交互确认，Hook 拆成更单一的状态单元

## 拆分步骤

### 1. 先拆后端仓储职责，保留 facade

目标：

- 让 `store.py` 不再直接承载四类持久化逻辑

具体动作：

- 新增 `repositories/lock_repository.py`
  - 负责锁获取、按 owner/job 精准释放、stale 清理
- 新增 `repositories/settings_repository.py`
  - 负责设置读取、写入和字段裁剪
- 新增 `repositories/job_repository.py`
  - 负责任务创建、更新、查询、取消状态读写
- 新增 `repositories/restore_drill_repository.py`
  - 负责恢复演练记录写入和读取
- `DataSecurityStore` 保留公开方法，但把实现委托给这些仓储

### 2. 把标准挂载路径策略移出持久化实现

目标：

- 明确“数据库里存什么”和“当前运行环境强制怎么解释这些值”是两层职责

具体动作：

- 新增 `settings_policy.py`
  - 负责标准挂载检测
  - 负责读取时注入运行时覆盖
  - 负责写入前强制收敛受保护字段
- `DataSecurityStore.get_settings()` / `update_settings()` 只做协调，不再直接嵌入具体环境策略

### 3. 收紧 backup lock 释放语义

目标：

- 让 stale lock 清理和正常 job 完成释放走不同、可验证的路径

具体动作：

- 正常释放优先按 `owner` 或 `job_id` 精确删除
- 仅在明确 stale recovery 场景下允许强制删除
- 同步调整 `runner.py`，让 worker 用 `job_id` 释放自己创建的锁
- 补充或调整锁相关单测

### 4. 整理错误传播

目标：

- 让活动任务查询失败不再伪装成“没有活动任务”

具体动作：

- `get_active_job_id()` 取消吞异常的默认返回
- 保持调用链失败即失败，必要时在更高层记录清晰错误

### 5. 拆前端状态单元和展示组件

目标：

- 页面回到“组装 UI”职责，Hook 回到“单一状态域”职责

具体动作：

- 把格式化函数、状态标签、目标路径预览等抽到 `dataSecurityHelpers.js`
- 把设置编辑拆到 `useDataSecuritySettingsForm.js`
- 把任务列表/轮询拆到 `useDataSecurityJobs.js`
- 把恢复演练表单拆到 `useRestoreDrillForm.js`
- 把 `window.prompt` 从 Hook 移到页面层
- 页面按卡片区域拆分成多个展示组件

### 6. 最后补齐测试和工件证据

目标：

- 用现有测试证明这轮重构没有改变行为

具体动作：

- 跑数据安全后端定向测试
- 跑前端 Hook/页面测试
- 把变更范围、命令和结果写入任务工件

## 测试与验证计划

### 后端

- `python -m pytest backend/tests/test_data_security_cancel_unit.py backend/tests/test_data_security_runner_stale_lock.py backend/tests/test_data_security_router_unit.py backend/tests/test_data_security_backup_steps_unit.py backend/tests/test_data_security_path_mapping.py backend/tests/test_data_security_scheduler_v2_unit.py backend/tests/test_data_security_models_unit.py backend/tests/test_config_change_log_unit.py`
- 如涉及恢复演练持久化或审计联动，再补：
  - `python -m pytest backend/tests/test_backup_restore_audit_unit.py backend/tests/test_audit_evidence_export_api_unit.py`

### 前端

- `CI=true npm test -- --runInBand --watchAll=false src/features/dataSecurity/api.test.js src/features/dataSecurity/useDataSecurityPage.test.js src/pages/DataSecurity.test.js`

## 风险与回滚

### 主要风险

- facade 委托改造后，如果有漏转发方法，可能影响依赖注入或调度器
- 锁释放语义收紧后，如果 worker 场景处理不完整，可能造成备份任务被锁死
- 前端拆组件时若改动了测试选择器或页面文案，可能造成回归测试失真

### 回滚策略

- 每次只在 facade 内部替换一类职责，不做跨文件大改
- 优先保持公开方法名和参数不变，必要时通过内部组合退回旧实现
- 前端保持页面顶层结构和 `data-testid` 稳定，降低回滚成本

## 完成标准

满足以下条件即可认为一期完成：

1. `backend/services/data_security/store.py` 显著缩小，并主要承担 facade/委托职责
2. 标准挂载路径策略从持久化实现中剥离到独立策略对象
3. backup lock 释放语义支持正常释放与 stale recovery 区分，并有测试覆盖
4. `useDataSecurityPage.js` 不再同时承载所有状态域，`window.prompt` 已移回页面层
5. `DataSecurity.js` 明显缩小，页面展示按区域拆成独立组件
6. 数据安全相关前后端定向回归测试通过
