# 页面级业务测试说明

本目录收录按页面拆分的业务测试文档。当前 19 份页面级文档已全部接入 `doc/e2e` 全真链路，不再保留待接入项。

## 当前状态

- 页面文档总数：**19**
- 已接入全真链路自动化：**19**
- 待补齐自动化：**0**

## 已接入全真链路自动化

- [审批中心](./审批中心.md)
  对应 `fronted/e2e/tests/docs.approval-center.spec.js`
- [审批配置](./审批配置.md)
  对应 `fronted/e2e/tests/docs.approval-config.spec.js`
- [培训合规](./培训合规.md)
  对应 `fronted/e2e/tests/docs.training-compliance.spec.js`
- [文档记录](./文档记录.md)
  对应 `fronted/e2e/tests/docs.document-audit.spec.js`
- [电子签名管理](./电子签名管理.md)
  对应 `fronted/e2e/tests/docs.electronic-signatures.spec.js`
- [站内信](./站内信.md)
  对应 `fronted/e2e/tests/docs.inbox.spec.js`
- [通知设置](./通知设置.md)
  对应 `fronted/e2e/tests/docs.notification-settings.spec.js`
- [文档上传](./文档上传.md)
  对应 `fronted/e2e/tests/docs.document-upload.spec.js`
- [文档浏览](./文档浏览.md)
  对应 `fronted/e2e/tests/docs.document-browser.spec.js`
- [知识库配置](./知识库配置.md)
  对应 `fronted/e2e/tests/docs.knowledge-base-config.spec.js`
- [用户管理](./用户管理.md)
  对应 `fronted/e2e/tests/docs.user-management.spec.js`
- [权限分组](./权限分组.md)
  对应 `fronted/e2e/tests/docs.permission-groups.spec.js`
- [组织管理](./组织管理.md)
  对应 `fronted/e2e/tests/docs.org-management.spec.js`
- [全库搜索](./全库搜索.md)
  对应 `fronted/e2e/tests/docs.global-search.spec.js`
- [智能对话](./智能对话.md)
  对应 `fronted/e2e/tests/docs.chat.spec.js`
- [日志审计](./日志审计.md)
  对应 `fronted/e2e/tests/docs.audit-logs.spec.js`
- [数据安全](./数据安全.md)
  对应 `fronted/e2e/tests/docs.data-security.spec.js`
- [修改密码](./修改密码.md)
  对应 `fronted/e2e/tests/docs.password-change.spec.js`
- [实用工具](./实用工具.md)
  对应 `fronted/e2e/tests/docs.tools.spec.js`

## 扩展要求

- 页面级自动化必须走真实后端、真实数据库、真实登录态。
- 依赖前置不足时直接 fail-fast，不允许通过 mock 对齐预期。
- 需要新增页面级场景时，优先把真实种子补进 `scripts/bootstrap_doc_test_env.py`，再补 Playwright 断言。
