# Fullstack Test Report

- Time: 2026-04-02 18:40:35
- Repository: `D:\ProjectPackage\RagflowAuth`
- Overall: **PASS**

## Summary

| Scope | Status | Exit Code | Detail |
|---|---|---:|---|
| Backend | PASS | 0 | 237/237 |
| Frontend Build | PASS | 0 | pass |
| Frontend Acceptance | PASS | 0 | 22/22 |

## Commands

- Backend: `python -m unittest discover -s backend/tests -p "test_*.py"` (cwd: `D:\ProjectPackage\RagflowAuth`)
- Frontend Build: `npm run build` (cwd: `D:\ProjectPackage\RagflowAuth\fronted`)
- Frontend Acceptance: `npx playwright test e2e/tests/rbac.unauthorized.spec.js e2e/tests/rbac.viewer.permissions-matrix.spec.js e2e/tests/rbac.uploader.permissions-matrix.spec.js e2e/tests/rbac.reviewer.permissions-matrix.spec.js e2e/tests/audit.logs.filters-combined.spec.js e2e/tests/document.version-history.spec.js e2e/tests/documents.review.approve.spec.js e2e/tests/review.notification.spec.js e2e/tests/review.signature.spec.js e2e/tests/document.watermark.spec.js e2e/tests/company.data-isolation.spec.js e2e/tests/admin.config-change-reason.spec.js e2e/tests/admin.data-security.backup.failure.spec.js e2e/tests/admin.data-security.backup.polling.spec.js e2e/tests/admin.data-security.settings.save.spec.js e2e/tests/admin.data-security.share.validation.spec.js e2e/tests/admin.data-security.validation.spec.js e2e/tests/data-security.advanced-panel.spec.js e2e/tests/admin.data-security.restore-drill.spec.js --workers=1` (cwd: `D:\ProjectPackage\RagflowAuth\fronted`)

## Backend Raw Output

