# 重构方案清单

## 目标

本清单用于指导本仓库的分阶段重构工作。

原则：

- 先处理真实缺陷风险，再处理结构性复杂度
- 先做局部重构，不做推倒重写
- 每一阶段都必须保证现有行为可回归验证
- 不引入默认 fallback，不通过“兼容分支”掩盖问题

---

## 总体结论

- 重构建议：需要
- 重构优先级：高
- 重构级别：局部重构
- 当前策略：按业务热点分批推进，先后端审批流，再前端用户管理，再处理组织导入和文档浏览器

---

## P0：必须优先处理

### 1. 审批流事务边界收敛

涉及热点：

- `backend/services/operation_approval/service.py`
- `backend/services/operation_approval/store.py`

待办：

- [ ] 梳理 `approve_request`、`reject_request`、`withdraw_request`、`_complete_request_approval`、`_activate_next_step`、`_execute_request` 的完整状态流转
- [ ] 识别所有“单次审批动作”中的数据库写入点
- [ ] 将“审批人状态更新 + 步骤状态更新 + 请求状态更新 + 事件写入”收敛到单事务中
- [ ] 为 store 增加显式事务入口，避免 service 通过多个独立提交拼接流程
- [ ] 将“执行开始 / 执行成功 / 执行失败”三类状态切换分别收敛为明确的事务边界，避免执行阶段产生半更新状态
- [ ] 校验并发审批下的幂等性和状态一致性
- [ ] 补充审批通过、驳回、会签、任一审批、重复点击、并发审批、执行成功、执行失败的单元测试

完成标准：

- 同一审批动作不再拆成多次独立提交
- 并发场景下不会出现 request / step / approver 状态不一致
- 相关测试可以覆盖关键状态分支

### 2. 审批服务职责拆分

涉及热点：

- `backend/services/operation_approval/service.py`

待办：

- [ ] 从 `OperationApprovalService` 中拆出“审批决策”逻辑
- [ ] 拆出“执行落地”逻辑
- [ ] 拆出“通知分发”逻辑
- [ ] 拆出“审计记录”逻辑
- [ ] 将历史迁移逻辑从核心审批服务中剥离
- [ ] 为 request / step / workflow / event 定义更稳定的数据模型，减少裸 `dict` 透传

建议拆分方向：

- `ApprovalDecisionService`
- `ApprovalExecutionService`
- `ApprovalNotificationService`
- `ApprovalAuditService`
- `OperationApprovalMigrationService`

完成标准：

- `OperationApprovalService` 只保留流程编排职责
- 各模块边界清晰，可单独测试
- 核心审批状态机可以被独立阅读和验证

---

## P1：高收益局部重构

### 3. 用户管理前端共享规则收敛

涉及热点：

- `fronted/src/features/users/hooks/useUserManagement.js`

待办：

- [ ] 抽离“创建用户”和“编辑用户策略”的共享 payload 构造函数
- [ ] 抽离公司、部门、直属管理员、权限组、知识库目录等共享校验函数
- [ ] 抽离账号禁用策略的时间解析与校验逻辑
- [ ] 统一错误码到提示文案的映射逻辑
- [ ] 为共享纯函数补充独立测试

建议新增模块：

- `fronted/src/features/users/utils/buildUserPayload.js`
- `fronted/src/features/users/utils/validateUserDraft.js`
- `fronted/src/features/users/utils/loginPolicy.js`

完成标准：

- 创建和编辑不再各自维护一套业务规则
- 修改角色/组织/目录规则时只需要改一个地方
- hook 中明显减少重复判断与重复 payload 拼接

### 4. 用户管理大 hook 拆分

涉及热点：

- `fronted/src/features/users/hooks/useUserManagement.js`

待办：

- [ ] 将列表加载与筛选拆为独立 hook
- [ ] 将创建用户弹窗状态拆为独立 hook
- [ ] 将用户策略弹窗状态拆为独立 hook
- [ ] 将密码重置流程拆为独立 hook
- [ ] 将权限组分配流程拆为独立 hook
- [ ] 将“组织架构 + 知识目录联动”抽为可复用 hook

建议拆分方向：

- `useUserListController`
- `useCreateUserDialog`
- `useUserPolicyDialog`
- `useResetPasswordDialog`
- `useAssignPermissionGroupsDialog`
- `useUserOrgDirectoryBinding`

完成标准：

- 页面主 hook 只做组合，不再承载全部细节
- 单个 hook 状态数和回调数明显下降
- 测试不再依赖超大 harness 才能覆盖主要行为

### 5. 组织架构导入逻辑拆分

涉及热点：

- `backend/services/org_directory/manager.py`
- `backend/services/org_directory/store.py`

待办：

