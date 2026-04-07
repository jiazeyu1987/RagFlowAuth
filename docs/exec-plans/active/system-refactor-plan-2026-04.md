# 系统重构修改计划

## 文档定位

本文档基于 2026-04-07 对当前仓库前后端代码的重构分析结果编写，目标不是发起系统性重写，而是给出一份可以直接执行的局部重构路线图。

适用范围：

- `backend/`
- `fronted/src/`
- 与以上模块直接相关的测试与文档

不包含范围：

- `tool/maintenance/`
- 部署脚本整体重写
- 目录名 `fronted` 更名
- 非当前热点的广泛 UI 美化

## 总体策略

### 结论

当前系统建议进行重构，但应采用“高风险热点优先、按域分治、逐步收敛”的方式推进，不建议进行系统性重写。

### 重构级别

- 总体级别：局部重构
- 审批、通知、数据安全：高优先级局部重构
- 权限、文档浏览/预览、路由导航：中优先级局部重构

### 执行原则

- 优先拆分职责，不优先追求代码风格统一
- 优先减少规则双写和状态分散，不优先抽象通用框架
- 每个阶段都必须保留现有行为，并补足对应测试
- 禁止以“兼容一切”为理由新增隐式 fallback
- 任何高风险域调整都要先定义验证边界，再动代码

## 为什么放在这里

建议存放目录：`docs/exec-plans/active/`

原因：

- 这份文档属于多模块、多阶段、需要持续推进的执行计划
- 它不是产品规格，不适合放在 `docs/product-specs/`
- 它不是稳定设计原则，不适合放在 `docs/design-docs/`
- 它不是零散问题记录，不适合只写进 `docs/exec-plans/tech-debt-tracker.md`

## 目标

本轮重构的核心目标是：

1. 降低审批、通知、数据安全三条高风险主链路的变更耦合度
2. 收敛前后端权限规则的重复解释
3. 拆解超大前端页面 Hook 和预览组件，降低回归风险
4. 让后续新增需求时只改一个主位置，而不是多个分散位置

## 非目标

以下事项本轮不作为目标：

1. 不做微服务拆分
2. 不做 ORM 替换
3. 不做前端状态管理框架迁移
4. 不做目录级大改名
5. 不做与当前热点无关的大面积样式整理

## 分阶段计划

### 阶段 1：审批域重构

优先级：P0

详细执行计划：

- [审批域重构一期执行计划](./operation-approval-refactor-phase-1.md)

目标：

- 把审批域从“超大服务 + 超大 store”继续拆成可维护的职责块
- 明确审批状态推进、签名、通知、审计、执行之间的边界

主要范围：

- `backend/services/operation_approval/service.py`
- `backend/services/operation_approval/store.py`
- `backend/services/operation_approval/migration_service.py`
- `backend/services/operation_approval/decision_service.py`
- 相关 router 和测试

主要动作：

1. 把 `OperationApprovalService` 收敛为 facade，只保留对外用例编排。
2. 抽离工作流构建与请求步骤物化逻辑，例如 `_build_workflow_steps()`、`_materialize_request_steps()` 进入单独 builder 模块。
3. 将签名动作、审批动作、驳回动作、撤回动作拆成独立 action service，避免 `approve/reject/withdraw` 在同一类中持续膨胀。
4. 把 `OperationApprovalStore` 按实体拆分为多个 repository。
5. 明确事务边界，保证“状态推进 + 事件写入 + 后续动作触发”的边界清晰。
6. 梳理旧审批链路和新审批链路的边界，避免迁移逻辑继续污染主服务。

预期产物：

- `operation_approval` 域内新增 builder/repository/action 类
- `service.py` 明显缩小
- 请求图读写不再都堆在一个 store 中

验证要求：

- 保持审批状态流转测试全绿
- 增加 repository 级 focused tests
- 对创建、审批、驳回、撤回、执行后通知做链路回归

完成标准：

- `service.py` 不再承载主要领域细节
- `store.py` 不再负责整个请求图的所有读写
- 审批动作的核心分支可单独测试

### 阶段 2：数据安全模块治理

优先级：P0

目标：

- 把数据安全模块中的存储职责、环境策略、并发控制拆开
- 降低备份/恢复链路的脆弱性

主要范围：

- `backend/services/data_security/store.py`
- `backend/services/data_security/*`
- `fronted/src/pages/DataSecurity.js`
- `fronted/src/features/dataSecurity/useDataSecurityPage.js`

主要动作：

1. 从 `DataSecurityStore` 中分离锁管理、settings 持久化、job 持久化、restore drill 持久化。
2. 将“标准挂载存在时强制改路径”的环境策略移出 store，改由 service 层做显式策略决策。
3. 修复 backup lock 的释放语义，恢复 owner/lease 概念，避免无条件按名称删锁。
4. 把 `get_active_job_id()` 等吞异常返回默认值的路径改成显式错误上报或可诊断结果。
5. 前端把页面拆成设置面板、备份进度、备份记录、恢复演练几个子组件。
6. 把 `window.prompt` 这类交互从 hook 中尽量移回页面层。

预期产物：

- `data_security` 子域有清晰的 store/service 切分
- 前端页面与业务 hook 的职责更单一

验证要求：

- 备份任务创建、轮询、记录恢复演练、设置变更全链路回归
- 并发锁相关单元测试补齐

完成标准：

- `DataSecurityStore` 不再同时承担环境策略和持久化
- 备份锁语义可被单测清晰验证

### 阶段 3：通知模块拆分

优先级：P0

目标：

- 把通知中心从超级服务拆成多个明确职责的服务

