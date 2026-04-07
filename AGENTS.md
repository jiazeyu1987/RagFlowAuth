# AGENTS.md

本文件用于给进入本仓库的编码代理提供仓库级事实与工作约束。内容以当前工作树为准，不按历史命名或理想结构臆测。

## 目标

- 做最小、安全、可验证的修改。
- 先按真实代码结构定位归属，再决定落点。
- 文档与代码都以当前仓库现状为准，不擅自“纠正”历史命名。

## 基本约束

- 不要引入未被明确要求的 fallback、兼容分支或静默降级。
- 缺少前提时直接说明，不要伪造成功路径。
- 不要因为目录名看起来像拼写错误就擅自重命名。
- 不要把历史上可能存在的 `doc/` 结构当成当前事实；当前主文档根目录是 `docs/`。

## 当前真实文档结构

仓库根目录下已经存在的总览型文档：

- `ARCHITECTURE.md`
- `DESIGN.md`
- `FRONTEND.md`
- `PLANS.md`
- `PRODUCT_SENSE.md`
- `QUALITY_SCORE.md`
- `RELIABILITY.md`
- `SECURITY.md`
- `VALIDATION.md`

`docs/` 目录是当前主文档树，实际结构如下：

```text
docs/
├── design-docs/
│   ├── index.md
│   └── core-beliefs.md
├── exec-plans/
│   ├── active/
│   │   └── README.md
│   ├── completed/
│   │   └── README.md
│   └── tech-debt-tracker.md
├── generated/
│   └── db-schema.md
├── maintance/
│   ├── backup.md
│   ├── publish.md
│   └── regression.md
├── product-specs/
│   ├── index.md
│   └── new-user-onboarding.md
├── references/
│   ├── design-system-reference-llms.txt
│   ├── nixpacks-llms.txt
│   └── uv-llms.txt
└── tasks/
    └── <spec-driven-delivery task dirs>
```

文档落点约定：

- 根目录 `*.md`：项目总览、架构、前端、可靠性、安全、质量、计划。
- `docs/design-docs/`：设计原则与设计层说明。
- `docs/product-specs/`：产品规格与上手路径。
- `docs/exec-plans/`：执行计划与技术债。
- `docs/generated/`：从代码或数据结构整理出的生成型文档。
- `docs/maintance/`：当前维护文档，仅包含发布、回归、备份三类主题。
- `docs/tasks/`：spec-driven-delivery 任务工件目录。

## 文档相关注意事项

- `docs/maintance/` 的目录名当前就是 `maintance`，不要擅自改成 `maintenance`，除非用户明确要求迁移。
- 当前 spec-driven-delivery 的任务根目录是 `docs/tasks/`，不是 `doc/tasks/`。
- 维护工具当前仍会把发布历史写到 `doc/maintenance/release_history.md`；这是现有代码事实，不代表主文档树已经迁回 `doc/`。
- 更新文档时，优先把内容写到拥有该主题的目录，不要把运维内容散落到根目录总览文档里。

## 当前真实代码结构

### 后端

后端源码根目录是 `backend/`，当前主要分层如下：

```text
backend/
├── app/
│   ├── main.py
│   ├── dependencies.py
│   ├── core/
│   └── modules/
├── core/
├── database/
├── migrations/
├── models/
├── runtime/
├── scripts/
├── services/
└── tests/
```

后端事实约定：

- FastAPI 入口：`backend/app/main.py`
- 依赖装配入口：`backend/app/dependencies.py`
- 认证、鉴权、配置、权限解析等核心逻辑：`backend/app/core/`
- 业务模块路由：`backend/app/modules/<module>/router.py`
- 数据库 schema、路径与租户相关逻辑：`backend/database/`
- 服务层与后台任务逻辑：`backend/services/`
- 后端测试：`backend/tests/`

如果改后端接口、权限或共享行为，必须同时检查：

- `backend/app/main.py` 的注册关系
- `backend/app/dependencies.py` 的依赖注入
- 对应 `backend/app/modules/*`
- 下游服务与测试

### 前端

前端源码根目录当前真实名称是 `fronted/`，不是 `frontend/`。不要静默修正。

```text
fronted/
├── public/
├── src/
│   ├── App.js
│   ├── api/
│   ├── components/
│   ├── config/
│   ├── constants/
│   ├── features/
│   ├── hooks/
│   ├── pages/
│   └── shared/
├── e2e/
├── build/
└── playwright-report/
```

前端事实约定：

- 应用入口：`fronted/src/App.js`
- 认证状态入口：`fronted/src/hooks/useAuth.js`
- 权限守卫：`fronted/src/components/PermissionGuard.js`
- 主布局：`fronted/src/components/Layout.js`
- 共享 HTTP 层：`fronted/src/shared/http/httpClient.js`
- 页面层：`fronted/src/pages/`
- 业务分组：`fronted/src/features/`
- 前端 E2E 目录：`fronted/e2e/`

工作时优先在 `src/features/`、`src/pages/`、`src/shared/` 的真实归属层修改，不要把所有逻辑都堆进 `App.js` 或 `components/`。

### 运维工具

运维相关真实代码集中在 `tool/maintenance/`，不是零散脚本。

```text
tool/maintenance/
├── tool.py
├── core/
├── controllers/
├── exports/
├── features/
├── scripts/
├── tests/
└── ui/
```

职责分层：

- `tool.py`：桌面工具入口与窗口装配
- `core/`：常量、环境、SSH、任务运行、base_url guard 等基础设施
- `ui/`：页签 UI 定义
- `controllers/`：UI 到具体动作的协调层
- `features/`：发布、回滚、冒烟、备份等相对稳定的功能实现
- `scripts/`：PowerShell/批处理脚本
- `tests/`：运维工具相关单测与集成测试

当前维护工具相关事实：

- 测试服务器 IP：`172.30.30.58`
- 正式服务器 IP：`172.30.30.57`
- 默认 SSH 用户：`root`
- 远端应用目录：`/opt/ragflowauth`
- 本地备份目录：`D:\datas\RagflowAuth`

## 其他仓库事实

- `data/auth.db` 当前存在，可用于 schema 或运行态 spot-check。
- `ragflow_config.json` 位于仓库根目录。
- `tool/scripts/` 与 `scripts/` 都存在；改脚本前先确认归属，不要混放。
- `output/`、`build/`、`playwright-report/`、`node_modules/` 更偏产物或运行输出，修改前先确认是否真的应该入手这些目录。

## 修改建议

- 先改拥有行为的模块，再补与之对应的文档。
- 如果要更新结构说明，优先同步 `AGENTS.md`、根目录总览文档与 `docs/` 下对应专题文档。
- 如果某个路径是当前真实路径但命名不理想，例如 `fronted/` 或 `docs/maintance/`，文档里应如实写明，而不是私自“修正”。