- [ ] 将 Excel 读取与表头校验拆成独立解析层
- [ ] 将“标准化中间模型构建”从 `rebuild_from_excel` 中拆出
- [ ] 将“差量比对计划”拆成独立 planner
- [ ] 将“数据库批量提交”下沉到公开 repo/store 接口
- [ ] 移除 manager 对 store 私有方法 `_get_connection`、`_log` 的直接调用
- [ ] 为导入计划、差量更新、脏数据报错补充测试

建议拆分方向：

- `OrgExcelParser`
- `OrgStructureDiffPlanner`
- `OrgStructureRepository`
- `OrgStructureAuditWriter`

完成标准：

- 导入流程可以分段理解：解析 -> 规划 -> 提交 -> 审计
- manager 不再直接穿透 store 私有实现
- 导入规则变化时不需要修改 500+ 行大函数

---

## P2：建议随后推进

### 6. 文档浏览器按需加载与行为拆层

涉及热点：

- `fronted/src/features/knowledge/documentBrowser/useDocumentBrowserPage.js`

待办：

- [ ] 将数据集树、文档列表、预览、批量选择、转移操作拆为独立职责
- [ ] 把当前“遍历可见数据集自动拉取文档”的策略改为按展开或按进入目录加载
- [ ] 抽离 localStorage 相关逻辑
- [ ] 抽离批量转移与单条转移逻辑
- [ ] 去掉基于 `setInterval` 的路由恢复轮询，改为基于数据加载完成的显式状态驱动
- [ ] 为路由恢复、批量转移、按需加载补充测试

建议拆分方向：

- `useDatasetDirectoryState`
- `useDatasetDocumentLoader`
- `useDocumentSelection`
- `useDocumentTransfers`
- `useRecentDatasetKeywords`

完成标准：

- 文档请求数量与用户实际操作相匹配
- hook 不再同时承担加载、缓存、预览、转移、批量选择全部职责
- 页面状态更容易定位和测试

### 7. 依赖装配中心降耦

涉及热点：

- `backend/app/dependencies.py`

待办：

- [ ] 按业务域拆分依赖构造函数
- [ ] 将启动时副作用从 `create_dependencies` 中挪出
- [ ] 将审批历史迁移改为显式启动步骤
- [ ] 评估 `AppDependencies` 是否可以按域聚合，避免继续横向膨胀

建议拆分方向：

- `build_core_dependencies`
- `build_knowledge_dependencies`
- `build_notification_dependencies`
- `build_operation_approval_dependencies`

完成标准：

- 新模块接入时不再必须修改一个超大装配函数
- 测试可以只实例化最小依赖集
- 启动副作用与对象装配职责分离

### 8. 权限组路由工厂瘦身

涉及热点：

- `backend/app/modules/permission_groups/router.py`

待办：

- [ ] 将资源类接口和 CRUD 类接口拆开
- [ ] 将公共校验与异常翻译抽出
- [ ] 为 folder scope、group scope、resource payload 校验建立更稳定的辅助层

完成标准：

- router 文件不再继续膨胀
- 新增权限组接口时不需要继续堆在单一工厂函数里

---

## 暂不建议重构

以下部分暂不作为本轮重点：

- `backend/app/main.py`
  - 原因：应用工厂、路由注册和生命周期结构总体清晰，不是当前主要风险源
- `fronted/src/features/users/utils/userFilters.js`
  - 原因：职责单一，抽象粒度合适
- `fronted/src/features/download/downloadPageUtils.js`
  - 原因：工具函数清晰，优先级低
- 纯展示型页面文件
  - 原因：虽然部分文件较长，但当前收益远低于优先处理状态机、共享规则和事务边界

---

## 执行顺序建议

1. 先做审批流事务改造
2. 再做审批服务拆分
3. 再做前端用户管理共享规则收敛
4. 再拆前端用户管理大 hook
5. 再拆组织架构导入流程
6. 再优化文档浏览器加载与转移逻辑
7. 最后整理依赖装配和大路由工厂

---

## 每阶段通用验收要求

- [ ] 变更前先补齐关键回归测试
- [ ] 每一阶段只处理一个热点，不并发大面积改动
- [ ] 每次重构后跑对应单元测试
- [ ] 如果涉及前端交互，补充页面级行为测试
- [ ] 如果涉及状态流转，补充异常路径和并发路径测试
- [ ] 不允许通过 silent downgrade 或 fallback 掩盖重构中暴露的问题

---

## 里程碑建议

### 里程碑 A

- 完成 P0 全部任务
- 目标：先把审批流从“高风险复杂代码”降到“可维护复杂代码”

### 里程碑 B

- 完成 P1 全部任务
- 目标：把用户管理和组织导入从“大而全逻辑块”改造成模块化结构

### 里程碑 C

- 完成 P2 全部任务
- 目标：进一步降低页面级 hook 和依赖装配中心的复杂度
