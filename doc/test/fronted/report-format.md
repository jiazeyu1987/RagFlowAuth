# 自动化测试报告格式（排障用）

你跑完后，建议提供以下内容（至少 1~4）：

## 1) 执行摘要（必填）
- 执行时间
- 分支 / 提交
- 执行命令（如：`npm run e2e` / `npm run e2e:integration`）
- 总用例数
- 成功数
- 失败数
- 跳过数

## 2) 失败列表（必填）
每条失败建议按以下字段给出：
- 用例 ID（如：`FLOW-001`）
- Playwright 用例名（spec + case）
- 报错首行
- 失败步骤（第几步）

示例：
```text
ID: FLOW-001
Spec: integration.flow.upload-approve-search-logs.spec.js > flow: upload -> approve -> searchable -> audit visible
Error: expect(locator).toBeVisible() timeout 10000ms
Step: 打开日志页后未找到 audit-logs-page
```

## 3) 附件（建议）
- `playwright-report/`（HTML 报告）
- 失败用例的 `trace.zip`
- 失败截图 `.png`
- integration 场景对应时间窗的后端日志片段

## 4) 环境信息（必填）
- OS
- Node / npm
- 前端地址（`E2E_FRONTEND_BASE_URL`）
- 后端地址（`E2E_BACKEND_BASE_URL`）
- 后端启动方式（`python -m backend` / 容器）
- 测试模式（`E2E_MODE=mock|real`）

## 5) 我会如何用这份报告排障
- 先按“失败用例 ID -> 模块”聚类。
- 再看 trace 回放网络与 UI 状态。
- 最后判断问题归属：前端状态机、后端 contract、权限配置、数据污染或依赖异常。
