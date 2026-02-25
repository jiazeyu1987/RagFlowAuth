# Frontend Playwright 测试总览

## 目标
- 提供一套可一键执行的 Playwright 自动化测试。
- 覆盖主要页签与关键业务链路（上传/审批/搜索/对话/权限/日志）。
- 产出可回放的失败证据（trace/screenshot/video）与 HTML 报告。

## 范围
- 前端：`fronted/src` 主要页面与交互流程。
- 后端联动：`backend` API（mock 与 integration 两层）。
- 自动化入口：`fronted/playwright.config.js`、`fronted/e2e/tests/**`。

## 分层
- `@smoke`：快速冒烟，提交前必跑。
- `@regression`：常规回归，覆盖主路径与权限分支。
- `@integration`：真实后端联调，验证上传-审批-搜索-日志全链路。

## 一键执行
- 全量（含 integration）：`cd fronted && npm run e2e:all`
- 回归（不含 integration）：`cd fronted && npm run e2e`
- 冒烟：`cd fronted && npm run e2e:smoke`
- 联调：`cd fronted && npm run e2e:integration`
- 报告：`cd fronted && npm run e2e:report`

## 文档索引
- 测试项清单：`doc/test/fronted/test-items.md`
- 测试方案：`doc/test/fronted/test-strategy.md`
- 报告格式：`doc/test/fronted/report-format.md`
- 已实现映射：`doc/test/fronted/implemented-mapping.md`
