# 给其他 LLM 的 Playwright 用例编写指南（RagflowAuth）

目标：让“不了解本仓库”的模型，也能按同一套规则持续新增/维护 Playwright E2E 用例，且尽量稳定、可回归、可扩展。

本指南只讲“仓库内约定与落地做法”，不讲 Playwright 基础教程。

---

## 1) 仓库结构（你需要先知道这些）

- 前端：`fronted/`（React）
- Playwright：`fronted/e2e/`
  - 用例：`fronted/e2e/tests/*.spec.js`
  - helpers：`fronted/e2e/helpers/*.js`
  - fixtures：`fronted/e2e/fixtures/`
  - 登录态（storageState）：`fronted/e2e/.auth/*.json`
  - 全局 setup：`fronted/e2e/global-setup.js`
- Playwright 配置：`fronted/playwright.config.js`
- 文档索引：
  - 已实现清单：`doc/test/implemented/`
  - 待补齐清单：`doc/test/pending/`
  - API 覆盖面映射：`doc/test/implemented/api_surface.md`、`doc/test/pending/api_surface.md`

---

## 2) 怎么运行（必须能自测）

在 `fronted/` 下：

- 回归（默认跳过 `@integration`）：`npm run e2e`
- 冒烟：`npm run e2e:smoke`
- 集成（真实后端/外部依赖，串行）：`npm run e2e:integration`
- 跑单个 spec：`npm run e2e -- e2e/tests/<name>.spec.js`
- 看报告：`npm run e2e:report`

约定：
- 所有依赖真实后端/外部系统（RAGFlow datasets、备份落盘等）的用例都要打 `@integration`
- `npm run e2e` 默认应“稳定可跑”，不要引入外部依赖波动

---

## 3) 分层策略（先决定写哪一层）

### 3.1 `@smoke`
只测最关键闭环（登录/基础路由/上传/审核/浏览），少而稳。

### 3.2 `@regression`（默认主力）
主要用 mock（`page.route`）控制数据与错误态，覆盖：
- 表单校验
- 空数据
- 403/404/500/超时
- 取消分支（confirm/prompt dismiss）

### 3.3 `@integration`
验证真实链路（写库/写审计/调用外部依赖），必须具备“可跳过条件”：
- 后端不可达 / 登录失败 / datasets 不可用 ⇒ `test.skip(true, reason)`

---

## 4) 登录/鉴权约定（最重要的稳定性来源）

### 4.1 mock 类用例（推荐）
使用 `fronted/e2e/helpers/auth.js`：
- `adminTest(...)`：模拟 admin storageState + 稳定 `me/refresh/me/kbs` 路由
- `viewerTest(...)`：模拟 viewer

优点：
- 不依赖真实后端
- 运行快、稳定

### 4.2 integration 类用例（必须真实后端）
使用 `fronted/e2e/helpers/integration.js`：
- `preflightAdmin()`：检查后端可达 + admin 登录 + `/api/auth/me`
- `uiLogin(page)`：真实 UI 登录（用于端到端链路）

重要：
- 集成用例应先 `preflightAdmin()`，再按需检查 `/api/datasets` 可用性（RAGFlow 是否可用）
- 不满足条件就 `test.skip(true, reason)`，不要硬失败

---

## 5) 选择器/定位约定（避免脆弱用例）

优先级（从高到低）：
1) `data-testid`（最稳）
2) role + name（`getByRole('button', { name: '...' })`）—— 适合稳定中文文案
3) 文本定位（`getByText`）—— 避免依赖表头乱码/编码问题
4) CSS selector（最后手段）

若页面缺少稳定 testid：
- 优先在 UI 里补 `data-testid`（对关键按钮/弹窗/错误提示/空态）
- 但不要无意义地给所有元素加；只加“测试需要稳定定位的关键控件”

---

## 6) Mock 约定（如何写稳定的 mock）

### 6.1 路由拦截
常用写法：
- `page.route('**/api/xxx', route => route.fulfill(...))`
- 只拦你关心的方法：`if (route.request().method() !== 'GET') return route.fallback();`

### 6.2 小工具
可用 helper：`fronted/e2e/helpers/mock.js` 的 `mockJson(page, pattern, json, status)`

### 6.3 错误态
前端 `httpClient.requestJson()` 会把非 2xx 解析成 `Error(message)`：
- message 优先来自 JSON：`detail/message/error`
- 否则是 `Request failed (<status>)`

因此：
- 想断言错误文案，建议在 mock body 里放 `{"detail":"..."}`，并在 UI 里断言该字符串

---

## 7) 与后端真实链路相关的关键坑（写 integration 必看）

### 7.1 文档冲突 approve-overwrite
后端 overwrite 强依赖旧文档 `ragflow_doc_id` 已存在：
- 必须先 approve 旧文件（确保上传到 RAGFlow 成功）  
- 再上传同名新文件触发冲突

参考实现：
- `fronted/e2e/tests/integration.documents.conflict.overwrite.spec.js`

### 7.2 datasets 可用性
integration 中应检测 `/api/datasets`：
- 不可用或为空 ⇒ `skip`

参考实现：
- `fronted/e2e/tests/integration.upload.reject.spec.js`

---

## 8) 如何新增一个用例（建议流程）

1) 选模块与分层：smoke / regression(mock) / integration
2) 先查现有用例命名与风格（同模块优先复用模式）
3) 找稳定定位：优先 `data-testid`；缺则补 testid
4) 只 mock “本用例需要的最小接口集合”
5) 覆盖一个“行为闭环” + 至少一个错误/取消分支（如果该功能有）
6) 跑单个 spec 验证，再跑同层级聚合命令（`e2e` 或 `e2e:integration`）
7) 更新文档：
   - 已实现：`doc/test/implemented/<module>.md`
   - 如果仍有缺口：`doc/test/pending/<module>.md`
   - API 映射（可选但推荐）：`doc/test/implemented/api_surface.md` / `doc/test/pending/api_surface.md`

---

## 9) 命名与 tag 约定

- 文件名建议：`<module>.<feature>.<case>.spec.js`
  - 例：`documents.review.reject.prompt-cancel.spec.js`
- 每个 test title 末尾加 tag（可多选）：
  - `@smoke` / `@regression` / `@integration`
  - 模块 tag（可选）：`@documents` `@upload` `@browser` `@dashboard` `@rbac`

---

## 10) 需要维护的“覆盖面事实来源”

本仓库以 `doc/test/` 为单一事实来源（不要只在口头/聊天里更新）：
- “现在有哪些用例”：看 `doc/test/implemented/`
- “还缺什么”：看 `doc/test/pending/`
- “后端路由覆盖到哪”：看 `doc/test/*/api_surface.md`

