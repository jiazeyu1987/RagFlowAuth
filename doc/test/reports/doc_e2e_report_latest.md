# Doc E2E Report

- Time: 2026-04-05 15:52:53
- Repository: `D:\ProjectPackage\RagflowAuth`
- Manifest: `D:\ProjectPackage\RagflowAuth\doc\e2e\manifest.json`
- Scopes: `unit, role`
- Overall: **PASS**
- Doc Count: **30**
- Spec Count: **24**

## Run Mode

- CWD: `D:\ProjectPackage\RagflowAuth\fronted`
- Strategy: `one-spec-per-playwright-run`

## Docs

| Scope | Doc | Spec Count |
|---|---|---:|
| unit | `doc/e2e/unit/审批中心.md` | 1 |
| unit | `doc/e2e/unit/审批配置.md` | 1 |
| unit | `doc/e2e/unit/培训合规.md` | 1 |
| unit | `doc/e2e/unit/文档记录.md` | 1 |
| unit | `doc/e2e/unit/电子签名管理.md` | 1 |
| unit | `doc/e2e/unit/站内信.md` | 1 |
| unit | `doc/e2e/unit/通知设置.md` | 1 |
| unit | `doc/e2e/unit/文档上传.md` | 1 |
| unit | `doc/e2e/unit/文档浏览.md` | 1 |
| unit | `doc/e2e/unit/知识库配置.md` | 1 |
| unit | `doc/e2e/unit/用户管理.md` | 1 |
| unit | `doc/e2e/unit/权限分组.md` | 1 |
| unit | `doc/e2e/unit/组织管理.md` | 1 |
| unit | `doc/e2e/unit/全库搜索.md` | 1 |
| unit | `doc/e2e/unit/智能对话.md` | 1 |
| unit | `doc/e2e/unit/日志审计.md` | 1 |
| unit | `doc/e2e/unit/数据安全.md` | 1 |
| unit | `doc/e2e/unit/修改密码.md` | 1 |
| unit | `doc/e2e/unit/实用工具.md` | 1 |
| role | `doc/e2e/role/01_账号与权限开通.md` | 1 |
| role | `doc/e2e/role/02_权限组与菜单生效.md` | 1 |
| role | `doc/e2e/role/03_知识库与目录范围.md` | 1 |
| role | `doc/e2e/role/04_文档上传审核发布.md` | 1 |
| role | `doc/e2e/role/05_文档删除下载与审计.md` | 1 |
| role | `doc/e2e/role/06_审批申请处理撤回.md` | 1 |
| role | `doc/e2e/role/07_通知规则与站内信.md` | 2 |
| role | `doc/e2e/role/08_电子签名授权与验签.md` | 1 |
| role | `doc/e2e/role/09_培训合规与审批资格.md` | 2 |
| role | `doc/e2e/role/10_密码重置与账号状态.md` | 2 |
| role | `doc/e2e/role/11_越权访问与数据隔离.md` | 1 |

## Specs

- `fronted/e2e/tests/docs.approval-center.spec.js`
- `fronted/e2e/tests/docs.approval-config.spec.js`
- `fronted/e2e/tests/docs.training-compliance.spec.js`
- `fronted/e2e/tests/docs.document-audit.spec.js`
- `fronted/e2e/tests/docs.electronic-signatures.spec.js`
- `fronted/e2e/tests/docs.inbox.spec.js`
- `fronted/e2e/tests/docs.notification-settings.spec.js`
- `fronted/e2e/tests/docs.document-upload.spec.js`
- `fronted/e2e/tests/docs.document-browser.spec.js`
- `fronted/e2e/tests/docs.knowledge-base-config.spec.js`
- `fronted/e2e/tests/docs.user-management.spec.js`
- `fronted/e2e/tests/docs.permission-groups.spec.js`
- `fronted/e2e/tests/docs.org-management.spec.js`
- `fronted/e2e/tests/docs.global-search.spec.js`
- `fronted/e2e/tests/docs.chat.spec.js`
- `fronted/e2e/tests/docs.audit-logs.spec.js`
- `fronted/e2e/tests/docs.data-security.spec.js`
- `fronted/e2e/tests/docs.password-change.spec.js`
- `fronted/e2e/tests/docs.tools.spec.js`
- `fronted/e2e/tests/docs.role.permission-menu.spec.js`
- `fronted/e2e/tests/docs.role.knowledge-scope.spec.js`
- `fronted/e2e/tests/docs.document-upload-publish.spec.js`
- `fronted/e2e/tests/docs.role.training-approval-flow.spec.js`
- `fronted/e2e/tests/docs.role.data-isolation.spec.js`

## Spec Runs

| Spec | Result | Command |
|---|---|---|
| `e2e/tests/docs.approval-center.spec.js` | PASS | `D:\Programs\npx.cmd playwright test --config playwright.docs.config.js e2e/tests/docs.approval-center.spec.js --workers=1` |
| `e2e/tests/docs.approval-config.spec.js` | PASS | `D:\Programs\npx.cmd playwright test --config playwright.docs.config.js e2e/tests/docs.approval-config.spec.js --workers=1` |
| `e2e/tests/docs.training-compliance.spec.js` | PASS | `D:\Programs\npx.cmd playwright test --config playwright.docs.config.js e2e/tests/docs.training-compliance.spec.js --workers=1` |
| `e2e/tests/docs.document-audit.spec.js` | PASS | `D:\Programs\npx.cmd playwright test --config playwright.docs.config.js e2e/tests/docs.document-audit.spec.js --workers=1` |
| `e2e/tests/docs.electronic-signatures.spec.js` | PASS | `D:\Programs\npx.cmd playwright test --config playwright.docs.config.js e2e/tests/docs.electronic-signatures.spec.js --workers=1` |
| `e2e/tests/docs.inbox.spec.js` | PASS | `D:\Programs\npx.cmd playwright test --config playwright.docs.config.js e2e/tests/docs.inbox.spec.js --workers=1` |
| `e2e/tests/docs.notification-settings.spec.js` | PASS | `D:\Programs\npx.cmd playwright test --config playwright.docs.config.js e2e/tests/docs.notification-settings.spec.js --workers=1` |
| `e2e/tests/docs.document-upload.spec.js` | PASS | `D:\Programs\npx.cmd playwright test --config playwright.docs.config.js e2e/tests/docs.document-upload.spec.js --workers=1` |
| `e2e/tests/docs.document-browser.spec.js` | PASS | `D:\Programs\npx.cmd playwright test --config playwright.docs.config.js e2e/tests/docs.document-browser.spec.js --workers=1` |
| `e2e/tests/docs.knowledge-base-config.spec.js` | PASS | `D:\Programs\npx.cmd playwright test --config playwright.docs.config.js e2e/tests/docs.knowledge-base-config.spec.js --workers=1` |
| `e2e/tests/docs.user-management.spec.js` | PASS | `D:\Programs\npx.cmd playwright test --config playwright.docs.config.js e2e/tests/docs.user-management.spec.js --workers=1` |
| `e2e/tests/docs.permission-groups.spec.js` | PASS | `D:\Programs\npx.cmd playwright test --config playwright.docs.config.js e2e/tests/docs.permission-groups.spec.js --workers=1` |
| `e2e/tests/docs.org-management.spec.js` | PASS | `D:\Programs\npx.cmd playwright test --config playwright.docs.config.js e2e/tests/docs.org-management.spec.js --workers=1` |
| `e2e/tests/docs.global-search.spec.js` | PASS | `D:\Programs\npx.cmd playwright test --config playwright.docs.config.js e2e/tests/docs.global-search.spec.js --workers=1` |
| `e2e/tests/docs.chat.spec.js` | PASS | `D:\Programs\npx.cmd playwright test --config playwright.docs.config.js e2e/tests/docs.chat.spec.js --workers=1` |
| `e2e/tests/docs.audit-logs.spec.js` | PASS | `D:\Programs\npx.cmd playwright test --config playwright.docs.config.js e2e/tests/docs.audit-logs.spec.js --workers=1` |
| `e2e/tests/docs.data-security.spec.js` | PASS | `D:\Programs\npx.cmd playwright test --config playwright.docs.config.js e2e/tests/docs.data-security.spec.js --workers=1` |
| `e2e/tests/docs.password-change.spec.js` | PASS | `D:\Programs\npx.cmd playwright test --config playwright.docs.config.js e2e/tests/docs.password-change.spec.js --workers=1` |
| `e2e/tests/docs.tools.spec.js` | PASS | `D:\Programs\npx.cmd playwright test --config playwright.docs.config.js e2e/tests/docs.tools.spec.js --workers=1` |
| `e2e/tests/docs.role.permission-menu.spec.js` | PASS | `D:\Programs\npx.cmd playwright test --config playwright.docs.config.js e2e/tests/docs.role.permission-menu.spec.js --workers=1` |
| `e2e/tests/docs.role.knowledge-scope.spec.js` | PASS | `D:\Programs\npx.cmd playwright test --config playwright.docs.config.js e2e/tests/docs.role.knowledge-scope.spec.js --workers=1` |
| `e2e/tests/docs.document-upload-publish.spec.js` | PASS | `D:\Programs\npx.cmd playwright test --config playwright.docs.config.js e2e/tests/docs.document-upload-publish.spec.js --workers=1` |
| `e2e/tests/docs.role.training-approval-flow.spec.js` | PASS | `D:\Programs\npx.cmd playwright test --config playwright.docs.config.js e2e/tests/docs.role.training-approval-flow.spec.js --workers=1` |
| `e2e/tests/docs.role.data-isolation.spec.js` | PASS | `D:\Programs\npx.cmd playwright test --config playwright.docs.config.js e2e/tests/docs.role.data-isolation.spec.js --workers=1` |

## Raw Output

