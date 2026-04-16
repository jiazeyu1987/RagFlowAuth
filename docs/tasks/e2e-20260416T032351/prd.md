# PRD

- Task ID: `e2e-20260416T032351`
- Created: `2026-04-16T03:23:51`
- Workspace: `D:\ProjectPackage\RagflowAuth`
- User Request: `为当前审批矩阵编写 E2E 测试用例，尽量覆盖完整的文控矩阵主流程、关键错误场景和审计展示`

## Goal

为当前“审批矩阵接入文控审批流”补充可运行的 Playwright E2E，用真实浏览器覆盖矩阵预览、提交审批后的链路展示、关键错误场景，以及日志审计里的矩阵流转展示。

## Scope

- `fronted/e2e/tests/document-control.matrix*.spec.js`
- `fronted/e2e/tests/audit.logs.document-control-matrix.spec.js`
- 复用 `fronted/e2e/helpers/auth.js`、`fronted/e2e/helpers/mock.js`
- 只补 mocked 浏览器 E2E，不修改业务逻辑来迎合测试

## Non-Goals

- 不补真实后端数据库驱动的全链路集成浏览器测试
- 不改审批矩阵业务规则本身
- 不重构现有文控页面或审计页面实现

## Preconditions

- Node / npm 可用，并能运行 `npx playwright test`
- Playwright 已在 `fronted/` 安装
- 前端 dev server 与测试 backend 能由 Playwright 配置自动拉起
- 可使用独立 `E2E_TEST_DB_PATH`，避免占用默认 `data/e2e/auth.db`

## Impacted Areas

- `fronted/src/pages/DocumentControl.js`
- `fronted/src/pages/AuditLogs.js`
- `fronted/src/features/documentControl/api.js`
- `fronted/src/features/documentControl/useDocumentControlPage.js`
- 现有文控矩阵 mocked E2E 基线：`fronted/e2e/tests/document-control.matrix.spec.js`
- 现有矩阵审计 mocked E2E 基线：`fronted/e2e/tests/audit.logs.document-control-matrix.spec.js`

## Phase Plan

### P1: 审查现有矩阵 E2E 覆盖

- Objective: 盘点当前审批矩阵 E2E 已覆盖与未覆盖的文控场景
- Owned paths: `fronted/e2e/tests/`, `docs/tasks/e2e-20260416T032351/`
- Dependencies: 已有矩阵前后端实现与已有 E2E 文件
- Deliverables: 覆盖缺口清单写入 `execution-log.md`

### P2: 补充矩阵主流程与错误场景 E2E

- Objective: 新增/扩展 mocked Playwright 用例，覆盖矩阵预览、注册条件分支、提交流程、关键错误态
- Owned paths: `fronted/e2e/tests/document-control.matrix*.spec.js`
- Dependencies: 文控页面现有 testid 与 mocked API 契约
- Deliverables: 新增或更新的 E2E spec 文件

### P3: 补充矩阵审计 E2E 并完成定向验证

- Objective: 确认审计页可读、可筛选，并运行目标 E2E 回归
- Owned paths: `fronted/e2e/tests/audit.logs.document-control-matrix.spec.js`, `docs/tasks/e2e-20260416T032351/test-report.md`
- Dependencies: 审计页现有 filter/testid 与新旧矩阵动作映射
- Deliverables: 通过的 Playwright 结果与测试报告摘要

## Phase Acceptance Criteria

### P1

- P1-AC1: 明确列出当前矩阵 E2E 已覆盖的 happy path 和缺失的关键分支
- P1-AC2: 缺口分析覆盖主流程、错误态、审计展示三类场景
- Evidence expectation: `execution-log.md` 中记录现状与缺口

### P2

- P2-AC1: 至少补齐一个文件小类/矩阵预览主流程用例以外的矩阵分支用例
- P2-AC2: 至少补齐两个关键错误场景的浏览器 E2E 断言
- P2-AC3: 至少补齐一个“注册条件不触发注册会签”的浏览器 E2E 断言
- Evidence expectation: 新增/更新的 E2E spec 与运行日志

### P3

- P3-AC1: 审计页 E2E 能断言矩阵流转 action/source/上下文摘要/筛选
- P3-AC2: 目标 Playwright 命令在独立测试库下通过
- P3-AC3: `test-report.md` 记录通过情况、环境前提和剩余风险
- Evidence expectation: Playwright 通过输出与 `test-report.md`

## Done Definition

- P1~P3 全部完成
- 新增的矩阵 E2E 覆盖主流程、注册条件分支、关键错误态、审计展示
- 目标 Playwright 命令通过
- `execution-log.md` 与 `test-report.md` 记录完整

## Blocking Conditions

- Playwright 无法启动前后端测试环境
- `E2E_TEST_DB_PATH` 无法切换导致默认测试库被占用
- 现有页面 testid 或 mocked API 契约缺失，导致关键场景无法通过浏览器断言
