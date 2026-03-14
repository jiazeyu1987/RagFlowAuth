# Fullstack Test Report

- Time: 2026-03-14 07:26:38
- Repository: `D:\ProjectPackage\RagflowAuth`
- Overall: **PASS**

## Summary

| Scope | Exit Code | Total | Passed | Failed | Errors | Skipped |
|---|---:|---:|---:|---:|---:|---:|
| Backend | 0 | 306 | 306 | 0 | 0 | 0 |
| Frontend | 0 | 171 | 146 | 0 | 0 | 25 |

## Commands

- Backend: `python -m unittest discover -s backend/tests -p "test_*.py"` (cwd: `D:\ProjectPackage\RagflowAuth`)
- Frontend: `npm run e2e:all` (cwd: `D:\ProjectPackage\RagflowAuth\fronted`)

## Backend Raw Output

```text
python : C:\Users\BJB110\AppData\Local\Programs\Python\Python312\Lib\site-packages\requests\__init__.py:113: RequestsDe
pendencyWarning: urllib3 (2.6.3) or chardet (6.0.0.post1)/charset_normalizer (3.4.4) doesn't match a supported version!
At line:1 char:1
+ python -m unittest discover -s backend/tests -p "test_*.py"
+ ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : NotSpecified: (C:\Users\BJB110...ported version!:String) [], RemoteException
    + FullyQualifiedErrorId : NativeCommandError
 
  warnings.warn(
........................WARNING:backend.app.modules.chat.routes_chats:ragflow_chat_service.list_chats dropped non-dict 
chat items: 2
.WARNING:backend.app.modules.chat.routes_chats:ragflow_chat_service.list_chats returned non-list: bool
.......................................................................................................................
......................................WARNING:backend.services.ragflow_chat_service:RAGFlow update_chat failed with par
sed-file ownership error; retrying minimal update. msg=The dataset d_new doesn't own parsed file
WARNING:backend.services.ragflow_chat_service:RAGFlow update_chat still failed with parsed-file ownership; retrying wit
h merged dataset ids. cur=['d_old'] desired=['d_new'] merged=['d_old', 'd_new']
..WARNING:backend.services.ragflow_chat_service:RAGFlow update_chat failed with parsed-file ownership error; retrying m
inimal update. msg=The dataset abc doesn't own parsed file
ERROR:backend.services.ragflow_chat_service:RAGFlow update_chat failed (retry): The dataset abc doesn't own parsed file
..WARNING:backend.services.ragflow_chat_service:RAGFlow update_chat failed with parsed-file ownership error; retrying m
inimal update. msg=The dataset abc doesn't own parsed file
.............WARNING:backend.services.ragflow_http_client:RAGFlow GET blocked by egress policy: mode=intranet host=api.
openai.com reason=egress_blocked_by_mode: mode=intranet source=ragflow_http_client:GET host=api.openai.com
.WARNING:backend.services.ragflow_http_client:RAGFlow POST blocked by egress policy engine: egress_blocked_high_sensiti
ve_payload
.WARNING:backend.services.ragflow_http_client:RAGFlow POST blocked by egress policy engine: egress_blocked_model_not_al
lowed:gpt-4
..WARNING:backend.services.ragflow_http_client:RAGFlow SSE_POST blocked by egress policy: mode=intranet host=api.openai
.com reason=egress_blocked_by_mode: mode=intranet source=ragflow_http_client:SSE_POST host=api.openai.com
....WARNING:backend.services.ragflow_http_client:RAGFlow SSE stream ended prematurely trace_id=- url=http://127.0.0.1:9
380/api/v1/chats/c1/completions: Response ended prematurely
....WARNING:uvicorn.error:RAGFlow config loaded: path=C:\Users\BJB110\AppData\Local\Temp\ragflow_config_g5ds0ijj.json b
ase_url=http://172.30.30.57:9380 api_key=REMOTE��_KEY (configured)
.WARNING:uvicorn.error:RAGFlow config loaded: path=C:\Users\BJB110\AppData\Local\Temp\ragflow_config_lwj4uo_0.json base
_url=http://127.0.0.1:9380 api_key=ragflo��I0Mm (local_default)
.WARNING:uvicorn.error:RAGFlow config loaded: path=C:\Users\BJB110\AppData\Local\Temp\ragflow_config_g388akre.json base
_url=http://127.0.0.1:9380 api_key=LOCAL_��_KEY (configured)
..................ERROR:backend.app.modules.agents.router:[SEARCH] Error: upstream_failed
Traceback (most recent call last):
  File "D:\ProjectPackage\RagflowAuth\backend\app\modules\agents\router.py", line 107, in search_chunks
    return deps.ragflow_chat_service.retrieve_chunks(
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "D:\ProjectPackage\RagflowAuth\backend\tests\test_route_request_models_unit.py", line 114, in retrieve_chunks
    raise RuntimeError("upstream_failed")
RuntimeError: upstream_failed
..............WARNING:backend.services.task_control_service:task_metric_alert {'alert_id': 'all:failure_rate', 'level':
 'warning', 'metric': 'failure_rate', 'current_value': 0.3333, 'threshold': 0.3, 'message': 'task_failure_rate_exceeded
'}
.WARNING:backend.services.task_control_service:task_metric_alert {'alert_id': 'collection:failure_rate', 'level': 'warn
ing', 'metric': 'failure_rate', 'current_value': 0.5, 'threshold': 0.3, 'message': 'task_failure_rate_exceeded'}
.WARNING:backend.services.task_control_service:task_metric_alert {'alert_id': 'knowledge_upload:failure_rate', 'level':
 'warning', 'metric': 'failure_rate', 'current_value': 0.5, 'threshold': 0.3, 'message': 'task_failure_rate_exceeded'}
.WARNING:backend.services.task_control_service:task_metric_alert {'alert_id': 'paper_plagiarism:failure_rate', 'level':
 'warning', 'metric': 'failure_rate', 'current_value': 0.5, 'threshold': 0.3, 'message': 'task_failure_rate_exceeded'}
.WARNING:backend.services.task_control_service:task_metric_alert {'alert_id': 'nas_import:failure_rate', 'level': 'warn
ing', 'metric': 'failure_rate', 'current_value': 0.5, 'threshold': 0.3, 'message': 'task_failure_rate_exceeded'}
.........................................................
----------------------------------------------------------------------
Ran 306 tests in 14.166s

OK
```