```text
C:\Users\BJB110\AppData\Local\Programs\Python\Python312\Lib\site-packages\requests\__init__.py:113: RequestsDependencyWarning: urllib3 (2.6.3) or chardet (6.0.0.post1)/charset_normalizer (3.4.4) doesn't match a supported version!
  warnings.warn(
.........................WARNING:backend.app.modules.chat.routes_chats:ragflow_chat_service.list_chats dropped non-dict chat items: 2
.WARNING:backend.app.modules.chat.routes_chats:ragflow_chat_service.list_chats returned non-list: bool
...............................................................................................WARNING:backend.services.notification.service:Notification dispatch failed: job_id=1 channel_id=email-main err=fake_email_send_failed
......WARNING:asyncio:Executing <Task finished name='Task-286' coro=<TestPackageDrawingManagerUnit.test_import_xlsx_supports_upsert_and_partial_errors() done, defined at D:\ProjectPackage\RagflowAuth\backend\tests\test_package_drawing_manager_unit.py:41> result=None created at C:\Users\BJB110\AppData\Local\Programs\Python\Python312\Lib\asyncio\runners.py:100> took 0.188 seconds
..............................................WARNING:backend.services.ragflow_chat_service:RAGFlow update_chat failed with parsed-file ownership error; retrying minimal update. msg=The dataset d_new doesn't own parsed file
WARNING:backend.services.ragflow_chat_service:RAGFlow update_chat still failed with parsed-file ownership; retrying with merged dataset ids. cur=['d_old'] desired=['d_new'] merged=['d_old', 'd_new']
..WARNING:backend.services.ragflow_chat_service:RAGFlow update_chat failed with parsed-file ownership error; retrying minimal update. msg=The dataset abc doesn't own parsed file
ERROR:backend.services.ragflow_chat_service:RAGFlow update_chat failed (retry): The dataset abc doesn't own parsed file
..WARNING:backend.services.ragflow_chat_service:RAGFlow update_chat failed with parsed-file ownership error; retrying minimal update. msg=The dataset abc doesn't own parsed file
..............WARNING:backend.services.ragflow_http_client:RAGFlow SSE stream ended prematurely trace_id=- url=http://127.0.0.1:9380/api/v1/chats/c1/completions: Response ended prematurely
....WARNING:uvicorn.error:RAGFlow config loaded: path=C:\Users\BJB110\AppData\Local\Temp\ragflow_config_f9qs4t7k.json base_url=http://172.30.30.57:9380 api_key=REMOTE��_KEY (configured)
.WARNING:uvicorn.error:RAGFlow config loaded: path=C:\Users\BJB110\AppData\Local\Temp\ragflow_config_653vnusz.json base_url=http://127.0.0.1:9380 api_key=ragflo��I0Mm (local_default)
.WARNING:uvicorn.error:RAGFlow config loaded: path=C:\Users\BJB110\AppData\Local\Temp\ragflow_config_awjx9zyy.json base_url=http://127.0.0.1:9380 api_key=LOCAL_��_KEY (configured)
..WARNING:backend.services.approval.service:Approval notification failed without blocking transaction: event_type=review_todo_approval err=notification_service_down
WARNING:backend.services.approval.service:Approval notification failed without blocking transaction: event_type=review_approved err=notification_service_down
WARNING:backend.services.approval.service:Approval notification failed without blocking transaction: event_type=review_rejected err=notification_service_down
........ERROR:backend.app.modules.agents.router:[SEARCH] Error: upstream_failed
Traceback (most recent call last):
  File "D:\ProjectPackage\RagflowAuth\backend\app\modules\agents\router.py", line 87, in search_chunks
    return deps.ragflow_chat_service.retrieve_chunks(
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "D:\ProjectPackage\RagflowAuth\backend\tests\test_route_request_models_unit.py", line 114, in retrieve_chunks
    raise RuntimeError("upstream_failed")
RuntimeError: upstream_failed
..WARNING:backend.runtime.runner:reload mode does not support multiple workers; forcing workers=1
...WARNING:uvicorn.error:RAGFlow config loaded: path=D:\ProjectPackage\RagflowAuth\ragflow_config.json base_url=http://127.0.0.1:9380 api_key=ragflo��FFBs (configured)
WARNING:uvicorn.error:RAGFlow client init: base_url=http://127.0.0.1:9380 api_key=ragflo��FFBs
WARNING:uvicorn.error:RAGFlow config loaded: path=D:\ProjectPackage\RagflowAuth\ragflow_config.json base_url=http://127.0.0.1:9380 api_key=ragflo��FFBs (configured)
WARNING:uvicorn.error:RAGFlow client init: base_url=http://127.0.0.1:9380 api_key=ragflo��FFBs
WARNING:uvicorn.error:RAGFlow config loaded: path=D:\ProjectPackage\RagflowAuth\ragflow_config.json base_url=http://127.0.0.1:9380 api_key=ragflo��FFBs (configured)
WARNING:uvicorn.error:RAGFlow client init: base_url=http://127.0.0.1:9380 api_key=ragflo��FFBs
.WARNING:uvicorn.error:RAGFlow config loaded: path=D:\ProjectPackage\RagflowAuth\ragflow_config.json base_url=http://127.0.0.1:9380 api_key=ragflo��FFBs (configured)
WARNING:uvicorn.error:RAGFlow client init: base_url=http://127.0.0.1:9380 api_key=ragflo��FFBs
WARNING:uvicorn.error:RAGFlow config loaded: path=D:\ProjectPackage\RagflowAuth\ragflow_config.json base_url=http://127.0.0.1:9380 api_key=ragflo��FFBs (configured)
WARNING:uvicorn.error:RAGFlow client init: base_url=http://127.0.0.1:9380 api_key=ragflo��FFBs
WARNING:uvicorn.error:RAGFlow config loaded: path=D:\ProjectPackage\RagflowAuth\ragflow_config.json base_url=http://127.0.0.1:9380 api_key=ragflo��FFBs (configured)
WARNING:uvicorn.error:RAGFlow client init: base_url=http://127.0.0.1:9380 api_key=ragflo��FFBs
........................
----------------------------------------------------------------------
Ran 237 tests in 6.337s
OK
```

