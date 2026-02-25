# Fullstack Test Report

- Time: 2026-02-25 10:56:41
- Repository: `D:\ProjectPackage\RagflowAuth`
- Overall: **FAIL**

## Summary

| Scope | Exit Code | Total | Passed | Failed | Errors | Skipped |
|---|---:|---:|---:|---:|---:|---:|
| Backend | 9009 | 0 | 0 | 0 | 0 | 0 |
| Frontend | 0 | 97 | 97 | 0 | 0 | 0 |

## Commands

- Backend: `python -m unittest discover -s backend/tests -p "test_*.py"` (cwd: `D:\ProjectPackage\RagflowAuth`)
- Frontend: `npm run e2e:all` (cwd: `D:\ProjectPackage\RagflowAuth\fronted`)

## Backend Raw Output

```text

```

## Frontend Raw Output

```text

> auth-frontend@1.0.0 e2e:all
> playwright test


Running 97 tests using 16 workers

  ok  2 [chromium] › e2e\tests\admin.data-security.validation.spec.js:5:1 › data security run-full displays backend validation error (mock) @regression @admin (2.3s)
  ok  8 [chromium] › e2e\tests\admin.org-directory.api-errors.spec.js:5:1 › org directory shows error when initial load fails @regression @admin (2.7s)
  ok  4 [chromium] › e2e\tests\admin.data-security.share.validation.spec.js:5:1 › data security run backup displays backend validation error @regression @admin (3.0s)
  ok 14 [chromium] › e2e\tests\admin.users.assign-groups.error.spec.js:6:1 › users assign groups shows error on save failure @regression @admin (2.9s)
  ok  7 [chromium] › e2e\tests\admin.org-directory.audit.spec.js:5:1 › admin can create company/department and see audit (mocked) @regression @admin (3.1s)
  ok 16 [chromium] › e2e\tests\admin.users.api-errors.spec.js:6:1 › users list shows error on API failure @regression @admin (2.8s)
  ok 13 [chromium] › e2e\tests\admin.org-directory.delete.cancel.spec.js:5:1 › org directory delete confirm can be cancelled @regression @admin (2.9s)
  ok 11 [chromium] › e2e\tests\admin.permission-groups.resources.error.spec.js:5:1 › permission groups handles resources API failures gracefully @regression @admin (2.9s)
  ok  5 [chromium] › e2e\tests\admin.org-directory.audit.refresh.error.spec.js:5:1 › org directory audit refresh shows error on failure @regression @admin (3.2s)
  ok  3 [chromium] › e2e\tests\admin.data-security.settings.save.spec.js:5:1 › data security retention save persists and re-renders @regression @admin (3.6s)
  ok 10 [chromium] › e2e\tests\admin.org-directory.edit.cancel.spec.js:5:1 › org directory edit prompt can be cancelled @regression @admin (3.2s)
  ok  9 [chromium] › e2e\tests\admin.permission-groups.resources.spec.js:6:1 › permission groups can select knowledge bases and chats @regression @admin (3.4s)
  ok 15 [chromium] › e2e\tests\admin.permission-groups.crud.spec.js:6:1 › admin can CRUD permission groups via UI @regression @admin (3.4s)
  ok  1 [chromium] › e2e\tests\admin.data-security.backup.failure.spec.js:5:1 › data security run backup shows failure details and stops running @regression @admin (4.1s)
  ok 12 [chromium] › e2e\tests\admin.org-directory.edit-delete.spec.js:5:1 › admin can edit/delete org directory and filter audit (mocked) @regression @admin (3.7s)
  ok 17 [chromium] › e2e\tests\admin.users.assign-groups.spec.js:6:1 › admin can assign permission groups to user via UI @regression @admin (2.2s)
  ok 23 [chromium] › e2e\tests\agents.search.spec.js:5:1 › agents search sends expected request and renders results (mock) @regression @agents (2.1s)
  ok 20 [chromium] › e2e\tests\admin.users.delete.cancel.spec.js:6:1 › users delete confirm can be cancelled @regression @admin (2.4s)
  ok 24 [chromium] › e2e\tests\audit.logs.action-completeness.spec.js:5:1 › audit logs page renders key actions @regression @audit (2.3s)
  ok 18 [chromium] › e2e\tests\admin.users.create.spec.js:6:1 › admin can create user via UI @regression @admin (2.9s)
  ok 22 [chromium] › e2e\tests\agents.multi-kb.preview.spec.js:5:1 › agents supports multi-kb search params and unified preview for md/pdf/docx @regression @agents @preview (2.7s)
  ok  6 [chromium] › e2e\tests\admin.data-security.backup.polling.spec.js:5:1 › data security run backup polls progress until done @regression @admin (5.9s)
  ok 25 [chromium] › e2e\tests\audit.logs.filters-combined.spec.js:9:1 › audit logs supports combined filters and total count (mock) @regression @audit (2.7s)
  ok 19 [chromium] › e2e\tests\admin.users.create.validation.spec.js:6:1 › user create requires company/department @regression @admin (3.4s)
  ok 21 [chromium] › e2e\tests\admin.users.filters.spec.js:6:1 › users list client-side filters work @regression @admin (3.3s)
  ok 31 [chromium] › e2e\tests\auth.logout.spec.js:5:1 › logout clears local auth and navigates to /login @regression @auth (3.0s)
  ok 32 [chromium] › e2e\tests\auth.refresh-failure.spec.js:4:1 › refresh token failure redirects to /login and clears auth @regression @auth (3.0s)
  ok 28 [chromium] › e2e\tests\auth.change-password.spec.js:147:3 › Password Change Flow › password change validation - empty fields @smoke (3.9s)
  ok 27 [chromium] › e2e\tests\auth.change-password.spec.js:96:3 › Password Change Flow › password change validation - passwords do not match @smoke (4.4s)
  ok 29 [chromium] › e2e\tests\auth.change-password.spec.js:193:3 › Password Change Flow › password change validation - incorrect old password @smoke (4.4s)
  ok 33 [chromium] › e2e\tests\browser.api-errors.spec.js:5:1 › browser shows message when no datasets (mock) @regression @browser (3.1s)
  ok 34 [chromium] › e2e\tests\browser.api-errors.spec.js:16:1 › browser datasets 500 shows error banner (mock) @regression @browser (3.0s)
  ok 37 [chromium] › e2e\tests\browser.preview.image.spec.js:5:1 › document browser previews an image (mock) @regression @browser (3.1s)
  ok 26 [chromium] › e2e\tests\auth.change-password.spec.js:6:3 › Password Change Flow › user changes password successfully and can login with new password @smoke (5.6s)
  ok 39 [chromium] › e2e\tests\browser.preview.unsupported.spec.js:5:1 › document browser shows unsupported preview message (mock) @regression @browser (3.1s)
  ok 30 [chromium] › e2e\tests\auth.change-password.spec.js:250:3 › Password Change Flow › password change button disabled during submission @smoke (5.7s)
  ok 35 [chromium] › e2e\tests\browser.batch-download.spec.js:5:1 › browser supports selecting docs and batch download (mock) @regression @browser (3.9s)
  ok 40 [chromium] › e2e\tests\browser.ragflow.smoke.spec.js:5:1 › document browser loads and previews a text file @regression (3.6s)
  ok 36 [chromium] › e2e\tests\browser.dataset-filter-history.spec.js:5:1 › browser dataset keyword filter and recent-5 history work @regression @browser (4.3s)
  ok 41 [chromium] › e2e\tests\browser.viewer-no-download-view.spec.js:7:1 › viewer without download permission can view but not download in browser @regression @browser @rbac (3.7s)
  ok 44 [chromium] › e2e\tests\chat.think.incremental.spec.js:5:1 › chat think is incremental and not duplicated @regression @chat (2.8s)
  ok 45 [chromium] › e2e\tests\dashboard.stats.spec.js:5:1 › root route redirects to chat and shell renders @regression @dashboard (2.6s)
  ok 43 [chromium] › e2e\tests\chat.streaming.spec.js:5:1 › chat can create session, stream response, and delete session (mock) @regression @chat (3.5s)
  ok 47 [chromium] › e2e\tests\dashboard.stats.spec.js:21:1 › viewer has no admin menu entries @regression @dashboard (2.4s)
  ok 42 [chromium] › e2e\tests\chat.sources.preview.permission.spec.js:7:1 › chat shows sources/chunk and hides download when no permission @regression @chat @rbac (3.9s)
  ok 38 [chromium] › e2e\tests\browser.preview.supported-types.spec.js:7:1 › browser preview supports md/pdf/docx/xlsx/xls/csv/txt @regression @browser @preview (5.4s)
  ok 49 [chromium] › e2e\tests\documents.review.api-errors.spec.js:24:1 › documents pending list 500 shows error banner (mock) @regression @documents (2.3s)
  ok 46 [chromium] › e2e\tests\dashboard.stats.spec.js:12:1 › admin can navigate to key routes from sidebar @regression @dashboard (3.1s)
  ok 48 [chromium] › e2e\tests\documents.audit.filters.spec.js:6:1 › audit records filter by status and switch tabs (mock) @regression @audit (2.8s)
  ok 51 [chromium] › e2e\tests\documents.review.api-errors.spec.js:74:1 › documents empty pending list shows empty state (mock) @regression @documents (2.3s)
  ok 50 [chromium] › e2e\tests\documents.review.api-errors.spec.js:49:1 › documents pending list 504 shows error banner (mock) @regression @documents (2.5s)
  ok 52 [chromium] › e2e\tests\documents.review.api-errors.spec.js:95:1 › documents approve 403 shows error and keeps row (mock) @regression @documents (2.5s)
  ok 53 [chromium] › e2e\tests\documents.review.approve.spec.js:5:1 › admin can approve a pending document (mocked local docs) @regression @documents (2.5s)
  ok 54 [chromium] › e2e\tests\documents.review.batch-download.spec.js:5:1 › documents supports select-all and batch download (mock) @regression @documents (2.3s)
  ok 55 [chromium] › e2e\tests\documents.review.conflict.keep-old.spec.js:5:1 › review detects conflict and can keep old (reject new) (mock) @regression @documents (2.3s)
  ok 56 [chromium] › e2e\tests\documents.review.conflict.spec.js:5:1 › review detects conflict and can approve-overwrite (mock) @regression @documents (2.3s)
  ok 57 [chromium] › e2e\tests\documents.review.delete.spec.js:5:1 › admin can delete a local document (mock) @regression @documents (2.3s)
  ok 58 [chromium] › e2e\tests\documents.review.diff.not-supported.spec.js:14:1 › documents conflict diff rejects unsupported types (mock) @regression @documents (2.1s)
  ok 59 [chromium] › e2e\tests\documents.review.preview.error.spec.js:14:1 › documents preview failure shows error (mock) @regression @documents (2.0s)
  ok 63 [chromium] › e2e\tests\integration.diagnostics.spec.js:5:1 › diagnostics endpoints basic shape + auth @integration (1.6s)
  ok 72 [chromium] › e2e\tests\integration.permission-groups.resources.spec.js:5:1 › permission groups resources endpoints (real backend) @integration (1.4s)
  ok 76 [chromium] › e2e\tests\integration.users.reset-password.spec.js:5:1 › users reset password -> new password login works (real backend) @integration (1.7s)
  ok 77 [chromium] › e2e\tests\kbs.chat-config.dataset-selection.spec.js:5:1 › chat config keeps multi-kb selection on save/copy @regression @kbs (2.7s)
  ok 78 [chromium] › e2e\tests\kbs.config.p0.spec.js:5:1 › knowledge config p0: list/detail/save/create-copy/delete-empty-only @regression @kbs (2.6s)
  ok 62 [chromium] › e2e\tests\integration.chat.sessions.spec.js:5:1 › chat can create and delete session (real backend) @integration (7.2s)
  ok 80 [chromium] › e2e\tests\rbac.unauthorized.spec.js:5:1 › viewer cannot access /users @rbac (1.4s)
  ok 79 [chromium] › e2e\tests\rbac.reviewer.permissions-matrix.spec.js:7:1 › reviewer can review docs but cannot access admin management routes @regression @rbac (3.2s)
  ok 82 [chromium] › e2e\tests\rbac.viewer.permissions-matrix.spec.js:5:1 › viewer sidebar only shows allowed entries and blocks admin routes @regression @rbac (2.5s)
  ok 81 [chromium] › e2e\tests\rbac.uploader.permissions-matrix.spec.js:7:1 › uploader can upload but cannot access admin management routes @regression @rbac (3.1s)
  ok 83 [chromium] › e2e\tests\smoke.auth.spec.js:4:1 › login rejects wrong password @smoke (3.5s)
  ok 85 [chromium] › e2e\tests\smoke.routes.spec.js:6:1 › routes load with mocked APIs @smoke (4.3s)
  ok 84 [chromium] › e2e\tests\smoke.auth.spec.js:14:1 › login works via UI @smoke (5.2s)
  ok 86 [chromium] › e2e\tests\smoke.shell.spec.js:5:1 › app shell renders for admin @smoke @admin (3.1s)
  ok 64 [chromium] › e2e\tests\integration.documents.conflict.cancel.spec.js:22:1 › documents conflict -> close modal keeps pending (real backend) @integration (17.4s)
  ok 69 [chromium] › e2e\tests\integration.org-directory.audit.spec.js:5:1 › org directory create -> audit visible (real backend) @integration (16.9s)
  ok 87 [chromium] › e2e\tests\smoke.upload.spec.js:6:1 › upload document (mock datasets) @smoke (3.0s)
  ok 88 [chromium] › e2e\tests\unified.preview.markdown.spec.js:15:1 › unified preview renders markdown in 4 entries @regression @preview (3.1s)
  ok 89 [chromium] › e2e\tests\unified.preview.modal.spec.js:26:1 › unified preview modal behaves consistently across 4 entry points (mock) @regression @preview (3.2s)
  ok 90 [chromium] › e2e\tests\upload.api-errors.spec.js:6:1 › upload shows error when no datasets available (mock) @regression @upload (1.3s)
  ok 92 [chromium] › e2e\tests\upload.api-errors.spec.js:43:1 › upload for viewer shows no-datasets message (mock) @regression @upload (1.2s)
  ok 91 [chromium] › e2e\tests\upload.api-errors.spec.js:16:1 › upload shows error when backend upload fails (mock) @regression @upload (1.3s)
  ok 93 [chromium] › e2e\tests\upload.validation.spec.js:8:1 › upload submit is disabled when no file selected (mock) @regression @upload (1.3s)
  ok 94 [chromium] › e2e\tests\upload.validation.spec.js:23:1 › upload rejects files larger than 16MB (mock) @regression @upload (1.3s)
  ok 95 [chromium] › e2e\tests\upload.validation.spec.js:52:1 › upload datasets 500 shows error banner (mock) @regression @upload (1.3s)
  ok 96 [chromium] › e2e\tests\upload.validation.spec.js:62:1 › upload datasets network timeout shows error banner (mock) @regression @upload (1.3s)
  ok 71 [chromium] › e2e\tests\integration.permission-groups.crud.spec.js:5:1 › permission groups create -> edit -> delete (real backend) @integration (20.9s)
  ok 97 [chromium] › e2e\tests\upload.validation.spec.js:72:1 › upload uses selected kb_id in request query (mock) @regression @upload (3.2s)
  ok 61 [chromium] › e2e\tests\integration.browser.preview.approved.spec.js:8:1 › upload -> approve -> visible in browser and previewable (real backend) @integration (24.4s)
  ok 75 [chromium] › e2e\tests\integration.users.create-delete.spec.js:5:1 › users create -> delete (real backend) @integration (23.4s)
  ok 70 [chromium] › e2e\tests\integration.org-directory.edit-delete.spec.js:5:1 › org directory edit + delete (real backend) @integration (24.2s)
  ok 74 [chromium] › e2e\tests\integration.users.assign-groups.spec.js:5:1 › users assign permission groups (real backend) @integration (24.1s)
  ok 73 [chromium] › e2e\tests\integration.upload.reject.spec.js:15:1 › upload -> reject -> appears in records @integration (24.1s)
  ok 67 [chromium] › e2e\tests\integration.flow.upload-approve-search-logs.spec.js:13:1 › flow: upload -> approve -> searchable -> audit visible @integration @flow (25.5s)
  ok 65 [chromium] › e2e\tests\integration.documents.conflict.overwrite.spec.js:22:1 › documents conflict -> approve-overwrite (real backend) @integration (26.2s)
  ok 66 [chromium] › e2e\tests\integration.flow.delete-removes-search.spec.js:13:1 › flow: delete approved document removes search hit and writes delete audit @integration @flow (26.5s)
  ok 68 [chromium] › e2e\tests\integration.flow.upload-reject-search-logs.spec.js:13:1 › flow: upload -> reject -> not searchable -> upload audit visible @integration @flow (26.0s)
  ok 60 [chromium] › e2e\tests\integration.audit.downloads-deletions.spec.js:19:1 › download + delete produce audit records (real backend) @integration (27.6s)

  97 passed (41.3s)
```