## Frontend Raw Output

```text

> auth-frontend@1.0.0 e2e:all
> playwright test

node.exe : [2m[WebServer] [22m(node:44628) [DEP0176] DeprecationWarning: fs.F_OK is deprecated, use fs.constants.F_OK
 instead
At line:1 char:1
+ & "D:\Programs/node.exe" "D:\Programs/node_modules/npm/bin/npm-cli.js ...
+ ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : NotSpecified: ([2m[WebServer]...ts.F_OK instead:String) [], RemoteException
    + FullyQualifiedErrorId : NativeCommandError
 
[2m[WebServer] [22m(Use `node --trace-deprecation ...` to show where the warning was created)
[2m[WebServer] [22m(node:44628) [DEP_WEBPACK_DEV_SERVER_ON_AFTER_SETUP_MIDDLEWARE] DeprecationWarning: 'onAfterSetupM
iddleware' option is deprecated. Please use the 'setupMiddlewares' option.
[2m[WebServer] [22m(node:44628) [DEP_WEBPACK_DEV_SERVER_ON_BEFORE_SETUP_MIDDLEWARE] DeprecationWarning: 'onBeforeSetu
pMiddleware' option is deprecated. Please use the 'setupMiddlewares' option.

Running 171 tests using 16 workers

  ok   3 [chromium] › e2e\tests\admin.data-security.share.validation.spec.js:5:1 › data security run backup displays backend validation error @regression @admin (1.3s)
  ok   1 [chromium] › e2e\tests\admin.data-security.settings.save.spec.js:5:1 › data security retention save persists and re-renders @regression @admin (1.9s)
  ok   2 [chromium] › e2e\tests\admin.org-directory.audit.spec.js:5:1 › admin can create company/department and see audit (mocked) @regression @admin (2.0s)
  ok  14 [chromium] › e2e\tests\admin.users.api-errors.spec.js:6:1 › users list shows error on API failure @regression @admin (1.7s)
  ok  10 [chromium] › e2e\tests\admin.org-directory.api-errors.spec.js:5:1 › org directory shows error when initial load fails @regression @admin (1.7s)
  ok   6 [chromium] › e2e\tests\admin.data-security.validation.spec.js:5:1 › data security run-full displays backend validation error (mock) @regression @admin (1.9s)
  ok  13 [chromium] › e2e\tests\admin.permission-groups.resources.error.spec.js:5:1 › permission groups handles resources API failures gracefully @regression @admin (1.9s)
  ok  11 [chromium] › e2e\tests\admin.users.admin-account-actions.spec.js:6:1 › admin account row only shows reset-password action @regression @admin (1.9s)
  ok   5 [chromium] › e2e\tests\admin.org-directory.audit.refresh.error.spec.js:5:1 › org directory audit refresh shows error on failure @regression @admin (2.3s)
  ok   9 [chromium] › e2e\tests\admin.org-directory.edit.cancel.spec.js:5:1 › org directory edit prompt can be cancelled @regression @admin (2.2s)
  ok   8 [chromium] › e2e\tests\admin.org-directory.delete.cancel.spec.js:5:1 › org directory delete confirm can be cancelled @regression @admin (2.4s)
  ok  16 [chromium] › e2e\tests\admin.permission-groups.resources.spec.js:6:1 › permission groups can select knowledge bases and chats @regression @admin (2.2s)
  ok  17 [chromium] › e2e\tests\admin.users.assign-groups.error.spec.js:6:1 › users assign groups shows error on save failure @regression @admin (1.4s)
  ok  15 [chromium] › e2e\tests\admin.permission-groups.crud.spec.js:6:1 › admin can CRUD permission groups via UI @regression @admin (2.7s)
  ok  12 [chromium] › e2e\tests\admin.org-directory.edit-delete.spec.js:5:1 › admin can edit/delete org directory and filter audit (mocked) @regression @admin (2.8s)
  ok  18 [chromium] › e2e\tests\admin.users.assign-groups.spec.js:6:1 › admin can assign permission groups to user via UI @regression @admin (1.6s)
  ok  21 [chromium] › e2e\tests\admin.users.delete.cancel.spec.js:6:1 › users delete confirm can be cancelled @regression @admin (1.6s)
  ok  19 [chromium] › e2e\tests\admin.users.create.spec.js:6:1 › admin can create user via UI @regression @admin (1.6s)
  ok  23 [chromium] › e2e\tests\admin.users.policy.spec.js:6:1 › users policy modal updates session limit and idle timeout @regression @admin (1.5s)
  ok  20 [chromium] › e2e\tests\admin.users.create.validation.spec.js:6:1 › user create requires company/department @regression @admin (1.8s)
  -   30 [chromium] › e2e\tests\auth.change-password.spec.js:6:3 › Password Change Flow › user changes password successfully and can login with new password @smoke
  -   31 [chromium] › e2e\tests\auth.change-password.spec.js:96:3 › Password Change Flow › password change validation - passwords do not match @smoke
  ok   7 [chromium] › e2e\tests\admin.data-security.backup.failure.spec.js:5:1 › data security run backup shows failure details and stops running @regression @admin (3.7s)
  ok  25 [chromium] › e2e\tests\admin.users.toggle-status.spec.js:6:1 › users can be disabled and re-enabled from table actions @regression @admin (1.5s)
  ok  24 [chromium] › e2e\tests\admin.users.policy.validation.spec.js:6:1 › users policy modal validates ranges and blocks invalid submit @regression @admin (1.7s)
  ok  28 [chromium] › e2e\tests\audit.logs.action-completeness.spec.js:5:1 › audit logs page renders key actions @regression @audit (1.5s)
  ok  22 [chromium] › e2e\tests\admin.users.filters.spec.js:6:1 › users list client-side filters work @regression @admin (2.2s)
  -   32 [chromium] › e2e\tests\auth.change-password.spec.js:147:3 › Password Change Flow › password change validation - empty fields @smoke
  -   33 [chromium] › e2e\tests\auth.change-password.spec.js:193:3 › Password Change Flow › password change validation - incorrect old password @smoke
  -   34 [chromium] › e2e\tests\auth.change-password.spec.js:250:3 › Password Change Flow › password change button disabled during submission @smoke
  ok  29 [chromium] › e2e\tests\audit.logs.filters-combined.spec.js:9:1 › audit logs supports combined filters and total count (mock) @regression @audit (1.7s)
  ok  27 [chromium] › e2e\tests\agents.search.spec.js:5:1 › agents search sends expected request and renders results (mock) @regression @agents (2.2s)
  ok  26 [chromium] › e2e\tests\agents.multi-kb.preview.spec.js:5:1 › agents supports multi-kb search params and unified preview for md/pdf/docx @regression @agents @preview (2.7s)
  ok  37 [chromium] › e2e\tests\auth.logout.spec.js:5:1 › logout clears local auth and navigates to /login @regression @auth (1.3s)
  ok   4 [chromium] › e2e\tests\admin.data-security.backup.polling.spec.js:5:1 › data security run backup polls progress until done @regression @admin (5.3s)
  ok  36 [chromium] › e2e\tests\auth.login.disabled-account.spec.js:4:1 › disabled account shows blocked login message @regression @auth (1.6s)
  ok  38 [chromium] › e2e\tests\auth.refresh-failure.spec.js:4:1 › refresh token failure redirects to /login and clears auth @regression @auth (1.7s)
  ok  41 [chromium] › e2e\tests\browser.api-errors.spec.js:16:1 › browser datasets 500 shows error banner (mock) @regression @browser (2.1s)
  ok  44 [chromium] › e2e\tests\browser.folder-tree.spec.js:5:1 › document browser shows folder tree at left and datasets on the right @regression @browser (2.3s)
  ok  51 [chromium] › e2e\tests\chat-configs.deep-branches.spec.js:73:1 › chat configs: copy and delete failure branches show errors @regression @kbs @chat-configs (1.3s)
  ok  50 [chromium] › e2e\tests\chat-configs.deep-branches.spec.js:5:1 › chat configs: locked branch supports save-name-only and clear parsed files @regression @kbs @chat-configs (1.5s)
  ok  39 [chromium] › e2e\tests\auth.session-timeout-redirect.spec.js:4:1 › session timeout on business API redirects to /login and clears auth @regression @auth (3.1s)
  ok  53 [chromium] › e2e\tests\chat.sources.preview.permission.spec.js:7:1 › chat shows sources/chunk and hides download when no permission @regression @chat @rbac (1.7s)
  ok  52 [chromium] › e2e\tests\chat.first-turn.rename-nonblocking.spec.js:5:1 › chat first turn is not blocked by slow auto-rename @regression @chat (1.9s)
  ok  35 [chromium] › e2e\tests\auth.idle-timeout-auto-redirect.spec.js:4:1 › idle timeout auto-redirects to /login without API activity @regression @auth (3.7s)
  ok  54 [chromium] › e2e\tests\chat.stream.answer-shape-compat.spec.js:5:1 › chat stream renders when answer arrives as data.content @regression @chat (1.5s)
  ok  56 [chromium] › e2e\tests\chat.stream.deep-answer.spec.js:5:1 › chat stream renders answer from deep choices-delta structure @regression @chat (1.3s)
  ok  55 [chromium] › e2e\tests\chat.stream.auto-refresh-empty.spec.js:5:1 › chat auto-refreshes current session when stream has no renderable answer @regression @chat (1.4s)
  ok  57 [chromium] › e2e\tests\chat.stream.disconnect.spec.js:5:1 › chat stream disconnect shows error banner @regression @chat (1.4s)
  ok  40 [chromium] › e2e\tests\browser.api-errors.spec.js:5:1 › browser shows message when no datasets (mock) @regression @browser (4.2s)
  ok  58 [chromium] › e2e\tests\chat.stream.json-fallback.spec.js:5:1 › chat renders when completions returns plain JSON body @regression @chat (1.3s)
  ok  42 [chromium] › e2e\tests\browser.batch-download.spec.js:5:1 › browser supports selecting docs and batch download (mock) @regression @browser (4.6s)
  ok  45 [chromium] › e2e\tests\browser.preview.image.spec.js:5:1 › document browser previews an image (mock) @regression @browser (4.5s)
  ok  59 [chromium] › e2e\tests\chat.stream.network-abort.spec.js:5:1 › chat network abort shows non-business error banner @regression @chat (1.5s)
  ok  47 [chromium] › e2e\tests\browser.preview.unsupported.spec.js:5:1 › document browser shows unsupported preview message (mock) @regression @browser (4.4s)
  ok  48 [chromium] › e2e\tests\browser.ragflow.smoke.spec.js:5:1 › document browser loads and previews a text file @regression (4.5s)
  ok  43 [chromium] › e2e\tests\browser.dataset-filter-history.spec.js:5:1 › browser dataset keyword filter and recent-5 history work @regression @browser (5.1s)
  ok  65 [chromium] › e2e\tests\collection.workbench.feature-flag.spec.js:5:1 › collection workbench falls back to legacy layout when flag disabled @regression @tools (1.3s)
  ok  60 [chromium] › e2e\tests\chat.stream.partial-read-failure.spec.js:5:1 › chat recovers after partial-token stream read failure @regression @chat (2.3s)
  ok  62 [chromium] › e2e\tests\chat.stream.tail-buffer.spec.js:5:1 › chat handles SSE tail buffer without trailing newline @regression @chat (2.2s)
  ok  49 [chromium] › e2e\tests\browser.viewer-no-download-view.spec.js:7:1 › viewer without download permission can view but not download in browser @regression @browser @rbac (4.6s)
  ok  61 [chromium] › e2e\tests\chat.stream.recovery.spec.js:5:1 › chat can recover after non-business stream failure and continue conversation @regression @chat (2.4s)
  ok  66 [chromium] › e2e\tests\collection.workbench.spec.js:5:1 › collection workbench supports task control and batch ingest @regression @tools (1.7s)
  ok  64 [chromium] › e2e\tests\chat.think.incremental.spec.js:5:1 › chat think is incremental and not duplicated @regression @chat (2.0s)
  ok  46 [chromium] › e2e\tests\browser.preview.supported-types.spec.js:7:1 › browser preview supports md/pdf/docx/xlsx/xls/csv/txt @regression @browser @preview (5.8s)
  ok  70 [chromium] › e2e\tests\dashboard.stats.spec.js:32:1 › dashboard shows empty state when user has no dashboard cards @regression @dashboard (1.4s)
  ok  71 [chromium] › e2e\tests\dashboard.stats.spec.js:38:1 › dashboard route renders stats cards from backend stats API @regression @dashboard (1.5s)
  ok  73 [chromium] › e2e\tests\dashboard.stats.spec.js:93:1 › dashboard shows stats error when stats API fails @regression @dashboard (1.3s)
  ok  63 [chromium] › e2e\tests\chat.streaming.spec.js:5:1 › chat can create session, stream response, and delete session (mock) @regression @chat (2.6s)
  ok  67 [chromium] › e2e\tests\dashboard.stats.spec.js:5:1 › root route redirects to chat and shell renders @regression @dashboard (2.3s)
  ok  74 [chromium] › e2e\tests\data-security.advanced-panel.spec.js:5:1 › data security advanced settings are gated by query flag @regression @admin (1.8s)
  ok  69 [chromium] › e2e\tests\dashboard.stats.spec.js:21:1 › viewer has no admin menu entries @regression @dashboard (2.4s)
  ok  68 [chromium] › e2e\tests\dashboard.stats.spec.js:12:1 › admin can navigate to key routes from sidebar @regression @dashboard (2.6s)
  ok  72 [chromium] › e2e\tests\dashboard.stats.spec.js:61:1 › dashboard quick actions navigate to target routes @regression @dashboard (2.5s)
  ok  75 [chromium] › e2e\tests\documents.audit.filters.spec.js:6:1 › audit records filter by status and switch tabs (mock) @regression @audit (2.2s)
  ok  78 [chromium] › e2e\tests\documents.review.api-errors.spec.js:74:1 › documents empty pending list shows empty state (mock) @regression @documents (2.1s)
  ok  77 [chromium] › e2e\tests\documents.review.api-errors.spec.js:49:1 › documents pending list 504 shows error banner (mock) @regression @documents (2.1s)
  ok  76 [chromium] › e2e\tests\documents.review.api-errors.spec.js:24:1 › documents pending list 500 shows error banner (mock) @regression @documents (2.2s)
  ok  79 [chromium] › e2e\tests\documents.review.api-errors.spec.js:95:1 › documents approve 403 shows error and keeps row (mock) @regression @documents (2.3s)
  ok  80 [chromium] › e2e\tests\documents.review.approve.spec.js:5:1 › admin can approve a pending document (mocked local docs) @regression @documents (2.2s)
  ok  87 [chromium] › e2e\tests\drug-admin.failures.spec.js:5:1 › drug admin resolve and verify failures show error messages @regression @tools @drug-admin (1.2s)
  ok  85 [chromium] › e2e\tests\documents.review.diff.not-supported.spec.js:14:1 › documents conflict diff rejects unsupported types (mock) @regression @documents (1.8s)
  ok  88 [chromium] › e2e\tests\drug-admin.init-resolve-branches.spec.js:5:1 › drug admin: provinces init loading failure branch @regression @tools @drug-admin (1.3s)
  -   95 [chromium] › e2e\tests\integration.diagnostics.spec.js:5:1 › diagnostics endpoints basic shape + auth @integration
  ok  89 [chromium] › e2e\tests\drug-admin.init-resolve-branches.spec.js:19:1 › drug admin: resolve ok=false shows unreachable and errors without opening url @regression @tools @drug-admin (1.2s)
  -   91 [chromium] › e2e\tests\integration.audit.downloads-deletions.spec.js:19:1 › download + delete produce audit records (real backend) @integration
  ok  81 [chromium] › e2e\tests\documents.review.batch-download.spec.js:5:1 › documents supports select-all and batch download (mock) @regression @documents (2.4s)
  ok  82 [chromium] › e2e\tests\documents.review.conflict.keep-old.spec.js:5:1 › review detects conflict and can keep old (reject new) (mock) @regression @documents (2.4s)
  -   92 [chromium] › e2e\tests\integration.browser.preview.approved.spec.js:8:1 › upload -> approve -> visible in browser and previewable (real backend) @integration
  -   94 [chromium] › e2e\tests\integration.chat.sessions.spec.js:5:1 › chat can create and delete session (real backend) @integration
  -   93 [chromium] › e2e\tests\integration.chat-agents.real-flow.spec.js:17:1 › real flow: smart chat and global search are both available @integration @chat @agents @realdata
  ok  84 [chromium] › e2e\tests\documents.review.delete.spec.js:5:1 › admin can delete a local document (mock) @regression @documents (2.2s)
  ok  83 [chromium] › e2e\tests\documents.review.conflict.spec.js:5:1 › review detects conflict and can approve-overwrite (mock) @regression @documents (2.4s)
  ok  86 [chromium] › e2e\tests\documents.review.preview.error.spec.js:14:1 › documents preview failure shows error (mock) @regression @documents (2.2s)
  -   96 [chromium] › e2e\tests\integration.documents.conflict.cancel.spec.js:22:1 › documents conflict -> close modal keeps pending (real backend) @integration
  ok  90 [chromium] › e2e\tests\drug-admin.resolve-verify.spec.js:5:1 › drug admin: resolve selected province and verify all status @regression @tools @drug-admin (1.2s)
  -   97 [chromium] › e2e\tests\integration.documents.conflict.overwrite.spec.js:22:1 › documents conflict -> approve-overwrite (real backend) @integration
  -  104 [chromium] › e2e\tests\integration.permission-groups.resources.spec.js:5:1 › permission groups resources endpoints (real backend) @integration
  -   98 [chromium] › e2e\tests\integration.flow.delete-removes-search.spec.js:13:1 › flow: delete approved document removes search hit and writes delete audit @integration @flow
  -   99 [chromium] › e2e\tests\integration.flow.upload-approve-search-logs.spec.js:13:1 › flow: upload -> approve -> searchable -> audit visible @integration @flow
  -  100 [chromium] › e2e\tests\integration.flow.upload-reject-search-logs.spec.js:13:1 › flow: upload -> reject -> not searchable -> upload audit visible @integration @flow
  -  102 [chromium] › e2e\tests\integration.org-directory.edit-delete.spec.js:5:1 › org directory edit + delete (real backend) @integration
  -  101 [chromium] › e2e\tests\integration.org-directory.audit.spec.js:5:1 › org directory create -> audit visible (real backend) @integration
  -  110 [chromium] › e2e\tests\integration.users.reset-password.spec.js:5:1 › users reset password -> new password login works (real backend) @integration
  -  103 [chromium] › e2e\tests\integration.permission-groups.crud.spec.js:5:1 › permission groups create -> edit -> delete (real backend) @integration
  -  105 [chromium] › e2e\tests\integration.ragflow.real-chat.multiturn.spec.js:6:1 › ragflow real chat: multi-turn responses on target chat @integration @chat @realdata
  -  108 [chromium] › e2e\tests\integration.ragflow.real-search.matrix.spec.js:6:1 › ragflow real search: keyword matrix on agents page @integration @agents @realdata
  -  106 [chromium] › e2e\tests\integration.upload.reject.spec.js:15:1 › upload -> reject -> appears in records @integration
  -  109 [chromium] › e2e\tests\integration.users.create-delete.spec.js:5:1 › users create -> delete (real backend) @integration
  -  107 [chromium] › e2e\tests\integration.users.assign-groups.spec.js:5:1 › users assign permission groups (real backend) @integration
  ok 114 [chromium] › e2e\tests\kbs.directory-tree.advanced.spec.js:83:1 › kbs directory tree: drag dataset to folder failure shows error @regression @kbs (1.2s)
  ok 115 [chromium] › e2e\tests\nas.browser.basic.spec.js:5:1 › nas browser basic: list and import one file @regression @tools @nas (1.2s)
  ok 121 [chromium] › e2e\tests\nas.browser.load-cancel.spec.js:5:1 › nas browser: files loading failure branch @regression @tools @nas (1.2s)
  ok 116 [chromium] › e2e\tests\nas.browser.failures-restore.spec.js:5:1 › nas folder import failed status shows error @regression @tools @nas (1.4s)
  ok 113 [chromium] › e2e\tests\kbs.directory-tree.advanced.spec.js:5:1 › kbs directory tree: create, rename, delete directory flow @regression @kbs (1.6s)
  ok 117 [chromium] › e2e\tests\nas.browser.failures-restore.spec.js:76:1 › nas import-file failure shows error @regression @tools @nas (1.4s)
  ok 118 [chromium] › e2e\tests\nas.browser.failures-restore.spec.js:111:1 › nas restore running task from localStorage and clear after completed @regression @tools @nas (1.5s)
  ok 123 [chromium] › e2e\tests\nmpa.links.spec.js:5:1 › nmpa links: opens expected urls @regression @tools @nmpa (1.5s)
  ok 111 [chromium] › e2e\tests\kbs.chat-config.dataset-selection.spec.js:5:1 › chat config keeps multi-kb selection on save/copy @regression @kbs (1.9s)
  ok 122 [chromium] › e2e\tests\nas.browser.load-cancel.spec.js:28:1 › nas browser: dataset loading failure keeps import confirm disabled and cancel closes dialog @regression @tools @nas (1.5s)
  ok 119 [chromium] › e2e\tests\nas.browser.folder-import.details.spec.js:5:1 › nas folder import completed details: skipped and failed entries rendered @regression @tools @nas (1.7s)
  ok 112 [chromium] › e2e\tests\kbs.config.p0.spec.js:5:1 › knowledge config p0: list/detail/save/create-copy/delete-empty-only @regression @kbs (2.0s)
  ok 125 [chromium] › e2e\tests\paper-patent.preview.permission.spec.js:111:1 › patent preview in no-download role never calls patent item download API @regression @tools @patent @rbac (2.0s)
  ok 124 [chromium] › e2e\tests\paper-patent.preview.permission.spec.js:38:1 › paper preview in no-download role never calls paper item download API @regression @tools @paper @rbac (2.1s)
  ok 137 [chromium] › e2e\tests\rbac.unauthorized.spec.js:5:1 › viewer cannot access /users @rbac (1.1s)
  ok 127 [chromium] › e2e\tests\paper.download.smoke.spec.js:5:1 › paper download smoke: run once and render result @regression @tools @paper (2.1s)
  ok 138 [chromium] › e2e\tests\rbac.unauthorized.spec.js:11:1 › viewer cannot access /chat-configs @rbac (1.3s)
  ok 136 [chromium] › e2e\tests\rbac.tools.nas-admin-only.spec.js:5:1 › tools rbac: viewer cannot see nas card or access nas route @regression @rbac @tools (1.5s)
  ok 134 [chromium] › e2e\tests\rbac.admin-business-guest.matrix.spec.js:57:1 › rbac matrix: guest is redirected to login for protected routes @regression @rbac (1.7s)
  ok 120 [chromium] › e2e\tests\nas.browser.folder-import.polling.spec.js:5:1 › nas browser folder import polling: reaches completed state @regression @tools @nas (3.4s)
  ok 126 [chromium] › e2e\tests\paper.download.actions.spec.js:5:1 › paper download actions: current and history operations @regression @tools @paper (3.3s)
  ok 128 [chromium] › e2e\tests\paper.download.stop-failures.spec.js:5:1 › paper download running stop and item add/delete failure branches @regression @tools @paper (2.4s)
  ok 140 [chromium] › e2e\tests\rbac.unauthorized.spec.js:41:1 › authorized user can visit /unauthorized route directly @rbac (1.2s)
  ok 139 [chromium] › e2e\tests\rbac.unauthorized.spec.js:17:1 › /audit alias redirects to records tab in /documents @regression @rbac (1.6s)
  ok 129 [chromium] › e2e\tests\patent.download.actions.spec.js:5:1 › patent download actions: current and history operations @regression @tools @patent (2.6s)
  ok 130 [chromium] › e2e\tests\patent.download.smoke.spec.js:5:1 › patent download smoke: run once and render result @regression @tools @patent (2.6s)
  ok 132 [chromium] › e2e\tests\rbac.admin-business-guest.matrix.spec.js:6:1 › rbac matrix: admin can see admin nav and access users management @regression @rbac (2.6s)
  ok 131 [chromium] › e2e\tests\patent.download.stop-failures.spec.js:5:1 › patent download running stop and item add/delete failure branches @regression @tools @patent (2.9s)
  ok 133 [chromium] › e2e\tests\rbac.admin-business-guest.matrix.spec.js:31:1 › rbac matrix: business user can use chat but is blocked from admin routes @regression @rbac (2.9s)
  ok 143 [chromium] › e2e\tests\routes.direct-pages.spec.js:5:1 › change password route direct load renders form @regression @auth (1.3s)
  ok 145 [chromium] › e2e\tests\routes.direct-pages.spec.js:38:1 › documents audit direct route renders page @regression @audit (1.1s)
  ok 146 [chromium] › e2e\tests\routes.direct-pages.spec.js:61:1 › data security test direct route renders page @regression @admin (1.2s)
  ok 149 [chromium] › e2e\tests\search-configs.failures.spec.js:19:1 › search configs: detail loading failure branch @regression @search-configs (1.1s)
  ok 148 [chromium] › e2e\tests\search-configs.failures.spec.js:5:1 › search configs: list loading failure branch @regression @search-configs (1.2s)
  ok 152 [chromium] › e2e\tests\search-configs.rbac-save-error.spec.js:5:1 › search configs route is admin-only @regression @search-configs @rbac (1.2s)
  ok 147 [chromium] › e2e\tests\search-configs.copy-invalid.spec.js:5:1 › search configs: copy mode create and invalid json validation @regression @search-configs (1.7s)
  ok 144 [chromium] › e2e\tests\routes.direct-pages.spec.js:14:1 › documents review direct route renders page @regression @documents (2.2s)
  ok 150 [chromium] › e2e\tests\search-configs.failures.spec.js:42:1 › search configs: delete and create failure branches @regression @search-configs (1.7s)
  ok 153 [chromium] › e2e\tests\search-configs.rbac-save-error.spec.js:11:1 › search configs save api failure shows detail error @regression @search-configs (1.6s)
  ok 151 [chromium] › e2e\tests\search-configs.panel.spec.js:5:1 › search configs panel: create update delete flow @regression @search-configs (1.9s)
  ok 154 [chromium] › e2e\tests\smoke.auth.spec.js:4:1 › login rejects wrong password @smoke (1.7s)
  ok 159 [chromium] › e2e\tests\tools.external-links-tbd.spec.js:5:1 › tools external cards open links and TBD cards stay disabled @regression @tools (1.5s)
  ok 135 [chromium] › e2e\tests\rbac.reviewer.permissions-matrix.spec.js:7:1 › reviewer can review docs but cannot access admin management routes @regression @rbac (4.7s)
  ok 142 [chromium] › e2e\tests\rbac.viewer.permissions-matrix.spec.js:5:1 › viewer sidebar only shows allowed entries and blocks admin routes @regression @rbac (3.3s)
  ok 141 [chromium] › e2e\tests\rbac.uploader.permissions-matrix.spec.js:7:1 › uploader can upload but cannot access admin management routes @regression @rbac (3.7s)
  ok 164 [chromium] › e2e\tests\upload.api-errors.spec.js:6:1 › upload shows error when no datasets available (mock) @regression @upload (1.5s)
  ok 155 [chromium] › e2e\tests\smoke.auth.spec.js:24:1 › login works via UI @smoke (2.6s)
  ok 165 [chromium] › e2e\tests\upload.api-errors.spec.js:16:1 › upload shows error when backend upload fails (mock) @regression @upload (1.4s)
  ok 166 [chromium] › e2e\tests\upload.validation.spec.js:8:1 › upload submit is disabled when no file selected (mock) @regression @upload (1.2s)
  ok 167 [chromium] › e2e\tests\upload.api-errors.spec.js:43:1 › upload for viewer shows no-datasets message (mock) @regression @upload (1.2s)
  ok 168 [chromium] › e2e\tests\upload.validation.spec.js:23:1 › upload rejects files larger than 16MB (mock) @regression @upload (1.3s)
  ok 169 [chromium] › e2e\tests\upload.validation.spec.js:53:1 › upload datasets 500 shows error banner (mock) @regression @upload (1.1s)
  ok 170 [chromium] › e2e\tests\upload.validation.spec.js:63:1 › upload datasets network timeout shows error banner (mock) @regression @upload (1.1s)
  ok 161 [chromium] › e2e\tests\tools.pagination-tbd.spec.js:5:1 › tools pagination covers all pages and all TBD cards stay disabled @regression @tools (2.5s)
  ok 158 [chromium] › e2e\tests\smoke.upload.spec.js:6:1 › upload document (mock datasets) @smoke (3.4s)
  ok 160 [chromium] › e2e\tests\tools.navigation.spec.js:5:1 › tools navigation: key cards route to target pages @regression @tools (4.1s)
  ok 156 [chromium] › e2e\tests\smoke.routes.spec.js:6:1 › routes load with mocked APIs @smoke (4.8s)
  ok 171 [chromium] › e2e\tests\upload.validation.spec.js:73:1 › upload uses selected kb_id in request query (mock) @regression @upload (3.1s)
  ok 157 [chromium] › e2e\tests\smoke.shell.spec.js:5:1 › app shell renders for admin @smoke @admin (5.4s)
  ok 162 [chromium] › e2e\tests\unified.preview.markdown.spec.js:15:1 › unified preview renders markdown in 4 entries @regression @preview (6.2s)
  ok 163 [chromium] › e2e\tests\unified.preview.modal.spec.js:26:1 › unified preview modal behaves consistently across 4 entry points (mock) @regression @preview (6.2s)

  25 skipped
  146 passed (30.1s)
```