主要范围：

- `backend/services/notification/service.py`
- `backend/services/notification/store.py`
- 相关 API、测试

主要动作：

1. 将通道管理、事件规则管理、任务投递、站内信读取、组织目录同步分离。
2. 把收件人解析与钉钉目录同步移到单独的 recipient directory service。
3. 把 inbox 读状态管理独立为 inbox service。
4. 保留统一 facade 仅作为外部入口，不再承载全部业务细节。

预期产物：

- `notification/service.py` 大幅缩小
- 关键行为按服务维度拆开测试

验证要求：

- 通道保存、规则保存、任务入队、发送、重试、标记已读回归
- 钉钉目录重建单测维持通过

完成标准：

- 单个 notification service 文件不再覆盖整个通知子系统

### 阶段 4：权限模型收敛

优先级：P1

目标：

- 让后端成为唯一权限真相源
- 减少前端对权限语义的二次解释

主要范围：

- `backend/app/core/permission_resolver.py`
- `fronted/src/hooks/useAuth.js`
- `fronted/src/components/PermissionGuard.js`
- `fronted/src/App.js`
- 相关 `features/*` 的权限判断

主要动作：

1. 统一定义 capability 输出结构，明确 resource/action/target 的正式语义。
2. 前端 `useAuth.can()` 改为消费后端规范能力，不再写大量资源类型分支。
3. 补一份权限能力映射说明，明确哪些是前端展示权限，哪些是后端执行权限。
4. 清理容易漂移的前后端重复判断。

预期产物：

- 权限新增时主要只改后端 resolver 和前端一层适配

验证要求：

- 登录后权限快照相关单测通过
- 前端路由守卫、按钮可见性、后端接口权限回归

完成标准：

- 不再需要在多个前端文件新增平行权限分支

### 阶段 5：文档浏览与预览前端拆分

优先级：P1

目标：

- 把文档浏览和预览从超长 Hook/组件拆成稳定子模块

主要范围：

- `fronted/src/features/knowledge/documentBrowser/useDocumentBrowserPage.js`
- `fronted/src/shared/documents/preview/DocumentPreviewModal.js`
- 相关 preview helper 和 API

主要动作：

1. 文档浏览拆为目录状态、选择状态、批量操作、转移操作、最近使用记录几个 Hook。
2. 预览弹窗拆为数据加载层、渲染分发层、预览壳层、不同格式 renderer。
3. OnlyOffice、PDF、HTML、Markdown、图片渲染路径分别独立。
4. 统一对象 URL 生命周期和关闭清理逻辑。

预期产物：

- 新增预览格式时只需要新增 renderer，而不是继续堆在一个 modal 里

验证要求：

- 文档浏览页面测试
- 预览组件测试
- 批量操作和转移操作回归

完成标准：

- `useDocumentBrowserPage` 与 `DocumentPreviewModal` 不再同时承担多条状态机

### 阶段 6：前端路由与导航配置收敛

优先级：P2

目标：

- 降低新增页面时的多处同步修改成本

主要范围：

- `fronted/src/App.js`
- `fronted/src/components/Layout.js`

主要动作：

1. 建立统一 route registry。
2. 用同一份配置驱动路由注册、导航展示、标题映射、权限守卫。
3. 去掉路由和导航两边重复维护 path/title/role 的写法。

预期产物：

- 新增一个页面时，只需要补一条主配置

验证要求：

- 路由跳转和导航展示回归
- 权限相关导航隐藏/显示回归

完成标准：

- 页面路径、标题、导航项不再分散定义

## 暂不执行的内容

以下内容建议记录但暂不纳入当前执行计划：

1. `fronted` 目录更名
2. 运维工具 `tool/maintenance/` 结构调整
3. 全仓库统一样式系统
4. ORM 或数据库层技术栈替换
5. 微服务拆分

## 风险与依赖

### 主要风险

1. 审批、通知、数据安全都属于高风险业务域，回归不足会直接影响真实流程。
2. 当前存在较多历史兼容逻辑和 fallback 路径，拆分过程中容易误删隐式依赖。
3. 前端多个页面已经围绕现有 hook 组织，重构时要避免只换结构不补测试。

### 关键依赖

1. 需要先确认审批旧链路与新链路的边界
2. 需要明确哪些 fallback 是必须保留的现网约束，哪些是历史遗留
3. 需要把验证入口从旧 `doc/e2e` 引用继续收敛到当前 `docs/` 体系

## 验证策略

每个阶段必须按以下顺序验证：

1. 先跑该模块最小单元测试
2. 再跑该子域的集成测试
3. 若涉及共享权限、审批、通知、预览能力，再补一轮跨调用链验证

如果某一阶段无法自动验证，必须在阶段文档或提交说明里写清：

- 缺少什么前提
- 已经人工核对了什么
- 还剩什么风险没有覆盖

## 建议执行顺序

1. 审批域
2. 数据安全
3. 通知
4. 权限模型
5. 文档浏览与预览
6. 路由与导航

## 与技术债台账的关系

这份文档是“执行计划”。

如果后续需要同步沉淀到技术债台账，建议把以下主题补进 `docs/exec-plans/tech-debt-tracker.md`：

- 审批域超级服务与超级 store
- 数据安全 store 职责混杂与锁语义风险
- 通知中心超级服务
- 前后端权限规则双写
- 文档浏览与预览超长状态机

## 后续建议

如果正式启动其中任一阶段，建议再为该阶段单独建一份更细的子计划，内容至少包括：

- 变更文件范围
- 测试范围
- 回滚点
- 风险清单
- 完成判据