## Frontend Build Raw Output

```text

> auth-frontend@1.0.0 build
> react-scripts build

(node:75688) [DEP0176] DeprecationWarning: fs.F_OK is deprecated, use fs.constants.F_OK instead
(Use `node --trace-deprecation ...` to show where the warning was created)
Creating an optimized production build...
Compiled successfully.

File sizes after gzip:

  354.15 kB  build\static\js\532.c66e780e.chunk.js
  297.02 kB  build\static\js\226.16e6fd99.chunk.js
  128.34 kB  build\static\js\179.9de0fabe.chunk.js
  64.77 kB   build\static\js\main.d71a5e95.js
  18.09 kB   build\static\js\340.dd7ac6e3.chunk.js
  12.85 kB   build\static\js\901.7e912b67.chunk.js
  9.93 kB    build\static\js\834.ca126462.chunk.js
  9.9 kB     build\static\js\751.dd3224b3.chunk.js
  9.3 kB     build\static\js\438.e33789f5.chunk.js
  8.96 kB    build\static\js\486.7dc33520.chunk.js
  8.91 kB    build\static\js\941.0887adbc.chunk.js
  8.33 kB    build\static\js\12.710caf4c.chunk.js
  7.52 kB    build\static\js\380.f74f919f.chunk.js
  6.46 kB    build\static\js\17.ac6c2f97.chunk.js
  6.07 kB    build\static\js\68.b62d1f8c.chunk.js
  5.59 kB    build\static\js\408.e76146b8.chunk.js
  4.89 kB    build\static\js\186.746c9f9f.chunk.js
  4.84 kB    build\static\js\290.1b686b24.chunk.js
  4.75 kB    build\static\js\669.6e41a8fe.chunk.js
  4.41 kB    build\static\js\449.edc4197f.chunk.js
  4.36 kB    build\static\js\867.11ca0170.chunk.js
  4.14 kB    build\static\js\958.906f697b.chunk.js
  4.05 kB    build\static\js\927.d0177805.chunk.js
  3.73 kB    build\static\js\247.fede1990.chunk.js
  3.32 kB    build\static\js\772.bc169b51.chunk.js
  3.1 kB     build\static\js\913.99615794.chunk.js
  3.09 kB    build\static\js\149.97d872f6.chunk.js
  2.78 kB    build\static\js\588.e614cd09.chunk.js
  2.69 kB    build\static\js\221.00134198.chunk.js
  2.53 kB    build\static\js\649.2685c57b.chunk.js
  2.4 kB     build\static\js\827.261ba952.chunk.js
  2.1 kB     build\static\js\93.2096e730.chunk.js
  1.8 kB     build\static\js\158.0ae3635f.chunk.js
  1.79 kB    build\static\js\479.14a3c870.chunk.js
  1.1 kB     build\static\js\823.936ad428.chunk.js
  494 B      build\static\js\541.c616bbcd.chunk.js
  309 B      build\static\css\main.74379e76.css

The project was built assuming it is hosted at /.
You can control this with the homepage field in your package.json.

The build folder is ready to be deployed.
You may serve it with a static server:

  npm install -g serve
  serve -s build

Find out more about deployment here:

  https://cra.link/deployment
```

## Frontend Acceptance Raw Output

