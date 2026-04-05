# 多角色联动测试说明

本目录收录需要两个及以上角色共同参与的联动场景文档。当前 11 份角色联动文档已全部接入 `doc/e2e` 全真链路，不再保留待接入项。

## 当前状态

- 多角色文档总数：**11**
- 已接入全真链路自动化：**11**
- 待补齐自动化：**0**

## 已接入全真链路自动化

- [01 账号与权限开通](./01_账号与权限开通.md)
  对应 `fronted/e2e/tests/docs.user-management.spec.js`
- [02 权限组与菜单生效](./02_权限组与菜单生效.md)
  对应 `fronted/e2e/tests/docs.role.permission-menu.spec.js`
- [03 知识库与目录范围](./03_知识库与目录范围.md)
  对应 `fronted/e2e/tests/docs.role.knowledge-scope.spec.js`
- [04 文档上传审核发布](./04_文档上传审核发布.md)
  对应 `fronted/e2e/tests/docs.document-upload-publish.spec.js`
- [05 文档删除下载与审计](./05_文档删除下载与审计.md)
  对应 `fronted/e2e/tests/docs.document-audit.spec.js`
- [06 审批申请处理撤回](./06_审批申请处理撤回.md)
  对应 `fronted/e2e/tests/docs.approval-center.spec.js`
- [07 通知规则与站内信](./07_通知规则与站内信.md)
  对应 `fronted/e2e/tests/docs.notification-settings.spec.js`、`fronted/e2e/tests/docs.inbox.spec.js`
- [08 电子签名授权与验签](./08_电子签名授权与验签.md)
  对应 `fronted/e2e/tests/docs.electronic-signatures.spec.js`
- [09 培训合规与审批资格](./09_培训合规与审批资格.md)
  对应 `fronted/e2e/tests/docs.training-compliance.spec.js`、`fronted/e2e/tests/docs.role.training-approval-flow.spec.js`
- [10 密码重置与账号状态](./10_密码重置与账号状态.md)
  对应 `fronted/e2e/tests/docs.user-management.spec.js`、`fronted/e2e/tests/docs.password-change.spec.js`
- [11 越权访问与数据隔离](./11_越权访问与数据隔离.md)
  对应 `fronted/e2e/tests/docs.role.data-isolation.spec.js`

## 扩展要求

- 多角色链路必须使用独立真实账号，不能把申请人与审批人合并成同一用户。
- 审批、培训门禁、电子签名、权限隔离等关键状态必须来自真实后端，不允许前端伪造。
- 需要新增联动场景时，优先把真实前置补到 `scripts/bootstrap_doc_test_env.py`，再补 Playwright 断言。
