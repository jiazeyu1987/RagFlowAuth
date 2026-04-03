# 去除 mock 鉴权并切换真实数据验证记录

- 日期: 2026-04-02
- 范围:
  - Playwright E2E 鉴权基线从 `mock` 改为真实后端登录
  - 生成真实 `operator/viewer/reviewer/uploader/admin` storage state
  - 审批签名用例改为真实 `/api/auth/signature-challenge`
  - 上传页补充目录层级标签，支持显示 `node_path/name`

## 本轮执行命令

```powershell
cd D:\ProjectPackage\RagflowAuth\fronted
npx playwright test e2e/tests/documents.review.approve.spec.js e2e/tests/review.signature.spec.js e2e/tests/documents.review.api-errors.spec.js e2e/tests/upload.validation.spec.js e2e/tests/smoke.upload.spec.js
```

## 结果

- 结果: 13/13 通过
- 用时: 37.3s

## 通过项

1. `documents.review.approve.spec.js`
2. `review.signature.spec.js`
3. `documents.review.api-errors.spec.js`
4. `upload.validation.spec.js`
5. `smoke.upload.spec.js`

## 说明

- 初次复测时，`upload.validation.spec.js` 中“KB 下拉显示层级路径”失败，原因是上传页未消费 `/api/knowledge/directories` 返回的 `node_path`。
- 已修复上传页标签拼接逻辑后再次复测，13 项全部通过。