```text
[2m[WebServer] [22m(node:89888) [DEP0176] DeprecationWarning: fs.F_OK is deprecated, use fs.constants.F_OK instead
[2m[WebServer] [22m(Use `node --trace-deprecation ...` to show where the warning was created)
[2m[WebServer] [22m(node:89888) [DEP_WEBPACK_DEV_SERVER_ON_AFTER_SETUP_MIDDLEWARE] DeprecationWarning: 'onAfterSetupMiddleware' option is deprecated. Please use the 'setupMiddlewares' option.
[2m[WebServer] [22m(node:89888) [DEP_WEBPACK_DEV_SERVER_ON_BEFORE_SETUP_MIDDLEWARE] DeprecationWarning: 'onBeforeSetupMiddleware' option is deprecated. Please use the 'setupMiddlewares' option.

Running 22 tests using 1 worker

  ok  1 [chromium] › e2e\tests\admin.config-change-reason.spec.js:5:1 › upload allowed extensions save sends change_reason @regression @admin (872ms)
  ok  2 [chromium] › e2e\tests\admin.data-security.backup.failure.spec.js:5:1 › data security run backup shows failure details and stops running @regression @admin (2.6s)
  ok  3 [chromium] › e2e\tests\admin.data-security.backup.polling.spec.js:5:1 › data security run backup polls progress until done @regression @admin (4.8s)
  ok  4 [chromium] › e2e\tests\admin.data-security.restore-drill.spec.js:5:1 › data security restore drill can be recorded and listed @regression @admin (854ms)
  ok  5 [chromium] › e2e\tests\admin.data-security.settings.save.spec.js:5:1 › data security retention save persists and re-renders @regression @admin (1.0s)
  ok  6 [chromium] › e2e\tests\admin.data-security.share.validation.spec.js:5:1 › data security run backup displays backend validation error @regression @admin (713ms)
  ok  7 [chromium] › e2e\tests\admin.data-security.validation.spec.js:5:1 › data security run-full displays backend validation error (mock) @regression @admin (823ms)
  ok  8 [chromium] › e2e\tests\audit.logs.filters-combined.spec.js:9:1 › audit logs supports combined filters and total count (mock) @regression @audit (960ms)
  ok  9 [chromium] › e2e\tests\company.data-isolation.spec.js:5:1 › document list shows only current company records (mock) @regression @documents (1.1s)
  ok 10 [chromium] › e2e\tests\data-security.advanced-panel.spec.js:5:1 › data security advanced settings are gated by query flag @regression @admin (899ms)
  ok 11 [chromium] › e2e\tests\document.version-history.spec.js:6:1 › audit page opens document version history modal @regression @audit (1.0s)
  ok 12 [chromium] › e2e\tests\document.watermark.spec.js:5:1 › document preview renders backend watermark badge and overlay for onlyoffice documents (mock) @regression @preview (3.7s)
  ok 13 [chromium] › e2e\tests\documents.review.approve.spec.js:6:1 › admin can approve a pending document (mocked local docs) @regression @documents (1.2s)
  ok 14 [chromium] › e2e\tests\rbac.reviewer.permissions-matrix.spec.js:7:1 › reviewer can review docs but cannot access admin management routes @regression @rbac (1.8s)
  ok 15 [chromium] › e2e\tests\rbac.unauthorized.spec.js:5:1 › viewer cannot access /users @rbac (636ms)
  ok 16 [chromium] › e2e\tests\rbac.unauthorized.spec.js:11:1 › viewer cannot access /chat-configs @rbac (634ms)
  ok 17 [chromium] › e2e\tests\rbac.unauthorized.spec.js:17:1 › /audit alias redirects to records tab in /documents @regression @rbac (860ms)
  ok 18 [chromium] › e2e\tests\rbac.unauthorized.spec.js:41:1 › authorized user can visit /unauthorized route directly @rbac (650ms)
  ok 19 [chromium] › e2e\tests\rbac.uploader.permissions-matrix.spec.js:7:1 › uploader can upload but cannot access admin management routes @regression @rbac (1.4s)
  ok 20 [chromium] › e2e\tests\rbac.viewer.permissions-matrix.spec.js:5:1 › viewer sidebar only shows allowed entries and blocks admin routes @regression @rbac (1.1s)
  ok 21 [chromium] › e2e\tests\review.notification.spec.js:5:1 › notification settings can save channel and retry failed job @regression @admin (1.1s)
  ok 22 [chromium] › e2e\tests\review.signature.spec.js:6:1 › review actions require signature modal and submit signature payload (mock) @regression @documents (1.2s)

  22 passed (34.4s)
```