```text
$ D:\Programs\npx.cmd playwright test --config playwright.docs.config.js e2e/tests/docs.approval-center.spec.js --workers=1
[2m[WebServer] [22mC:\Users\BJB110\AppData\Local\Programs\Python\Python312\Lib\site-packages\requests\__init__.py:113: RequestsDependencyWarning: urllib3 (2.6.3) or chardet (6.0.0.post1)/charset_normalizer (3.4.4) doesn't match a supported version!
[2m[WebServer] [22m  warnings.warn(
[2m[WebServer] [22mINFO:     Started server process [58704]
[2m[WebServer] [22mINFO:     Waiting for application startup.
[2m[WebServer] [22mWARNING:  RAGFlow config loaded: path=D:\ProjectPackage\RagflowAuth\ragflow_config.json base_url=http://127.0.0.1:9380 api_key=ragflo��FFBs (configured)
[2m[WebServer] [22mWARNING:  RAGFlow client init: base_url=http://127.0.0.1:9380 api_key=ragflo��FFBs
[2m[WebServer] [22mWARNING:  Runtime python=C:\Users\BJB110\AppData\Local\Programs\Python\Python312\python.exe ragflow_chat_service=D:\ProjectPackage\RagflowAuth\backend\services\ragflow_chat_service.py mtime_ns=1772794782813123900
[2m[WebServer] [22mINFO:     Application startup complete.
[2m[WebServer] [22mINFO:     Uvicorn running on http://0.0.0.0:38002 (Press CTRL+C to quit)
[2m[WebServer] [22m(node:35000) [DEP0176] DeprecationWarning: fs.F_OK is deprecated, use fs.constants.F_OK instead
[2m[WebServer] [22m(Use `node --trace-deprecation ...` to show where the warning was created)
[2m[WebServer] [22m(node:35000) [DEP_WEBPACK_DEV_SERVER_ON_AFTER_SETUP_MIDDLEWARE] DeprecationWarning: 'onAfterSetupMiddleware' option is deprecated. Please use the 'setupMiddlewares' option.
[2m[WebServer] [22m(node:35000) [DEP_WEBPACK_DEV_SERVER_ON_BEFORE_SETUP_MIDDLEWARE] DeprecationWarning: 'onBeforeSetupMiddleware' option is deprecated. Please use the 'setupMiddlewares' option.
[2m[WebServer] [22mWARNING:  RAGFlow config loaded: path=D:\ProjectPackage\RagflowAuth\ragflow_config.json base_url=http://127.0.0.1:9380 api_key=ragflo��FFBs (configured)
[2m[WebServer] [22mWARNING:  RAGFlow client init: base_url=http://127.0.0.1:9380 api_key=ragflo��FFBs

Running 1 test using 1 worker

  ok 1 [chromium] › e2e\tests\docs.approval-center.spec.js:10:1 › Doc approval center covers real approve, reject, and withdraw flows @doc-e2e (5.2s)

  1 passed (25.6s)

$ D:\Programs\npx.cmd playwright test --config playwright.docs.config.js e2e/tests/docs.approval-config.spec.js --workers=1
[2m[WebServer] [22mC:\Users\BJB110\AppData\Local\Programs\Python\Python312\Lib\site-packages\requests\__init__.py:113: RequestsDependencyWarning: urllib3 (2.6.3) or chardet (6.0.0.post1)/charset_normalizer (3.4.4) doesn't match a supported version!
[2m[WebServer] [22m  warnings.warn(
[2m[WebServer] [22mINFO:     Started server process [83512]
[2m[WebServer] [22mINFO:     Waiting for application startup.
[2m[WebServer] [22mWARNING:  RAGFlow config loaded: path=D:\ProjectPackage\RagflowAuth\ragflow_config.json base_url=http://127.0.0.1:9380 api_key=ragflo��FFBs (configured)
[2m[WebServer] [22mWARNING:  RAGFlow client init: base_url=http://127.0.0.1:9380 api_key=ragflo��FFBs
[2m[WebServer] [22mWARNING:  Runtime python=C:\Users\BJB110\AppData\Local\Programs\Python\Python312\python.exe ragflow_chat_service=D:\ProjectPackage\RagflowAuth\backend\services\ragflow_chat_service.py mtime_ns=1772794782813123900
[2m[WebServer] [22mINFO:     Application startup complete.
[2m[WebServer] [22mINFO:     Uvicorn running on http://0.0.0.0:38002 (Press CTRL+C to quit)
[2m[WebServer] [22m(node:89192) [DEP0176] DeprecationWarning: fs.F_OK is deprecated, use fs.constants.F_OK instead
[2m[WebServer] [22m(Use `node --trace-deprecation ...` to show where the warning was created)
[2m[WebServer] [22m(node:89192) [DEP_WEBPACK_DEV_SERVER_ON_AFTER_SETUP_MIDDLEWARE] DeprecationWarning: 'onAfterSetupMiddleware' option is deprecated. Please use the 'setupMiddlewares' option.
[2m[WebServer] [22m(node:89192) [DEP_WEBPACK_DEV_SERVER_ON_BEFORE_SETUP_MIDDLEWARE] DeprecationWarning: 'onBeforeSetupMiddleware' option is deprecated. Please use the 'setupMiddlewares' option.
[2m[WebServer] [22mWARNING:  RAGFlow config loaded: path=D:\ProjectPackage\RagflowAuth\ragflow_config.json base_url=http://127.0.0.1:9380 api_key=ragflo��FFBs (configured)
[2m[WebServer] [22mWARNING:  RAGFlow client init: base_url=http://127.0.0.1:9380 api_key=ragflo��FFBs

Running 1 test using 1 worker

  ok 1 [chromium] › e2e\tests\docs.approval-config.spec.js:9:1 › 审批配置文档流程使用真实工作流、成员搜索与保存结果 @doc-e2e (1.6s)

  1 passed (19.6s)

$ D:\Programs\npx.cmd playwright test --config playwright.docs.config.js e2e/tests/docs.training-compliance.spec.js --workers=1
[2m[WebServer] [22mC:\Users\BJB110\AppData\Local\Programs\Python\Python312\Lib\site-packages\requests\__init__.py:113: RequestsDependencyWarning: urllib3 (2.6.3) or chardet (6.0.0.post1)/charset_normalizer (3.4.4) doesn't match a supported version!
[2m[WebServer] [22m  warnings.warn(
[2m[WebServer] [22mINFO:     Started server process [50208]
[2m[WebServer] [22mINFO:     Waiting for application startup.
[2m[WebServer] [22mWARNING:  RAGFlow config loaded: path=D:\ProjectPackage\RagflowAuth\ragflow_config.json base_url=http://127.0.0.1:9380 api_key=ragflo��FFBs (configured)
[2m[WebServer] [22mWARNING:  RAGFlow client init: base_url=http://127.0.0.1:9380 api_key=ragflo��FFBs
[2m[WebServer] [22mWARNING:  Runtime python=C:\Users\BJB110\AppData\Local\Programs\Python\Python312\python.exe ragflow_chat_service=D:\ProjectPackage\RagflowAuth\backend\services\ragflow_chat_service.py mtime_ns=1772794782813123900
[2m[WebServer] [22mINFO:     Application startup complete.
[2m[WebServer] [22mINFO:     Uvicorn running on http://0.0.0.0:38002 (Press CTRL+C to quit)
[2m[WebServer] [22m(node:89244) [DEP0176] DeprecationWarning: fs.F_OK is deprecated, use fs.constants.F_OK instead
[2m[WebServer] [22m(Use `node --trace-deprecation ...` to show where the warning was created)
[2m[WebServer] [22m(node:89244) [DEP_WEBPACK_DEV_SERVER_ON_AFTER_SETUP_MIDDLEWARE] DeprecationWarning: 'onAfterSetupMiddleware' option is deprecated. Please use the 'setupMiddlewares' option.
[2m[WebServer] [22m(node:89244) [DEP_WEBPACK_DEV_SERVER_ON_BEFORE_SETUP_MIDDLEWARE] DeprecationWarning: 'onBeforeSetupMiddleware' option is deprecated. Please use the 'setupMiddlewares' option.
[2m[WebServer] [22mWARNING:  RAGFlow config loaded: path=D:\ProjectPackage\RagflowAuth\ragflow_config.json base_url=http://127.0.0.1:9380 api_key=ragflo��FFBs (configured)
[2m[WebServer] [22mWARNING:  RAGFlow client init: base_url=http://127.0.0.1:9380 api_key=ragflo��FFBs

Running 2 tests using 1 worker

  ok 1 [chromium] › e2e\tests\docs.training-compliance.spec.js:8:1 › 培训合规文档流程覆盖刷新与页签切换 @doc-e2e (926ms)
  ok 2 [chromium] › e2e\tests\docs.training-compliance.spec.js:41:1 › 培训合规文档流程使用真实用户搜索并保存培训记录和认证 @doc-e2e (1.4s)

  2 passed (20.3s)

$ D:\Programs\npx.cmd playwright test --config playwright.docs.config.js e2e/tests/docs.document-audit.spec.js --workers=1
[2m[WebServer] [22mC:\Users\BJB110\AppData\Local\Programs\Python\Python312\Lib\site-packages\requests\__init__.py:113: RequestsDependencyWarning: urllib3 (2.6.3) or chardet (6.0.0.post1)/charset_normalizer (3.4.4) doesn't match a supported version!
[2m[WebServer] [22m  warnings.warn(
[2m[WebServer] [22mINFO:     Started server process [67272]
[2m[WebServer] [22mINFO:     Waiting for application startup.
[2m[WebServer] [22mWARNING:  RAGFlow config loaded: path=D:\ProjectPackage\RagflowAuth\ragflow_config.json base_url=http://127.0.0.1:9380 api_key=ragflo��FFBs (configured)
[2m[WebServer] [22mWARNING:  RAGFlow client init: base_url=http://127.0.0.1:9380 api_key=ragflo��FFBs
[2m[WebServer] [22mWARNING:  Runtime python=C:\Users\BJB110\AppData\Local\Programs\Python\Python312\python.exe ragflow_chat_service=D:\ProjectPackage\RagflowAuth\backend\services\ragflow_chat_service.py mtime_ns=1772794782813123900
[2m[WebServer] [22mINFO:     Application startup complete.
[2m[WebServer] [22mINFO:     Uvicorn running on http://0.0.0.0:38002 (Press CTRL+C to quit)
[2m[WebServer] [22m(node:88424) [DEP0176] DeprecationWarning: fs.F_OK is deprecated, use fs.constants.F_OK instead
[2m[WebServer] [22m(Use `node --trace-deprecation ...` to show where the warning was created)
[2m[WebServer] [22m(node:88424) [DEP_WEBPACK_DEV_SERVER_ON_AFTER_SETUP_MIDDLEWARE] DeprecationWarning: 'onAfterSetupMiddleware' option is deprecated. Please use the 'setupMiddlewares' option.
[2m[WebServer] [22m(node:88424) [DEP_WEBPACK_DEV_SERVER_ON_BEFORE_SETUP_MIDDLEWARE] DeprecationWarning: 'onBeforeSetupMiddleware' option is deprecated. Please use the 'setupMiddlewares' option.
[2m[WebServer] [22mWARNING:  RAGFlow config loaded: path=D:\ProjectPackage\RagflowAuth\ragflow_config.json base_url=http://127.0.0.1:9380 api_key=ragflo��FFBs (configured)
[2m[WebServer] [22mWARNING:  RAGFlow client init: base_url=http://127.0.0.1:9380 api_key=ragflo��FFBs

Running 1 test using 1 worker

  ok 1 [chromium] › e2e\tests\docs.document-audit.spec.js:8:1 › Doc document audit page uses real document, deletion, download, and version history data @doc-e2e (1.2s)

  1 passed (18.2s)

$ D:\Programs\npx.cmd playwright test --config playwright.docs.config.js e2e/tests/docs.electronic-signatures.spec.js --workers=1
[2m[WebServer] [22mC:\Users\BJB110\AppData\Local\Programs\Python\Python312\Lib\site-packages\requests\__init__.py:113: RequestsDependencyWarning: urllib3 (2.6.3) or chardet (6.0.0.post1)/charset_normalizer (3.4.4) doesn't match a supported version!
[2m[WebServer] [22m  warnings.warn(
[2m[WebServer] [22mINFO:     Started server process [26124]
[2m[WebServer] [22mINFO:     Waiting for application startup.
[2m[WebServer] [22mWARNING:  RAGFlow config loaded: path=D:\ProjectPackage\RagflowAuth\ragflow_config.json base_url=http://127.0.0.1:9380 api_key=ragflo��FFBs (configured)
[2m[WebServer] [22mWARNING:  RAGFlow client init: base_url=http://127.0.0.1:9380 api_key=ragflo��FFBs
[2m[WebServer] [22mWARNING:  Runtime python=C:\Users\BJB110\AppData\Local\Programs\Python\Python312\python.exe ragflow_chat_service=D:\ProjectPackage\RagflowAuth\backend\services\ragflow_chat_service.py mtime_ns=1772794782813123900
[2m[WebServer] [22mINFO:     Application startup complete.
[2m[WebServer] [22mINFO:     Uvicorn running on http://0.0.0.0:38002 (Press CTRL+C to quit)
[2m[WebServer] [22m(node:51920) [DEP0176] DeprecationWarning: fs.F_OK is deprecated, use fs.constants.F_OK instead
[2m[WebServer] [22m(Use `node --trace-deprecation ...` to show where the warning was created)
[2m[WebServer] [22m(node:51920) [DEP_WEBPACK_DEV_SERVER_ON_AFTER_SETUP_MIDDLEWARE] DeprecationWarning: 'onAfterSetupMiddleware' option is deprecated. Please use the 'setupMiddlewares' option.
[2m[WebServer] [22m(node:51920) [DEP_WEBPACK_DEV_SERVER_ON_BEFORE_SETUP_MIDDLEWARE] DeprecationWarning: 'onBeforeSetupMiddleware' option is deprecated. Please use the 'setupMiddlewares' option.
[2m[WebServer] [22mWARNING:  RAGFlow config loaded: path=D:\ProjectPackage\RagflowAuth\ragflow_config.json base_url=http://127.0.0.1:9380 api_key=ragflo��FFBs (configured)
[2m[WebServer] [22mWARNING:  RAGFlow client init: base_url=http://127.0.0.1:9380 api_key=ragflo��FFBs

Running 2 tests using 1 worker

  ok 1 [chromium] › e2e\tests\docs.electronic-signatures.spec.js:5:1 › Doc electronic signature management loads real signature detail and verifies it @doc-e2e (1.0s)
  ok 2 [chromium] › e2e\tests\docs.electronic-signatures.spec.js:58:1 › Doc electronic signature management toggles real authorization state and restores it @doc-e2e (1.1s)

  2 passed (19.9s)

$ D:\Programs\npx.cmd playwright test --config playwright.docs.config.js e2e/tests/docs.inbox.spec.js --workers=1
[2m[WebServer] [22mC:\Users\BJB110\AppData\Local\Programs\Python\Python312\Lib\site-packages\requests\__init__.py:113: RequestsDependencyWarning: urllib3 (2.6.3) or chardet (6.0.0.post1)/charset_normalizer (3.4.4) doesn't match a supported version!
[2m[WebServer] [22m  warnings.warn(
[2m[WebServer] [22mINFO:     Started server process [13764]
[2m[WebServer] [22mINFO:     Waiting for application startup.
[2m[WebServer] [22mWARNING:  RAGFlow config loaded: path=D:\ProjectPackage\RagflowAuth\ragflow_config.json base_url=http://127.0.0.1:9380 api_key=ragflo��FFBs (configured)
[2m[WebServer] [22mWARNING:  RAGFlow client init: base_url=http://127.0.0.1:9380 api_key=ragflo��FFBs
[2m[WebServer] [22mWARNING:  Runtime python=C:\Users\BJB110\AppData\Local\Programs\Python\Python312\python.exe ragflow_chat_service=D:\ProjectPackage\RagflowAuth\backend\services\ragflow_chat_service.py mtime_ns=1772794782813123900
[2m[WebServer] [22mINFO:     Application startup complete.
[2m[WebServer] [22mINFO:     Uvicorn running on http://0.0.0.0:38002 (Press CTRL+C to quit)
[2m[WebServer] [22m(node:90788) [DEP0176] DeprecationWarning: fs.F_OK is deprecated, use fs.constants.F_OK instead
[2m[WebServer] [22m(Use `node --trace-deprecation ...` to show where the warning was created)
[2m[WebServer] [22m(node:90788) [DEP_WEBPACK_DEV_SERVER_ON_AFTER_SETUP_MIDDLEWARE] DeprecationWarning: 'onAfterSetupMiddleware' option is deprecated. Please use the 'setupMiddlewares' option.
[2m[WebServer] [22m(node:90788) [DEP_WEBPACK_DEV_SERVER_ON_BEFORE_SETUP_MIDDLEWARE] DeprecationWarning: 'onBeforeSetupMiddleware' option is deprecated. Please use the 'setupMiddlewares' option.
[2m[WebServer] [22mWARNING:  RAGFlow config loaded: path=D:\ProjectPackage\RagflowAuth\ragflow_config.json base_url=http://127.0.0.1:9380 api_key=ragflo��FFBs (configured)
[2m[WebServer] [22mWARNING:  RAGFlow client init: base_url=http://127.0.0.1:9380 api_key=ragflo��FFBs

Running 1 test using 1 worker

  ok 1 [chromium] › e2e\tests\docs.inbox.spec.js:8:1 › Doc inbox uses real unread filtering, read-state updates, and detail navigation @doc-e2e (973ms)

  1 passed (21.4s)

$ D:\Programs\npx.cmd playwright test --config playwright.docs.config.js e2e/tests/docs.notification-settings.spec.js --workers=1
[2m[WebServer] [22mC:\Users\BJB110\AppData\Local\Programs\Python\Python312\Lib\site-packages\requests\__init__.py:113: RequestsDependencyWarning: urllib3 (2.6.3) or chardet (6.0.0.post1)/charset_normalizer (3.4.4) doesn't match a supported version!
[2m[WebServer] [22m  warnings.warn(
[2m[WebServer] [22mINFO:     Started server process [67016]
[2m[WebServer] [22mINFO:     Waiting for application startup.
[2m[WebServer] [22mWARNING:  RAGFlow config loaded: path=D:\ProjectPackage\RagflowAuth\ragflow_config.json base_url=http://127.0.0.1:9380 api_key=ragflo��FFBs (configured)
[2m[WebServer] [22mWARNING:  RAGFlow client init: base_url=http://127.0.0.1:9380 api_key=ragflo��FFBs
[2m[WebServer] [22mWARNING:  Runtime python=C:\Users\BJB110\AppData\Local\Programs\Python\Python312\python.exe ragflow_chat_service=D:\ProjectPackage\RagflowAuth\backend\services\ragflow_chat_service.py mtime_ns=1772794782813123900
[2m[WebServer] [22mINFO:     Application startup complete.
[2m[WebServer] [22mINFO:     Uvicorn running on http://0.0.0.0:38002 (Press CTRL+C to quit)
[2m[WebServer] [22m(node:45292) [DEP0176] DeprecationWarning: fs.F_OK is deprecated, use fs.constants.F_OK instead
[2m[WebServer] [22m(Use `node --trace-deprecation ...` to show where the warning was created)
[2m[WebServer] [22m(node:45292) [DEP_WEBPACK_DEV_SERVER_ON_AFTER_SETUP_MIDDLEWARE] DeprecationWarning: 'onAfterSetupMiddleware' option is deprecated. Please use the 'setupMiddlewares' option.
[2m[WebServer] [22m(node:45292) [DEP_WEBPACK_DEV_SERVER_ON_BEFORE_SETUP_MIDDLEWARE] DeprecationWarning: 'onBeforeSetupMiddleware' option is deprecated. Please use the 'setupMiddlewares' option.
[2m[WebServer] [22mWARNING:  RAGFlow config loaded: path=D:\ProjectPackage\RagflowAuth\ragflow_config.json base_url=http://127.0.0.1:9380 api_key=ragflo��FFBs (configured)
[2m[WebServer] [22mWARNING:  RAGFlow client init: base_url=http://127.0.0.1:9380 api_key=ragflo��FFBs

Running 1 test using 1 worker

  ok 1 [chromium] › e2e\tests\docs.notification-settings.spec.js:8:1 › Doc notification settings exercise real rules, channels, history, retry, and dispatch @doc-e2e (3.0s)

  1 passed (19.9s)

$ D:\Programs\npx.cmd playwright test --config playwright.docs.config.js e2e/tests/docs.document-upload.spec.js --workers=1
[2m[WebServer] [22mC:\Users\BJB110\AppData\Local\Programs\Python\Python312\Lib\site-packages\requests\__init__.py:113: RequestsDependencyWarning: urllib3 (2.6.3) or chardet (6.0.0.post1)/charset_normalizer (3.4.4) doesn't match a supported version!
[2m[WebServer] [22m  warnings.warn(
[2m[WebServer] [22mINFO:     Started server process [61516]
[2m[WebServer] [22mINFO:     Waiting for application startup.
[2m[WebServer] [22mWARNING:  RAGFlow config loaded: path=D:\ProjectPackage\RagflowAuth\ragflow_config.json base_url=http://127.0.0.1:9380 api_key=ragflo��FFBs (configured)
[2m[WebServer] [22mWARNING:  RAGFlow client init: base_url=http://127.0.0.1:9380 api_key=ragflo��FFBs
[2m[WebServer] [22mWARNING:  Runtime python=C:\Users\BJB110\AppData\Local\Programs\Python\Python312\python.exe ragflow_chat_service=D:\ProjectPackage\RagflowAuth\backend\services\ragflow_chat_service.py mtime_ns=1772794782813123900
[2m[WebServer] [22mINFO:     Application startup complete.
[2m[WebServer] [22mINFO:     Uvicorn running on http://0.0.0.0:38002 (Press CTRL+C to quit)
[2m[WebServer] [22m(node:39492) [DEP0176] DeprecationWarning: fs.F_OK is deprecated, use fs.constants.F_OK instead
[2m[WebServer] [22m(Use `node --trace-deprecation ...` to show where the warning was created)
[2m[WebServer] [22m(node:39492) [DEP_WEBPACK_DEV_SERVER_ON_AFTER_SETUP_MIDDLEWARE] DeprecationWarning: 'onAfterSetupMiddleware' option is deprecated. Please use the 'setupMiddlewares' option.
[2m[WebServer] [22m(node:39492) [DEP_WEBPACK_DEV_SERVER_ON_BEFORE_SETUP_MIDDLEWARE] DeprecationWarning: 'onBeforeSetupMiddleware' option is deprecated. Please use the 'setupMiddlewares' option.
[2m[WebServer] [22mWARNING:  RAGFlow config loaded: path=D:\ProjectPackage\RagflowAuth\ragflow_config.json base_url=http://127.0.0.1:9380 api_key=ragflo��FFBs (configured)
[2m[WebServer] [22mWARNING:  RAGFlow client init: base_url=http://127.0.0.1:9380 api_key=ragflo��FFBs

Running 1 test using 1 worker

  ok 1 [chromium] › e2e\tests\docs.document-upload.spec.js:25:1 › Doc upload page uses real file selection, removal, clear, and submit flow @doc-e2e (3.3s)

  1 passed (22.7s)

$ D:\Programs\npx.cmd playwright test --config playwright.docs.config.js e2e/tests/docs.document-browser.spec.js --workers=1
[2m[WebServer] [22mC:\Users\BJB110\AppData\Local\Programs\Python\Python312\Lib\site-packages\requests\__init__.py:113: RequestsDependencyWarning: urllib3 (2.6.3) or chardet (6.0.0.post1)/charset_normalizer (3.4.4) doesn't match a supported version!
[2m[WebServer] [22m  warnings.warn(
[2m[WebServer] [22mINFO:     Started server process [66580]
[2m[WebServer] [22mINFO:     Waiting for application startup.
[2m[WebServer] [22mWARNING:  RAGFlow config loaded: path=D:\ProjectPackage\RagflowAuth\ragflow_config.json base_url=http://127.0.0.1:9380 api_key=ragflo��FFBs (configured)
[2m[WebServer] [22mWARNING:  RAGFlow client init: base_url=http://127.0.0.1:9380 api_key=ragflo��FFBs
[2m[WebServer] [22mWARNING:  Runtime python=C:\Users\BJB110\AppData\Local\Programs\Python\Python312\python.exe ragflow_chat_service=D:\ProjectPackage\RagflowAuth\backend\services\ragflow_chat_service.py mtime_ns=1772794782813123900
[2m[WebServer] [22mINFO:     Application startup complete.
[2m[WebServer] [22mINFO:     Uvicorn running on http://0.0.0.0:38002 (Press CTRL+C to quit)
[2m[WebServer] [22m(node:79816) [DEP0176] DeprecationWarning: fs.F_OK is deprecated, use fs.constants.F_OK instead
[2m[WebServer] [22m(Use `node --trace-deprecation ...` to show where the warning was created)
[2m[WebServer] [22m(node:79816) [DEP_WEBPACK_DEV_SERVER_ON_AFTER_SETUP_MIDDLEWARE] DeprecationWarning: 'onAfterSetupMiddleware' option is deprecated. Please use the 'setupMiddlewares' option.
[2m[WebServer] [22m(node:79816) [DEP_WEBPACK_DEV_SERVER_ON_BEFORE_SETUP_MIDDLEWARE] DeprecationWarning: 'onBeforeSetupMiddleware' option is deprecated. Please use the 'setupMiddlewares' option.
[2m[WebServer] [22mWARNING:  RAGFlow config loaded: path=D:\ProjectPackage\RagflowAuth\ragflow_config.json base_url=http://127.0.0.1:9380 api_key=ragflo��FFBs (configured)
[2m[WebServer] [22mWARNING:  RAGFlow client init: base_url=http://127.0.0.1:9380 api_key=ragflo��FFBs

Running 1 test using 1 worker

  ok 1 [chromium] › e2e\tests\docs.document-browser.spec.js:30:1 › Doc browser covers real published preview/download and version relationship checks @doc-e2e (8.2s)

  1 passed (25.3s)

$ D:\Programs\npx.cmd playwright test --config playwright.docs.config.js e2e/tests/docs.knowledge-base-config.spec.js --workers=1
[2m[WebServer] [22mC:\Users\BJB110\AppData\Local\Programs\Python\Python312\Lib\site-packages\requests\__init__.py:113: RequestsDependencyWarning: urllib3 (2.6.3) or chardet (6.0.0.post1)/charset_normalizer (3.4.4) doesn't match a supported version!
[2m[WebServer] [22m  warnings.warn(
[2m[WebServer] [22mINFO:     Started server process [74088]
[2m[WebServer] [22mINFO:     Waiting for application startup.
[2m[WebServer] [22mWARNING:  RAGFlow config loaded: path=D:\ProjectPackage\RagflowAuth\ragflow_config.json base_url=http://127.0.0.1:9380 api_key=ragflo��FFBs (configured)
[2m[WebServer] [22mWARNING:  RAGFlow client init: base_url=http://127.0.0.1:9380 api_key=ragflo��FFBs
[2m[WebServer] [22mWARNING:  Runtime python=C:\Users\BJB110\AppData\Local\Programs\Python\Python312\python.exe ragflow_chat_service=D:\ProjectPackage\RagflowAuth\backend\services\ragflow_chat_service.py mtime_ns=1772794782813123900
[2m[WebServer] [22mINFO:     Application startup complete.
[2m[WebServer] [22mINFO:     Uvicorn running on http://0.0.0.0:38002 (Press CTRL+C to quit)
[2m[WebServer] [22m(node:62468) [DEP0176] DeprecationWarning: fs.F_OK is deprecated, use fs.constants.F_OK instead
[2m[WebServer] [22m(Use `node --trace-deprecation ...` to show where the warning was created)
[2m[WebServer] [22m(node:62468) [DEP_WEBPACK_DEV_SERVER_ON_AFTER_SETUP_MIDDLEWARE] DeprecationWarning: 'onAfterSetupMiddleware' option is deprecated. Please use the 'setupMiddlewares' option.
[2m[WebServer] [22m(node:62468) [DEP_WEBPACK_DEV_SERVER_ON_BEFORE_SETUP_MIDDLEWARE] DeprecationWarning: 'onBeforeSetupMiddleware' option is deprecated. Please use the 'setupMiddlewares' option.
[2m[WebServer] [22mWARNING:  RAGFlow config loaded: path=D:\ProjectPackage\RagflowAuth\ragflow_config.json base_url=http://127.0.0.1:9380 api_key=ragflo��FFBs (configured)
[2m[WebServer] [22mWARNING:  RAGFlow client init: base_url=http://127.0.0.1:9380 api_key=ragflo��FFBs

Running 1 test using 1 worker

  ok 1 [chromium] › e2e\tests\docs.knowledge-base-config.spec.js:29:1 › Knowledge-base config covers real directory create/rename, KB create/save, non-empty delete guard, and empty delete approval @doc-e2e (11.2s)

  1 passed (28.1s)

$ D:\Programs\npx.cmd playwright test --config playwright.docs.config.js e2e/tests/docs.user-management.spec.js --workers=1
[2m[WebServer] [22mC:\Users\BJB110\AppData\Local\Programs\Python\Python312\Lib\site-packages\requests\__init__.py:113: RequestsDependencyWarning: urllib3 (2.6.3) or chardet (6.0.0.post1)/charset_normalizer (3.4.4) doesn't match a supported version!
[2m[WebServer] [22m  warnings.warn(
[2m[WebServer] [22mINFO:     Started server process [39580]
[2m[WebServer] [22mINFO:     Waiting for application startup.
[2m[WebServer] [22mWARNING:  RAGFlow config loaded: path=D:\ProjectPackage\RagflowAuth\ragflow_config.json base_url=http://127.0.0.1:9380 api_key=ragflo��FFBs (configured)
[2m[WebServer] [22mWARNING:  RAGFlow client init: base_url=http://127.0.0.1:9380 api_key=ragflo��FFBs
[2m[WebServer] [22mWARNING:  Runtime python=C:\Users\BJB110\AppData\Local\Programs\Python\Python312\python.exe ragflow_chat_service=D:\ProjectPackage\RagflowAuth\backend\services\ragflow_chat_service.py mtime_ns=1772794782813123900
[2m[WebServer] [22mINFO:     Application startup complete.
[2m[WebServer] [22mINFO:     Uvicorn running on http://0.0.0.0:38002 (Press CTRL+C to quit)
[2m[WebServer] [22m(node:59328) [DEP0176] DeprecationWarning: fs.F_OK is deprecated, use fs.constants.F_OK instead
[2m[WebServer] [22m(Use `node --trace-deprecation ...` to show where the warning was created)
[2m[WebServer] [22m(node:59328) [DEP_WEBPACK_DEV_SERVER_ON_AFTER_SETUP_MIDDLEWARE] DeprecationWarning: 'onAfterSetupMiddleware' option is deprecated. Please use the 'setupMiddlewares' option.
[2m[WebServer] [22m(node:59328) [DEP_WEBPACK_DEV_SERVER_ON_BEFORE_SETUP_MIDDLEWARE] DeprecationWarning: 'onBeforeSetupMiddleware' option is deprecated. Please use the 'setupMiddlewares' option.
[2m[WebServer] [22mWARNING:  RAGFlow config loaded: path=D:\ProjectPackage\RagflowAuth\ragflow_config.json base_url=http://127.0.0.1:9380 api_key=ragflo��FFBs (configured)
[2m[WebServer] [22mWARNING:  RAGFlow client init: base_url=http://127.0.0.1:9380 api_key=ragflo��FFBs

Running 1 test using 1 worker

  ok 1 [chromium] › e2e\tests\docs.user-management.spec.js:24:1 › User management covers real create, reset password, disable/enable, and login effects @doc-e2e (3.6s)

  1 passed (21.6s)

$ D:\Programs\npx.cmd playwright test --config playwright.docs.config.js e2e/tests/docs.permission-groups.spec.js --workers=1
[2m[WebServer] [22mC:\Users\BJB110\AppData\Local\Programs\Python\Python312\Lib\site-packages\requests\__init__.py:113: RequestsDependencyWarning: urllib3 (2.6.3) or chardet (6.0.0.post1)/charset_normalizer (3.4.4) doesn't match a supported version!
[2m[WebServer] [22m  warnings.warn(
[2m[WebServer] [22mINFO:     Started server process [67508]
[2m[WebServer] [22mINFO:     Waiting for application startup.
[2m[WebServer] [22mWARNING:  RAGFlow config loaded: path=D:\ProjectPackage\RagflowAuth\ragflow_config.json base_url=http://127.0.0.1:9380 api_key=ragflo��FFBs (configured)
[2m[WebServer] [22mWARNING:  RAGFlow client init: base_url=http://127.0.0.1:9380 api_key=ragflo��FFBs
[2m[WebServer] [22mWARNING:  Runtime python=C:\Users\BJB110\AppData\Local\Programs\Python\Python312\python.exe ragflow_chat_service=D:\ProjectPackage\RagflowAuth\backend\services\ragflow_chat_service.py mtime_ns=1772794782813123900
[2m[WebServer] [22mINFO:     Application startup complete.
[2m[WebServer] [22mINFO:     Uvicorn running on http://0.0.0.0:38002 (Press CTRL+C to quit)
[2m[WebServer] [22m(node:4640) [DEP0176] DeprecationWarning: fs.F_OK is deprecated, use fs.constants.F_OK instead
[2m[WebServer] [22m(Use `node --trace-deprecation ...` to show where the warning was created)
[2m[WebServer] [22m(node:4640) [DEP_WEBPACK_DEV_SERVER_ON_AFTER_SETUP_MIDDLEWARE] DeprecationWarning: 'onAfterSetupMiddleware' option is deprecated. Please use the 'setupMiddlewares' option.
[2m[WebServer] [22m(node:4640) [DEP_WEBPACK_DEV_SERVER_ON_BEFORE_SETUP_MIDDLEWARE] DeprecationWarning: 'onBeforeSetupMiddleware' option is deprecated. Please use the 'setupMiddlewares' option.
[2m[WebServer] [22mWARNING:  RAGFlow config loaded: path=D:\ProjectPackage\RagflowAuth\ragflow_config.json base_url=http://127.0.0.1:9380 api_key=ragflo��FFBs (configured)
[2m[WebServer] [22mWARNING:  RAGFlow client init: base_url=http://127.0.0.1:9380 api_key=ragflo��FFBs

Running 1 test using 1 worker

  ok 1 [chromium] › e2e\tests\docs.permission-groups.spec.js:16:1 › Permission groups page covers real folder create/rename/delete and group create/edit/delete @doc-e2e (17.5s)

  1 passed (35.6s)

$ D:\Programs\npx.cmd playwright test --config playwright.docs.config.js e2e/tests/docs.org-management.spec.js --workers=1
[2m[WebServer] [22mC:\Users\BJB110\AppData\Local\Programs\Python\Python312\Lib\site-packages\requests\__init__.py:113: RequestsDependencyWarning: urllib3 (2.6.3) or chardet (6.0.0.post1)/charset_normalizer (3.4.4) doesn't match a supported version!
[2m[WebServer] [22m  warnings.warn(
[2m[WebServer] [22mINFO:     Started server process [38564]
[2m[WebServer] [22mINFO:     Waiting for application startup.
[2m[WebServer] [22mWARNING:  RAGFlow config loaded: path=D:\ProjectPackage\RagflowAuth\ragflow_config.json base_url=http://127.0.0.1:9380 api_key=ragflo��FFBs (configured)
[2m[WebServer] [22mWARNING:  RAGFlow client init: base_url=http://127.0.0.1:9380 api_key=ragflo��FFBs
[2m[WebServer] [22mWARNING:  Runtime python=C:\Users\BJB110\AppData\Local\Programs\Python\Python312\python.exe ragflow_chat_service=D:\ProjectPackage\RagflowAuth\backend\services\ragflow_chat_service.py mtime_ns=1772794782813123900
[2m[WebServer] [22mINFO:     Application startup complete.
[2m[WebServer] [22mINFO:     Uvicorn running on http://0.0.0.0:38002 (Press CTRL+C to quit)
[2m[WebServer] [22m(node:42704) [DEP0176] DeprecationWarning: fs.F_OK is deprecated, use fs.constants.F_OK instead
[2m[WebServer] [22m(Use `node --trace-deprecation ...` to show where the warning was created)
[2m[WebServer] [22m(node:42704) [DEP_WEBPACK_DEV_SERVER_ON_AFTER_SETUP_MIDDLEWARE] DeprecationWarning: 'onAfterSetupMiddleware' option is deprecated. Please use the 'setupMiddlewares' option.
[2m[WebServer] [22m(node:42704) [DEP_WEBPACK_DEV_SERVER_ON_BEFORE_SETUP_MIDDLEWARE] DeprecationWarning: 'onBeforeSetupMiddleware' option is deprecated. Please use the 'setupMiddlewares' option.
[2m[WebServer] [22mWARNING:  RAGFlow config loaded: path=D:\ProjectPackage\RagflowAuth\ragflow_config.json base_url=http://127.0.0.1:9380 api_key=ragflo��FFBs (configured)
[2m[WebServer] [22mWARNING:  RAGFlow client init: base_url=http://127.0.0.1:9380 api_key=ragflo��FFBs

Running 1 test using 1 worker

  ok 1 [chromium] › e2e\tests\docs.org-management.spec.js:17:1 › Org management covers real tree search, real Excel rebuild, and real org audit trail @doc-e2e (2.7s)

  1 passed (20.9s)

$ D:\Programs\npx.cmd playwright test --config playwright.docs.config.js e2e/tests/docs.global-search.spec.js --workers=1
[2m[WebServer] [22mC:\Users\BJB110\AppData\Local\Programs\Python\Python312\Lib\site-packages\requests\__init__.py:113: RequestsDependencyWarning: urllib3 (2.6.3) or chardet (6.0.0.post1)/charset_normalizer (3.4.4) doesn't match a supported version!
[2m[WebServer] [22m  warnings.warn(
[2m[WebServer] [22mINFO:     Started server process [84152]
[2m[WebServer] [22mINFO:     Waiting for application startup.
[2m[WebServer] [22mWARNING:  RAGFlow config loaded: path=D:\ProjectPackage\RagflowAuth\ragflow_config.json base_url=http://127.0.0.1:9380 api_key=ragflo��FFBs (configured)
[2m[WebServer] [22mWARNING:  RAGFlow client init: base_url=http://127.0.0.1:9380 api_key=ragflo��FFBs
[2m[WebServer] [22mWARNING:  Runtime python=C:\Users\BJB110\AppData\Local\Programs\Python\Python312\python.exe ragflow_chat_service=D:\ProjectPackage\RagflowAuth\backend\services\ragflow_chat_service.py mtime_ns=1772794782813123900
[2m[WebServer] [22mINFO:     Application startup complete.
[2m[WebServer] [22mINFO:     Uvicorn running on http://0.0.0.0:38002 (Press CTRL+C to quit)
[2m[WebServer] [22m(node:42392) [DEP0176] DeprecationWarning: fs.F_OK is deprecated, use fs.constants.F_OK instead
[2m[WebServer] [22m(Use `node --trace-deprecation ...` to show where the warning was created)
[2m[WebServer] [22m(node:42392) [DEP_WEBPACK_DEV_SERVER_ON_AFTER_SETUP_MIDDLEWARE] DeprecationWarning: 'onAfterSetupMiddleware' option is deprecated. Please use the 'setupMiddlewares' option.
[2m[WebServer] [22m(node:42392) [DEP_WEBPACK_DEV_SERVER_ON_BEFORE_SETUP_MIDDLEWARE] DeprecationWarning: 'onBeforeSetupMiddleware' option is deprecated. Please use the 'setupMiddlewares' option.
[2m[WebServer] [22mWARNING:  RAGFlow config loaded: path=D:\ProjectPackage\RagflowAuth\ragflow_config.json base_url=http://127.0.0.1:9380 api_key=ragflo��FFBs (configured)
[2m[WebServer] [22mWARNING:  RAGFlow client init: base_url=http://127.0.0.1:9380 api_key=ragflo��FFBs

Running 1 test using 1 worker

  ok 1 [chromium] › e2e\tests\docs.global-search.spec.js:19:1 › Doc: global search returns real uploaded/approved knowledge chunk @doc-e2e (8.4s)

  1 passed (25.3s)

$ D:\Programs\npx.cmd playwright test --config playwright.docs.config.js e2e/tests/docs.chat.spec.js --workers=1
[2m[WebServer] [22mC:\Users\BJB110\AppData\Local\Programs\Python\Python312\Lib\site-packages\requests\__init__.py:113: RequestsDependencyWarning: urllib3 (2.6.3) or chardet (6.0.0.post1)/charset_normalizer (3.4.4) doesn't match a supported version!
[2m[WebServer] [22m  warnings.warn(
[2m[WebServer] [22mINFO:     Started server process [20392]
[2m[WebServer] [22mINFO:     Waiting for application startup.
[2m[WebServer] [22mWARNING:  RAGFlow config loaded: path=D:\ProjectPackage\RagflowAuth\ragflow_config.json base_url=http://127.0.0.1:9380 api_key=ragflo��FFBs (configured)
[2m[WebServer] [22mWARNING:  RAGFlow client init: base_url=http://127.0.0.1:9380 api_key=ragflo��FFBs
[2m[WebServer] [22mWARNING:  Runtime python=C:\Users\BJB110\AppData\Local\Programs\Python\Python312\python.exe ragflow_chat_service=D:\ProjectPackage\RagflowAuth\backend\services\ragflow_chat_service.py mtime_ns=1772794782813123900
[2m[WebServer] [22mINFO:     Application startup complete.
[2m[WebServer] [22mINFO:     Uvicorn running on http://0.0.0.0:38002 (Press CTRL+C to quit)
[2m[WebServer] [22m(node:45600) [DEP0176] DeprecationWarning: fs.F_OK is deprecated, use fs.constants.F_OK instead
[2m[WebServer] [22m(Use `node --trace-deprecation ...` to show where the warning was created)
[2m[WebServer] [22m(node:45600) [DEP_WEBPACK_DEV_SERVER_ON_AFTER_SETUP_MIDDLEWARE] DeprecationWarning: 'onAfterSetupMiddleware' option is deprecated. Please use the 'setupMiddlewares' option.
[2m[WebServer] [22m(node:45600) [DEP_WEBPACK_DEV_SERVER_ON_BEFORE_SETUP_MIDDLEWARE] DeprecationWarning: 'onBeforeSetupMiddleware' option is deprecated. Please use the 'setupMiddlewares' option.
[2m[WebServer] [22mWARNING:  RAGFlow config loaded: path=D:\ProjectPackage\RagflowAuth\ragflow_config.json base_url=http://127.0.0.1:9380 api_key=ragflo��FFBs (configured)
[2m[WebServer] [22mWARNING:  RAGFlow client init: base_url=http://127.0.0.1:9380 api_key=ragflo��FFBs

Running 1 test using 1 worker

  ok 1 [chromium] › e2e\tests\docs.chat.spec.js:24:1 › Doc: smart chat uses real knowledge and returns non-empty answer @doc-e2e (14.1s)

  1 passed (31.7s)

$ D:\Programs\npx.cmd playwright test --config playwright.docs.config.js e2e/tests/docs.audit-logs.spec.js --workers=1
[2m[WebServer] [22mC:\Users\BJB110\AppData\Local\Programs\Python\Python312\Lib\site-packages\requests\__init__.py:113: RequestsDependencyWarning: urllib3 (2.6.3) or chardet (6.0.0.post1)/charset_normalizer (3.4.4) doesn't match a supported version!
[2m[WebServer] [22m  warnings.warn(
[2m[WebServer] [22mINFO:     Started server process [88688]
[2m[WebServer] [22mINFO:     Waiting for application startup.
[2m[WebServer] [22mWARNING:  RAGFlow config loaded: path=D:\ProjectPackage\RagflowAuth\ragflow_config.json base_url=http://127.0.0.1:9380 api_key=ragflo��FFBs (configured)
[2m[WebServer] [22mWARNING:  RAGFlow client init: base_url=http://127.0.0.1:9380 api_key=ragflo��FFBs
[2m[WebServer] [22mWARNING:  Runtime python=C:\Users\BJB110\AppData\Local\Programs\Python\Python312\python.exe ragflow_chat_service=D:\ProjectPackage\RagflowAuth\backend\services\ragflow_chat_service.py mtime_ns=1772794782813123900
[2m[WebServer] [22mINFO:     Application startup complete.
[2m[WebServer] [22mINFO:     Uvicorn running on http://0.0.0.0:38002 (Press CTRL+C to quit)
[2m[WebServer] [22m(node:9296) [DEP0176] DeprecationWarning: fs.F_OK is deprecated, use fs.constants.F_OK instead
[2m[WebServer] [22m(Use `node --trace-deprecation ...` to show where the warning was created)
[2m[WebServer] [22m(node:9296) [DEP_WEBPACK_DEV_SERVER_ON_AFTER_SETUP_MIDDLEWARE] DeprecationWarning: 'onAfterSetupMiddleware' option is deprecated. Please use the 'setupMiddlewares' option.
[2m[WebServer] [22m(node:9296) [DEP_WEBPACK_DEV_SERVER_ON_BEFORE_SETUP_MIDDLEWARE] DeprecationWarning: 'onBeforeSetupMiddleware' option is deprecated. Please use the 'setupMiddlewares' option.
[2m[WebServer] [22mWARNING:  RAGFlow config loaded: path=D:\ProjectPackage\RagflowAuth\ragflow_config.json base_url=http://127.0.0.1:9380 api_key=ragflo��FFBs (configured)
[2m[WebServer] [22mWARNING:  RAGFlow client init: base_url=http://127.0.0.1:9380 api_key=ragflo��FFBs

Running 1 test using 1 worker

  ok 1 [chromium] › e2e\tests\docs.audit-logs.spec.js:11:1 › Audit logs covers real auth-login query and real next/prev pagination @doc-e2e (1.1s)

  1 passed (20.1s)

$ D:\Programs\npx.cmd playwright test --config playwright.docs.config.js e2e/tests/docs.data-security.spec.js --workers=1
[2m[WebServer] [22mC:\Users\BJB110\AppData\Local\Programs\Python\Python312\Lib\site-packages\requests\__init__.py:113: RequestsDependencyWarning: urllib3 (2.6.3) or chardet (6.0.0.post1)/charset_normalizer (3.4.4) doesn't match a supported version!
[2m[WebServer] [22m  warnings.warn(
[2m[WebServer] [22mINFO:     Started server process [49924]
[2m[WebServer] [22mINFO:     Waiting for application startup.
[2m[WebServer] [22mWARNING:  RAGFlow config loaded: path=D:\ProjectPackage\RagflowAuth\ragflow_config.json base_url=http://127.0.0.1:9380 api_key=ragflo��FFBs (configured)
[2m[WebServer] [22mWARNING:  RAGFlow client init: base_url=http://127.0.0.1:9380 api_key=ragflo��FFBs
[2m[WebServer] [22mWARNING:  Runtime python=C:\Users\BJB110\AppData\Local\Programs\Python\Python312\python.exe ragflow_chat_service=D:\ProjectPackage\RagflowAuth\backend\services\ragflow_chat_service.py mtime_ns=1772794782813123900
[2m[WebServer] [22mINFO:     Application startup complete.
[2m[WebServer] [22mINFO:     Uvicorn running on http://0.0.0.0:38002 (Press CTRL+C to quit)
[2m[WebServer] [22m(node:78796) [DEP0176] DeprecationWarning: fs.F_OK is deprecated, use fs.constants.F_OK instead
[2m[WebServer] [22m(Use `node --trace-deprecation ...` to show where the warning was created)
[2m[WebServer] [22m(node:78796) [DEP_WEBPACK_DEV_SERVER_ON_AFTER_SETUP_MIDDLEWARE] DeprecationWarning: 'onAfterSetupMiddleware' option is deprecated. Please use the 'setupMiddlewares' option.
[2m[WebServer] [22m(node:78796) [DEP_WEBPACK_DEV_SERVER_ON_BEFORE_SETUP_MIDDLEWARE] DeprecationWarning: 'onBeforeSetupMiddleware' option is deprecated. Please use the 'setupMiddlewares' option.
[2m[WebServer] [22mWARNING:  RAGFlow config loaded: path=D:\ProjectPackage\RagflowAuth\ragflow_config.json base_url=http://127.0.0.1:9380 api_key=ragflo��FFBs (configured)
[2m[WebServer] [22mWARNING:  RAGFlow client init: base_url=http://127.0.0.1:9380 api_key=ragflo��FFBs

Running 1 test using 1 worker

  ok 1 [chromium] › e2e\tests\docs.data-security.spec.js:24:1 › Data security uses real retention save and real backup execution or fail-fast blocker @doc-e2e (3.6s)

  1 passed (23.6s)

$ D:\Programs\npx.cmd playwright test --config playwright.docs.config.js e2e/tests/docs.password-change.spec.js --workers=1
[2m[WebServer] [22mC:\Users\BJB110\AppData\Local\Programs\Python\Python312\Lib\site-packages\requests\__init__.py:113: RequestsDependencyWarning: urllib3 (2.6.3) or chardet (6.0.0.post1)/charset_normalizer (3.4.4) doesn't match a supported version!
[2m[WebServer] [22m  warnings.warn(
[2m[WebServer] [22mINFO:     Started server process [14060]
[2m[WebServer] [22mINFO:     Waiting for application startup.
[2m[WebServer] [22mWARNING:  RAGFlow config loaded: path=D:\ProjectPackage\RagflowAuth\ragflow_config.json base_url=http://127.0.0.1:9380 api_key=ragflo��FFBs (configured)
[2m[WebServer] [22mWARNING:  RAGFlow client init: base_url=http://127.0.0.1:9380 api_key=ragflo��FFBs
[2m[WebServer] [22mWARNING:  Runtime python=C:\Users\BJB110\AppData\Local\Programs\Python\Python312\python.exe ragflow_chat_service=D:\ProjectPackage\RagflowAuth\backend\services\ragflow_chat_service.py mtime_ns=1772794782813123900
[2m[WebServer] [22mINFO:     Application startup complete.
[2m[WebServer] [22mINFO:     Uvicorn running on http://0.0.0.0:38002 (Press CTRL+C to quit)
[2m[WebServer] [22m(node:48824) [DEP0176] DeprecationWarning: fs.F_OK is deprecated, use fs.constants.F_OK instead
[2m[WebServer] [22m(Use `node --trace-deprecation ...` to show where the warning was created)
[2m[WebServer] [22m(node:48824) [DEP_WEBPACK_DEV_SERVER_ON_AFTER_SETUP_MIDDLEWARE] DeprecationWarning: 'onAfterSetupMiddleware' option is deprecated. Please use the 'setupMiddlewares' option.
[2m[WebServer] [22m(node:48824) [DEP_WEBPACK_DEV_SERVER_ON_BEFORE_SETUP_MIDDLEWARE] DeprecationWarning: 'onBeforeSetupMiddleware' option is deprecated. Please use the 'setupMiddlewares' option.
[2m[WebServer] [22mWARNING:  RAGFlow config loaded: path=D:\ProjectPackage\RagflowAuth\ragflow_config.json base_url=http://127.0.0.1:9380 api_key=ragflo��FFBs (configured)
[2m[WebServer] [22mWARNING:  RAGFlow client init: base_url=http://127.0.0.1:9380 api_key=ragflo��FFBs

Running 1 test using 1 worker

  ok 1 [chromium] › e2e\tests\docs.password-change.spec.js:22:1 › Change password page uses real old/new password flow and login verification @doc-e2e (2.9s)

  1 passed (21.0s)

$ D:\Programs\npx.cmd playwright test --config playwright.docs.config.js e2e/tests/docs.tools.spec.js --workers=1
[2m[WebServer] [22mC:\Users\BJB110\AppData\Local\Programs\Python\Python312\Lib\site-packages\requests\__init__.py:113: RequestsDependencyWarning: urllib3 (2.6.3) or chardet (6.0.0.post1)/charset_normalizer (3.4.4) doesn't match a supported version!
[2m[WebServer] [22m  warnings.warn(
[2m[WebServer] [22mINFO:     Started server process [32216]
[2m[WebServer] [22mINFO:     Waiting for application startup.
[2m[WebServer] [22mWARNING:  RAGFlow config loaded: path=D:\ProjectPackage\RagflowAuth\ragflow_config.json base_url=http://127.0.0.1:9380 api_key=ragflo��FFBs (configured)
[2m[WebServer] [22mWARNING:  RAGFlow client init: base_url=http://127.0.0.1:9380 api_key=ragflo��FFBs
[2m[WebServer] [22mWARNING:  Runtime python=C:\Users\BJB110\AppData\Local\Programs\Python\Python312\python.exe ragflow_chat_service=D:\ProjectPackage\RagflowAuth\backend\services\ragflow_chat_service.py mtime_ns=1772794782813123900
[2m[WebServer] [22mINFO:     Application startup complete.
[2m[WebServer] [22mINFO:     Uvicorn running on http://0.0.0.0:38002 (Press CTRL+C to quit)
[2m[WebServer] [22m(node:22260) [DEP0176] DeprecationWarning: fs.F_OK is deprecated, use fs.constants.F_OK instead
[2m[WebServer] [22m(Use `node --trace-deprecation ...` to show where the warning was created)
[2m[WebServer] [22m(node:22260) [DEP_WEBPACK_DEV_SERVER_ON_AFTER_SETUP_MIDDLEWARE] DeprecationWarning: 'onAfterSetupMiddleware' option is deprecated. Please use the 'setupMiddlewares' option.
[2m[WebServer] [22m(node:22260) [DEP_WEBPACK_DEV_SERVER_ON_BEFORE_SETUP_MIDDLEWARE] DeprecationWarning: 'onBeforeSetupMiddleware' option is deprecated. Please use the 'setupMiddlewares' option.
[2m[WebServer] [22mWARNING:  RAGFlow config loaded: path=D:\ProjectPackage\RagflowAuth\ragflow_config.json base_url=http://127.0.0.1:9380 api_key=ragflo��FFBs (configured)
[2m[WebServer] [22mWARNING:  RAGFlow client init: base_url=http://127.0.0.1:9380 api_key=ragflo��FFBs

Running 1 test using 1 worker

  ok 1 [chromium] › e2e\tests\docs.tools.spec.js:21:1 › Tools page covers real pagination, internal navigation, external popup, and empty-state visibility @doc-e2e (7.7s)

  1 passed (25.4s)

$ D:\Programs\npx.cmd playwright test --config playwright.docs.config.js e2e/tests/docs.role.permission-menu.spec.js --workers=1
[2m[WebServer] [22mC:\Users\BJB110\AppData\Local\Programs\Python\Python312\Lib\site-packages\requests\__init__.py:113: RequestsDependencyWarning: urllib3 (2.6.3) or chardet (6.0.0.post1)/charset_normalizer (3.4.4) doesn't match a supported version!
[2m[WebServer] [22m  warnings.warn(
[2m[WebServer] [22mINFO:     Started server process [2856]
[2m[WebServer] [22mINFO:     Waiting for application startup.
[2m[WebServer] [22mWARNING:  RAGFlow config loaded: path=D:\ProjectPackage\RagflowAuth\ragflow_config.json base_url=http://127.0.0.1:9380 api_key=ragflo��FFBs (configured)
[2m[WebServer] [22mWARNING:  RAGFlow client init: base_url=http://127.0.0.1:9380 api_key=ragflo��FFBs
[2m[WebServer] [22mWARNING:  Runtime python=C:\Users\BJB110\AppData\Local\Programs\Python\Python312\python.exe ragflow_chat_service=D:\ProjectPackage\RagflowAuth\backend\services\ragflow_chat_service.py mtime_ns=1772794782813123900
[2m[WebServer] [22mINFO:     Application startup complete.
[2m[WebServer] [22mINFO:     Uvicorn running on http://0.0.0.0:38002 (Press CTRL+C to quit)
[2m[WebServer] [22m(node:20412) [DEP0176] DeprecationWarning: fs.F_OK is deprecated, use fs.constants.F_OK instead
[2m[WebServer] [22m(Use `node --trace-deprecation ...` to show where the warning was created)
[2m[WebServer] [22m(node:20412) [DEP_WEBPACK_DEV_SERVER_ON_AFTER_SETUP_MIDDLEWARE] DeprecationWarning: 'onAfterSetupMiddleware' option is deprecated. Please use the 'setupMiddlewares' option.
[2m[WebServer] [22m(node:20412) [DEP_WEBPACK_DEV_SERVER_ON_BEFORE_SETUP_MIDDLEWARE] DeprecationWarning: 'onBeforeSetupMiddleware' option is deprecated. Please use the 'setupMiddlewares' option.
[2m[WebServer] [22mWARNING:  RAGFlow config loaded: path=D:\ProjectPackage\RagflowAuth\ragflow_config.json base_url=http://127.0.0.1:9380 api_key=ragflo��FFBs (configured)
[2m[WebServer] [22mWARNING:  RAGFlow client init: base_url=http://127.0.0.1:9380 api_key=ragflo��FFBs

Running 1 test using 1 worker

  ok 1 [chromium] › e2e\tests\docs.role.permission-menu.spec.js:19:1 › Role permission menu shows real menu and route changes after permission group rebinding @doc-e2e (3.7s)

  1 passed (21.4s)

$ D:\Programs\npx.cmd playwright test --config playwright.docs.config.js e2e/tests/docs.role.knowledge-scope.spec.js --workers=1
[2m[WebServer] [22mC:\Users\BJB110\AppData\Local\Programs\Python\Python312\Lib\site-packages\requests\__init__.py:113: RequestsDependencyWarning: urllib3 (2.6.3) or chardet (6.0.0.post1)/charset_normalizer (3.4.4) doesn't match a supported version!
[2m[WebServer] [22m  warnings.warn(
[2m[WebServer] [22mINFO:     Started server process [22924]
[2m[WebServer] [22mINFO:     Waiting for application startup.
[2m[WebServer] [22mWARNING:  RAGFlow config loaded: path=D:\ProjectPackage\RagflowAuth\ragflow_config.json base_url=http://127.0.0.1:9380 api_key=ragflo��FFBs (configured)
[2m[WebServer] [22mWARNING:  RAGFlow client init: base_url=http://127.0.0.1:9380 api_key=ragflo��FFBs
[2m[WebServer] [22mWARNING:  Runtime python=C:\Users\BJB110\AppData\Local\Programs\Python\Python312\python.exe ragflow_chat_service=D:\ProjectPackage\RagflowAuth\backend\services\ragflow_chat_service.py mtime_ns=1772794782813123900
[2m[WebServer] [22mINFO:     Application startup complete.
[2m[WebServer] [22mINFO:     Uvicorn running on http://0.0.0.0:38002 (Press CTRL+C to quit)
[2m[WebServer] [22m(node:39784) [DEP0176] DeprecationWarning: fs.F_OK is deprecated, use fs.constants.F_OK instead
[2m[WebServer] [22m(Use `node --trace-deprecation ...` to show where the warning was created)
[2m[WebServer] [22m(node:39784) [DEP_WEBPACK_DEV_SERVER_ON_AFTER_SETUP_MIDDLEWARE] DeprecationWarning: 'onAfterSetupMiddleware' option is deprecated. Please use the 'setupMiddlewares' option.
[2m[WebServer] [22m(node:39784) [DEP_WEBPACK_DEV_SERVER_ON_BEFORE_SETUP_MIDDLEWARE] DeprecationWarning: 'onBeforeSetupMiddleware' option is deprecated. Please use the 'setupMiddlewares' option.
[2m[WebServer] [22mWARNING:  RAGFlow config loaded: path=D:\ProjectPackage\RagflowAuth\ragflow_config.json base_url=http://127.0.0.1:9380 api_key=ragflo��FFBs (configured)
[2m[WebServer] [22mWARNING:  RAGFlow client init: base_url=http://127.0.0.1:9380 api_key=ragflo��FFBs

Running 1 test using 1 worker

  ok 1 [chromium] › e2e\tests\docs.role.knowledge-scope.spec.js:88:1 › Role knowledge scope shows real browser and search differences for different users @doc-e2e (32.6s)

  1 passed (53.9s)

$ D:\Programs\npx.cmd playwright test --config playwright.docs.config.js e2e/tests/docs.document-upload-publish.spec.js --workers=1
[2m[WebServer] [22mC:\Users\BJB110\AppData\Local\Programs\Python\Python312\Lib\site-packages\requests\__init__.py:113: RequestsDependencyWarning: urllib3 (2.6.3) or chardet (6.0.0.post1)/charset_normalizer (3.4.4) doesn't match a supported version!
[2m[WebServer] [22m  warnings.warn(
[2m[WebServer] [22mINFO:     Started server process [83780]
[2m[WebServer] [22mINFO:     Waiting for application startup.
[2m[WebServer] [22mWARNING:  RAGFlow config loaded: path=D:\ProjectPackage\RagflowAuth\ragflow_config.json base_url=http://127.0.0.1:9380 api_key=ragflo��FFBs (configured)
[2m[WebServer] [22mWARNING:  RAGFlow client init: base_url=http://127.0.0.1:9380 api_key=ragflo��FFBs
[2m[WebServer] [22mWARNING:  Runtime python=C:\Users\BJB110\AppData\Local\Programs\Python\Python312\python.exe ragflow_chat_service=D:\ProjectPackage\RagflowAuth\backend\services\ragflow_chat_service.py mtime_ns=1772794782813123900
[2m[WebServer] [22mINFO:     Application startup complete.
[2m[WebServer] [22mINFO:     Uvicorn running on http://0.0.0.0:38002 (Press CTRL+C to quit)
[2m[WebServer] [22m(node:88248) [DEP0176] DeprecationWarning: fs.F_OK is deprecated, use fs.constants.F_OK instead
[2m[WebServer] [22m(Use `node --trace-deprecation ...` to show where the warning was created)
[2m[WebServer] [22m(node:88248) [DEP_WEBPACK_DEV_SERVER_ON_AFTER_SETUP_MIDDLEWARE] DeprecationWarning: 'onAfterSetupMiddleware' option is deprecated. Please use the 'setupMiddlewares' option.
[2m[WebServer] [22m(node:88248) [DEP_WEBPACK_DEV_SERVER_ON_BEFORE_SETUP_MIDDLEWARE] DeprecationWarning: 'onBeforeSetupMiddleware' option is deprecated. Please use the 'setupMiddlewares' option.
[2m[WebServer] [22mWARNING:  RAGFlow config loaded: path=D:\ProjectPackage\RagflowAuth\ragflow_config.json base_url=http://127.0.0.1:9380 api_key=ragflo��FFBs (configured)
[2m[WebServer] [22mWARNING:  RAGFlow client init: base_url=http://127.0.0.1:9380 api_key=ragflo��FFBs

Running 1 test using 1 worker

  ok 1 [chromium] › e2e\tests\docs.document-upload-publish.spec.js:30:1 › Doc upload publish flow covers real upload, approval, browser visibility, and searchability @doc-e2e (12.2s)

  1 passed (31.0s)

$ D:\Programs\npx.cmd playwright test --config playwright.docs.config.js e2e/tests/docs.role.training-approval-flow.spec.js --workers=1
[2m[WebServer] [22mC:\Users\BJB110\AppData\Local\Programs\Python\Python312\Lib\site-packages\requests\__init__.py:113: RequestsDependencyWarning: urllib3 (2.6.3) or chardet (6.0.0.post1)/charset_normalizer (3.4.4) doesn't match a supported version!
[2m[WebServer] [22m  warnings.warn(
[2m[WebServer] [22mINFO:     Started server process [18828]
[2m[WebServer] [22mINFO:     Waiting for application startup.
[2m[WebServer] [22mWARNING:  RAGFlow config loaded: path=D:\ProjectPackage\RagflowAuth\ragflow_config.json base_url=http://127.0.0.1:9380 api_key=ragflo��FFBs (configured)
[2m[WebServer] [22mWARNING:  RAGFlow client init: base_url=http://127.0.0.1:9380 api_key=ragflo��FFBs
[2m[WebServer] [22mWARNING:  Runtime python=C:\Users\BJB110\AppData\Local\Programs\Python\Python312\python.exe ragflow_chat_service=D:\ProjectPackage\RagflowAuth\backend\services\ragflow_chat_service.py mtime_ns=1772794782813123900
[2m[WebServer] [22mINFO:     Application startup complete.
[2m[WebServer] [22mINFO:     Uvicorn running on http://0.0.0.0:38002 (Press CTRL+C to quit)
[2m[WebServer] [22m(node:32288) [DEP0176] DeprecationWarning: fs.F_OK is deprecated, use fs.constants.F_OK instead
[2m[WebServer] [22m(Use `node --trace-deprecation ...` to show where the warning was created)
[2m[WebServer] [22m(node:32288) [DEP_WEBPACK_DEV_SERVER_ON_AFTER_SETUP_MIDDLEWARE] DeprecationWarning: 'onAfterSetupMiddleware' option is deprecated. Please use the 'setupMiddlewares' option.
[2m[WebServer] [22m(node:32288) [DEP_WEBPACK_DEV_SERVER_ON_BEFORE_SETUP_MIDDLEWARE] DeprecationWarning: 'onBeforeSetupMiddleware' option is deprecated. Please use the 'setupMiddlewares' option.
[2m[WebServer] [22mWARNING:  RAGFlow config loaded: path=D:\ProjectPackage\RagflowAuth\ragflow_config.json base_url=http://127.0.0.1:9380 api_key=ragflo��FFBs (configured)
[2m[WebServer] [22mWARNING:  RAGFlow client init: base_url=http://127.0.0.1:9380 api_key=ragflo��FFBs

Running 1 test using 1 worker

  ok 1 [chromium] › e2e\tests\docs.role.training-approval-flow.spec.js:81:1 › Doc role training flow enforces real approval gates, remediation, and re-blocking @doc-e2e (9.0s)

  1 passed (28.0s)

$ D:\Programs\npx.cmd playwright test --config playwright.docs.config.js e2e/tests/docs.role.data-isolation.spec.js --workers=1
[2m[WebServer] [22mC:\Users\BJB110\AppData\Local\Programs\Python\Python312\Lib\site-packages\requests\__init__.py:113: RequestsDependencyWarning: urllib3 (2.6.3) or chardet (6.0.0.post1)/charset_normalizer (3.4.4) doesn't match a supported version!
[2m[WebServer] [22m  warnings.warn(
[2m[WebServer] [22mINFO:     Started server process [4884]
[2m[WebServer] [22mINFO:     Waiting for application startup.
[2m[WebServer] [22mWARNING:  RAGFlow config loaded: path=D:\ProjectPackage\RagflowAuth\ragflow_config.json base_url=http://127.0.0.1:9380 api_key=ragflo��FFBs (configured)
[2m[WebServer] [22mWARNING:  RAGFlow client init: base_url=http://127.0.0.1:9380 api_key=ragflo��FFBs
[2m[WebServer] [22mWARNING:  Runtime python=C:\Users\BJB110\AppData\Local\Programs\Python\Python312\python.exe ragflow_chat_service=D:\ProjectPackage\RagflowAuth\backend\services\ragflow_chat_service.py mtime_ns=1772794782813123900
[2m[WebServer] [22mINFO:     Application startup complete.
[2m[WebServer] [22mINFO:     Uvicorn running on http://0.0.0.0:38002 (Press CTRL+C to quit)
[2m[WebServer] [22m(node:54008) [DEP0176] DeprecationWarning: fs.F_OK is deprecated, use fs.constants.F_OK instead
[2m[WebServer] [22m(Use `node --trace-deprecation ...` to show where the warning was created)
[2m[WebServer] [22m(node:54008) [DEP_WEBPACK_DEV_SERVER_ON_AFTER_SETUP_MIDDLEWARE] DeprecationWarning: 'onAfterSetupMiddleware' option is deprecated. Please use the 'setupMiddlewares' option.
[2m[WebServer] [22m(node:54008) [DEP_WEBPACK_DEV_SERVER_ON_BEFORE_SETUP_MIDDLEWARE] DeprecationWarning: 'onBeforeSetupMiddleware' option is deprecated. Please use the 'setupMiddlewares' option.
[2m[WebServer] [22mWARNING:  RAGFlow config loaded: path=D:\ProjectPackage\RagflowAuth\ragflow_config.json base_url=http://127.0.0.1:9380 api_key=ragflo��FFBs (configured)
[2m[WebServer] [22mWARNING:  RAGFlow client init: base_url=http://127.0.0.1:9380 api_key=ragflo��FFBs

Running 1 test using 1 worker

  ok 1 [chromium] › e2e\tests\docs.role.data-isolation.spec.js:31:1 › Doc Role: real route guard and search/chat data isolation across accounts @doc-e2e (25.5s)

  1 passed (45.9s)
```
