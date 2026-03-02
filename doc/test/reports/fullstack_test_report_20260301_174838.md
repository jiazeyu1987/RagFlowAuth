# Fullstack Test Report

- Time: 2026-03-01 17:54:20
- Repository: `D:\ProjectPackage\RagflowAuth`
- Overall: **FAIL**

## Summary

| Scope | Exit Code | Total | Passed | Failed | Errors | Skipped |
|---|---:|---:|---:|---:|---:|---:|
| Backend | 1 | 0 | 0 | 0 | 0 | 0 |
| Frontend | 1 | 97 | 77 | 16 | 0 | 4 |

## Commands

- Backend: `python -m unittest discover -s backend/tests -p "test_*.py"` (cwd: `D:\ProjectPackage\RagflowAuth`)
- Frontend: `npm run e2e:all` (cwd: `D:\ProjectPackage\RagflowAuth\fronted`)

## Backend Raw Output

```text
EE..E.......E..E.............E...........................E..........EEWARNING:backend.services.ragflow_chat_service:RAGFlow update_chat failed with parsed-file ownership error; retrying minimal update. msg=The dataset d_new doesn't own parsed file
```

## Frontend Raw Output

```text

> auth-frontend@1.0.0 e2e:all
> playwright test


Running 97 tests using 16 workers

  ok  9 [chromium] › e2e\tests\admin.data-security.validation.spec.js:5:1 › data security run-full displays backend validation error (mock) @regression @admin (3.5s)
  ok 10 [chromium] › e2e\tests\admin.users.api-errors.spec.js:6:1 › users list shows error on API failure @regression @admin (3.7s)
  ok  8 [chromium] › e2e\tests\admin.org-directory.api-errors.spec.js:5:1 › org directory shows error when initial load fails @regression @admin (3.7s)
  ok  2 [chromium] › e2e\tests\admin.data-security.share.validation.spec.js:5:1 › data security run backup displays backend validation error @regression @admin (3.7s)
  ok 15 [chromium] › e2e\tests\admin.org-directory.audit.refresh.error.spec.js:5:1 › org directory audit refresh shows error on failure @regression @admin (3.8s)
  ok  6 [chromium] › e2e\tests\admin.org-directory.edit.cancel.spec.js:5:1 › org directory edit prompt can be cancelled @regression @admin (3.9s)
  ok  4 [chromium] › e2e\tests\admin.users.assign-groups.error.spec.js:6:1 › users assign groups shows error on save failure @regression @admin (4.0s)
  ok 16 [chromium] › e2e\tests\admin.org-directory.delete.cancel.spec.js:5:1 › org directory delete confirm can be cancelled @regression @admin (4.1s)
  ok 14 [chromium] › e2e\tests\admin.org-directory.audit.spec.js:5:1 › admin can create company/department and see audit (mocked) @regression @admin (4.1s)
  ok  7 [chromium] › e2e\tests\admin.org-directory.edit-delete.spec.js:5:1 › admin can edit/delete org directory and filter audit (mocked) @regression @admin (4.5s)
  ok  3 [chromium] › e2e\tests\admin.data-security.backup.failure.spec.js:5:1 › data security run backup shows failure details and stops running @regression @admin (4.6s)
  ok  1 [chromium] › e2e\tests\admin.data-security.settings.save.spec.js:5:1 › data security retention save persists and re-renders @regression @admin (4.7s)
  ok 17 [chromium] › e2e\tests\admin.users.assign-groups.spec.js:6:1 › admin can assign permission groups to user via UI @regression @admin (2.0s)
  ok 20 [chromium] › e2e\tests\admin.users.delete.cancel.spec.js:6:1 › users delete confirm can be cancelled @regression @admin (2.8s)
  x  23 [chromium] › e2e\tests\agents.search.spec.js:5:1 › agents search sends expected request and renders results (mock) @regression @agents (2.3s)
  ok 19 [chromium] › e2e\tests\admin.users.create.validation.spec.js:6:1 › user create requires company/department @regression @admin (3.1s)
  ok 22 [chromium] › e2e\tests\agents.multi-kb.preview.spec.js:5:1 › agents supports multi-kb search params and unified preview for md/pdf/docx @regression @agents @preview (3.1s)
  ok 25 [chromium] › e2e\tests\audit.logs.filters-combined.spec.js:9:1 › audit logs supports combined filters and total count (mock) @regression @audit (3.0s)
  ok 21 [chromium] › e2e\tests\admin.users.filters.spec.js:6:1 › users list client-side filters work @regression @admin (3.5s)
  ok 12 [chromium] › e2e\tests\admin.data-security.backup.polling.spec.js:5:1 › data security run backup polls progress until done @regression @admin (7.6s)
  ok 28 [chromium] › e2e\tests\auth.change-password.spec.js:147:3 › Password Change Flow › password change validation - empty fields @smoke (4.3s)
  ok 32 [chromium] › e2e\tests\browser.api-errors.spec.js:5:1 › browser shows message when no datasets (mock) @regression @browser (2.1s)
  ok 31 [chromium] › e2e\tests\auth.refresh-failure.spec.js:4:1 › refresh token failure redirects to /login and clears auth @regression @auth (2.4s)
  ok 33 [chromium] › e2e\tests\browser.api-errors.spec.js:16:1 › browser datasets 500 shows error banner (mock) @regression @browser (2.2s)
  ok 27 [chromium] › e2e\tests\auth.change-password.spec.js:96:3 › Password Change Flow › password change validation - passwords do not match @smoke (4.7s)
  ok 29 [chromium] › e2e\tests\auth.change-password.spec.js:193:3 › Password Change Flow › password change validation - incorrect old password @smoke (4.2s)
  ok 34 [chromium] › e2e\tests\browser.batch-download.spec.js:5:1 › browser supports selecting docs and batch download (mock) @regression @browser (2.5s)
  ok 26 [chromium] › e2e\tests\auth.change-password.spec.js:6:3 › Password Change Flow › user changes password successfully and can login with new password @smoke (6.0s)
  ok 35 [chromium] › e2e\tests\browser.dataset-filter-history.spec.js:5:1 › browser dataset keyword filter and recent-5 history work @regression @browser (3.0s)
  ok 36 [chromium] › e2e\tests\auth.logout.spec.js:5:1 › logout clears local auth and navigates to /login @regression @auth (2.5s)
  ok 39 [chromium] › e2e\tests\browser.preview.unsupported.spec.js:5:1 › document browser shows unsupported preview message (mock) @regression @browser (2.4s)
  ok 37 [chromium] › e2e\tests\browser.preview.image.spec.js:5:1 › document browser previews an image (mock) @regression @browser (2.6s)
  ok 40 [chromium] › e2e\tests\browser.ragflow.smoke.spec.js:5:1 › document browser loads and previews a text file @regression (2.4s)
  ok 30 [chromium] › e2e\tests\auth.change-password.spec.js:250:3 › Password Change Flow › password change button disabled during submission @smoke (5.3s)
  ok 41 [chromium] › e2e\tests\browser.viewer-no-download-view.spec.js:7:1 › viewer without download permission can view but not download in browser @regression @browser @rbac (2.7s)
  ok 42 [chromium] › e2e\tests\chat.sources.preview.permission.spec.js:7:1 › chat shows sources/chunk and hides download when no permission @regression @chat @rbac (2.5s)
  ok 45 [chromium] › e2e\tests\dashboard.stats.spec.js:5:1 › root route redirects to chat and shell renders @regression @dashboard (2.0s)
  ok 38 [chromium] › e2e\tests\browser.preview.supported-types.spec.js:7:1 › browser preview supports md/pdf/docx/xlsx/xls/csv/txt @regression @browser @preview (3.5s)
  ok 44 [chromium] › e2e\tests\chat.think.incremental.spec.js:5:1 › chat think is incremental and not duplicated @regression @chat (2.3s)
  ok 43 [chromium] › e2e\tests\chat.streaming.spec.js:5:1 › chat can create session, stream response, and delete session (mock) @regression @chat (2.9s)
  ok 49 [chromium] › e2e\tests\documents.review.api-errors.spec.js:24:1 › documents pending list 500 shows error banner (mock) @regression @documents (1.8s)
  ok 47 [chromium] › e2e\tests\dashboard.stats.spec.js:21:1 › viewer has no admin menu entries @regression @dashboard (1.9s)
  ok 50 [chromium] › e2e\tests\documents.review.api-errors.spec.js:49:1 › documents pending list 504 shows error banner (mock) @regression @documents (1.8s)
  ok 51 [chromium] › e2e\tests\documents.review.api-errors.spec.js:74:1 › documents empty pending list shows empty state (mock) @regression @documents (1.7s)
  ok 48 [chromium] › e2e\tests\documents.audit.filters.spec.js:6:1 › audit records filter by status and switch tabs (mock) @regression @audit (2.2s)
  ok 46 [chromium] › e2e\tests\dashboard.stats.spec.js:12:1 › admin can navigate to key routes from sidebar @regression @dashboard (2.3s)
  ok 52 [chromium] › e2e\tests\documents.review.api-errors.spec.js:95:1 › documents approve 403 shows error and keeps row (mock) @regression @documents (1.8s)
  ok 53 [chromium] › e2e\tests\documents.review.approve.spec.js:5:1 › admin can approve a pending document (mocked local docs) @regression @documents (2.0s)
  ok 54 [chromium] › e2e\tests\documents.review.batch-download.spec.js:5:1 › documents supports select-all and batch download (mock) @regression @documents (2.1s)
  ok 55 [chromium] › e2e\tests\documents.review.conflict.keep-old.spec.js:5:1 › review detects conflict and can keep old (reject new) (mock) @regression @documents (2.1s)
  ok 56 [chromium] › e2e\tests\documents.review.conflict.spec.js:5:1 › review detects conflict and can approve-overwrite (mock) @regression @documents (2.1s)
  ok 63 [chromium] › e2e\tests\integration.diagnostics.spec.js:5:1 › diagnostics endpoints basic shape + auth @integration (902ms)
  -  60 [chromium] › e2e\tests\integration.audit.downloads-deletions.spec.js:19:1 › download + delete produce audit records (real backend) @integration
  ok 57 [chromium] › e2e\tests\documents.review.delete.spec.js:5:1 › admin can delete a local document (mock) @regression @documents (1.9s)
  ok 58 [chromium] › e2e\tests\documents.review.diff.not-supported.spec.js:14:1 › documents conflict diff rejects unsupported types (mock) @regression @documents (1.9s)
  ok 59 [chromium] › e2e\tests\documents.review.preview.error.spec.js:14:1 › documents preview failure shows error (mock) @regression @documents (1.9s)
  -  64 [chromium] › e2e\tests\integration.documents.conflict.cancel.spec.js:22:1 › documents conflict -> close modal keeps pending (real backend) @integration
  x  72 [chromium] › e2e\tests\integration.permission-groups.resources.spec.js:5:1 › permission groups resources endpoints (real backend) @integration (536ms)
  x  24 [chromium] › e2e\tests\audit.logs.action-completeness.spec.js:5:1 › audit logs page renders key actions @regression @audit (12.2s)
  ok 70 [chromium] › e2e\tests\integration.org-directory.edit-delete.spec.js:5:1 › org directory edit + delete (real backend) @integration (6.0s)
  -  75 [chromium] › e2e\tests\integration.users.create-delete.spec.js:5:1 › users create -> delete (real backend) @integration
  -  74 [chromium] › e2e\tests\integration.users.assign-groups.spec.js:5:1 › users assign permission groups (real backend) @integration
  ok 76 [chromium] › e2e\tests\integration.users.reset-password.spec.js:5:1 › users reset password -> new password login works (real backend) @integration (490ms)
  ok 78 [chromium] › e2e\tests\kbs.chat-config.dataset-selection.spec.js:5:1 › chat config keeps multi-kb selection on save/copy @regression @kbs (1.5s)
  ok 79 [chromium] › e2e\tests\rbac.reviewer.permissions-matrix.spec.js:7:1 › reviewer can review docs but cannot access admin management routes @regression @rbac (2.4s)
  ok 80 [chromium] › e2e\tests\rbac.unauthorized.spec.js:5:1 › viewer cannot access /users @rbac (1.1s)
  ok 82 [chromium] › e2e\tests\rbac.viewer.permissions-matrix.spec.js:5:1 › viewer sidebar only shows allowed entries and blocks admin routes @regression @rbac (1.8s)
  ok 81 [chromium] › e2e\tests\rbac.uploader.permissions-matrix.spec.js:7:1 › uploader can upload but cannot access admin management routes @regression @rbac (2.4s)
  ok 83 [chromium] › e2e\tests\smoke.auth.spec.js:4:1 › login rejects wrong password @smoke (1.7s)
  ok 84 [chromium] › e2e\tests\smoke.auth.spec.js:14:1 › login works via UI @smoke (2.1s)
  x  61 [chromium] › e2e\tests\integration.browser.preview.approved.spec.js:8:1 › upload -> approve -> visible in browser and previewable (real backend) @integration (15.4s)
  x  62 [chromium] › e2e\tests\integration.chat.sessions.spec.js:5:1 › chat can create and delete session (real backend) @integration (15.5s)
  ok 86 [chromium] › e2e\tests\smoke.shell.spec.js:5:1 › app shell renders for admin @smoke @admin (1.5s)
  ok 85 [chromium] › e2e\tests\smoke.routes.spec.js:6:1 › routes load with mocked APIs @smoke (4.2s)
  ok 87 [chromium] › e2e\tests\smoke.upload.spec.js:6:1 › upload document (mock datasets) @smoke (3.1s)
  x  77 [chromium] › e2e\tests\kbs.config.p0.spec.js:5:1 › knowledge config p0: list/detail/save/create-copy/delete-empty-only @regression @kbs (11.2s)
  ok 90 [chromium] › e2e\tests\upload.api-errors.spec.js:6:1 › upload shows error when no datasets available (mock) @regression @upload (1.2s)
  ok 88 [chromium] › e2e\tests\unified.preview.modal.spec.js:26:1 › unified preview modal behaves consistently across 4 entry points (mock) @regression @preview (3.5s)
  ok 91 [chromium] › e2e\tests\upload.api-errors.spec.js:16:1 › upload shows error when backend upload fails (mock) @regression @upload (1.4s)
  ok 89 [chromium] › e2e\tests\unified.preview.markdown.spec.js:15:1 › unified preview renders markdown in 4 entries @regression @preview (3.4s)
  ok 92 [chromium] › e2e\tests\upload.validation.spec.js:8:1 › upload submit is disabled when no file selected (mock) @regression @upload (1.2s)
  ok 93 [chromium] › e2e\tests\upload.validation.spec.js:23:1 › upload rejects files larger than 16MB (mock) @regression @upload (1.3s)
  ok 94 [chromium] › e2e\tests\upload.validation.spec.js:52:1 › upload datasets 500 shows error banner (mock) @regression @upload (1.4s)
  ok 96 [chromium] › e2e\tests\upload.validation.spec.js:62:1 › upload datasets network timeout shows error banner (mock) @regression @upload (1.3s)
  ok 95 [chromium] › e2e\tests\upload.api-errors.spec.js:43:1 › upload for viewer shows no-datasets message (mock) @regression @upload (1.3s)
  ok 97 [chromium] › e2e\tests\upload.validation.spec.js:72:1 › upload uses selected kb_id in request query (mock) @regression @upload (3.2s)
  x  69 [chromium] › e2e\tests\integration.org-directory.audit.spec.js:5:1 › org directory create -> audit visible (real backend) @integration (34.4s)
  x  11 [chromium] › e2e\tests\admin.permission-groups.resources.spec.js:6:1 › permission groups can select knowledge bases and chats @regression @admin (1.0m)
  x  13 [chromium] › e2e\tests\admin.permission-groups.resources.error.spec.js:5:1 › permission groups handles resources API failures gracefully @regression @admin (1.0m)
  x   5 [chromium] › e2e\tests\admin.permission-groups.crud.spec.js:6:1 › admin can CRUD permission groups via UI @regression @admin (1.0m)
  x  18 [chromium] › e2e\tests\admin.users.create.spec.js:6:1 › admin can create user via UI @regression @admin (1.0m)
  x  71 [chromium] › e2e\tests\integration.permission-groups.crud.spec.js:5:1 › permission groups create -> edit -> delete (real backend) @integration (2.1m)
  x  73 [chromium] › e2e\tests\integration.upload.reject.spec.js:15:1 › upload -> reject -> appears in records @integration (2.1m)
  x  65 [chromium] › e2e\tests\integration.documents.conflict.overwrite.spec.js:22:1 › documents conflict -> approve-overwrite (real backend) @integration (3.1m)
  x  67 [chromium] › e2e\tests\integration.flow.upload-approve-search-logs.spec.js:13:1 › flow: upload -> approve -> searchable -> audit visible @integration @flow (4.2m)
  x  68 [chromium] › e2e\tests\integration.flow.upload-reject-search-logs.spec.js:13:1 › flow: upload -> reject -> not searchable -> upload audit visible @integration @flow (4.2m)
  x  66 [chromium] › e2e\tests\integration.flow.delete-removes-search.spec.js:13:1 › flow: delete approved document removes search hit and writes delete audit @integration @flow (5.2m)


  1) [chromium] › e2e\tests\admin.permission-groups.crud.spec.js:6:1 › admin can CRUD permission groups via UI @regression @admin 

    [31mTest timeout of 60000ms exceeded.[39m

    Error: locator.click: Target page, context or browser has been closed
    Call log:
    [2m  - waiting for getByTestId('pg-create-open')[22m


      71 |   await page.goto('/permission-groups');
      72 |
    > 73 |   await page.getByTestId('pg-create-open').click();
         |                                            ^
      74 |   await page.getByTestId('pg-form-group-name').fill('e2e_group');
      75 |   await page.getByTestId('pg-form-description').fill('created by e2e');
      76 |   await page.getByTestId('pg-form-can-upload').check();
        at D:\ProjectPackage\RagflowAuth\fronted\e2e\tests\admin.permission-groups.crud.spec.js:73:44

    attachment #1: screenshot (image/png) ──────────────────────────────────────────────────────────
    C:\Users\BJB110\AppData\Local\Temp\ragflowauth_playwright\admin.permission-groups.cr-76832-ups-via-UI-regression-admin-chromium\test-failed-1.png
    ────────────────────────────────────────────────────────────────────────────────────────────────

    attachment #2: trace (application/zip) ─────────────────────────────────────────────────────────
    C:\Users\BJB110\AppData\Local\Temp\ragflowauth_playwright\admin.permission-groups.cr-76832-ups-via-UI-regression-admin-chromium\trace.zip
    Usage:

        npx playwright show-trace C:\Users\BJB110\AppData\Local\Temp\ragflowauth_playwright\admin.permission-groups.cr-76832-ups-via-UI-regression-admin-chromium\trace.zip

    ────────────────────────────────────────────────────────────────────────────────────────────────

  2) [chromium] › e2e\tests\admin.permission-groups.resources.error.spec.js:5:1 › permission groups handles resources API failures gracefully @regression @admin 

    [31mTest timeout of 60000ms exceeded.[39m

    Error: locator.click: Target page, context or browser has been closed
    Call log:
    [2m  - waiting for getByTestId('pg-create-open')[22m


      34 |   await page.goto('/permission-groups');
      35 |
    > 36 |   await page.getByTestId('pg-create-open').click();
         |                                            ^
      37 |   await expect(page.getByTestId('pg-modal')).toBeVisible();
      38 |   await expect(page.getByTestId('pg-form-kb-empty')).toBeVisible();
      39 |   await expect(page.getByTestId('pg-form-chat-empty')).toBeVisible();
        at D:\ProjectPackage\RagflowAuth\fronted\e2e\tests\admin.permission-groups.resources.error.spec.js:36:44

    attachment #1: screenshot (image/png) ──────────────────────────────────────────────────────────
    C:\Users\BJB110\AppData\Local\Temp\ragflowauth_playwright\admin.permission-groups.re-b6f69-gracefully-regression-admin-chromium\test-failed-1.png
    ────────────────────────────────────────────────────────────────────────────────────────────────

    attachment #2: trace (application/zip) ─────────────────────────────────────────────────────────
    C:\Users\BJB110\AppData\Local\Temp\ragflowauth_playwright\admin.permission-groups.re-b6f69-gracefully-regression-admin-chromium\trace.zip
    Usage:

        npx playwright show-trace C:\Users\BJB110\AppData\Local\Temp\ragflowauth_playwright\admin.permission-groups.re-b6f69-gracefully-regression-admin-chromium\trace.zip

    ────────────────────────────────────────────────────────────────────────────────────────────────

  3) [chromium] › e2e\tests\admin.permission-groups.resources.spec.js:6:1 › permission groups can select knowledge bases and chats @regression @admin 

    [31mTest timeout of 60000ms exceeded.[39m

    Error: locator.click: Target page, context or browser has been closed
    Call log:
    [2m  - waiting for getByTestId('pg-edit-1')[22m


      82 |
      83 |   // Edit existing: should preselect current resources.
    > 84 |   await page.getByTestId('pg-edit-1').click();
         |                                       ^
      85 |   await expect(page.getByTestId('pg-modal')).toBeVisible();
      86 |   await expect(page.getByTestId('pg-form-kb-kb_1')).toBeChecked();
      87 |   await expect(page.getByTestId('pg-form-chat-agent_1')).toBeChecked();
        at D:\ProjectPackage\RagflowAuth\fronted\e2e\tests\admin.permission-groups.resources.spec.js:84:39

    attachment #1: screenshot (image/png) ──────────────────────────────────────────────────────────
    C:\Users\BJB110\AppData\Local\Temp\ragflowauth_playwright\admin.permission-groups.re-415dd--and-chats-regression-admin-chromium\test-failed-1.png
    ────────────────────────────────────────────────────────────────────────────────────────────────

    attachment #2: trace (application/zip) ─────────────────────────────────────────────────────────
    C:\Users\BJB110\AppData\Local\Temp\ragflowauth_playwright\admin.permission-groups.re-415dd--and-chats-regression-admin-chromium\trace.zip
    Usage:

        npx playwright show-trace C:\Users\BJB110\AppData\Local\Temp\ragflowauth_playwright\admin.permission-groups.re-415dd--and-chats-regression-admin-chromium\trace.zip

    ────────────────────────────────────────────────────────────────────────────────────────────────

  4) [chromium] › e2e\tests\admin.users.create.spec.js:6:1 › admin can create user via UI @regression @admin 

    [31mTest timeout of 60000ms exceeded.[39m

    Error: locator.click: Target page, context or browser has been closed
    Call log:
    [2m  - waiting for getByTestId('users-create-submit')[22m
    [2m    - locator resolved to <button type="submit" data-testid="users-create-submit">创建</button>[22m
    [2m  - attempting click action[22m
    [2m    2 × waiting for element to be visible, enabled and stable[22m
    [2m      - element is visible, enabled and stable[22m
    [2m      - scrolling into view if needed[22m
    [2m      - done scrolling[22m
    [2m      - element is outside of the viewport[22m
    [2m    - retrying click action[22m
    [2m    - waiting 20ms[22m
    [2m    2 × waiting for element to be visible, enabled and stable[22m
    [2m      - element is visible, enabled and stable[22m
    [2m      - scrolling into view if needed[22m
    [2m      - done scrolling[22m
    [2m      - element is outside of the viewport[22m
    [2m    - retrying click action[22m
    [2m      - waiting 100ms[22m
    [2m    109 × waiting for element to be visible, enabled and stable[22m
    [2m        - element is visible, enabled and stable[22m
    [2m        - scrolling into view if needed[22m
    [2m        - done scrolling[22m
    [2m        - element is outside of the viewport[22m
    [2m      - retrying click action[22m
    [2m        - waiting 500ms[22m


      65 |   await page.getByTestId('users-create-department').selectOption('10');
      66 |   await page.getByTestId('users-create-group-101').check();
    > 67 |   await page.getByTestId('users-create-submit').click();
         |                                                 ^
      68 |
      69 |   expect(capturedCreateBody).toBeTruthy();
      70 |   expect(capturedCreateBody.username).toBe(username);
        at D:\ProjectPackage\RagflowAuth\fronted\e2e\tests\admin.users.create.spec.js:67:49

    attachment #1: screenshot (image/png) ──────────────────────────────────────────────────────────
    C:\Users\BJB110\AppData\Local\Temp\ragflowauth_playwright\admin.users.create-admin-c-20e5e-ser-via-UI-regression-admin-chromium\test-failed-1.png
    ────────────────────────────────────────────────────────────────────────────────────────────────

    attachment #2: trace (application/zip) ─────────────────────────────────────────────────────────
    C:\Users\BJB110\AppData\Local\Temp\ragflowauth_playwright\admin.users.create-admin-c-20e5e-ser-via-UI-regression-admin-chromium\trace.zip
    Usage:

        npx playwright show-trace C:\Users\BJB110\AppData\Local\Temp\ragflowauth_playwright\admin.users.create-admin-c-20e5e-ser-via-UI-regression-admin-chromium\trace.zip

    ────────────────────────────────────────────────────────────────────────────────────────────────

  5) [chromium] › e2e\tests\agents.search.spec.js:5:1 › agents search sends expected request and renders results (mock) @regression @agents 

    Error: [2mexpect([22m[31mreceived[39m[2m).[22mtoBe[2m([22m[32mexpected[39m[2m) // Object.is equality[22m

    Expected: [32m"hello"[39m
    Received: [31m"[object Object]"[39m

      45 |
      46 |   expect(captured).toBeTruthy();
    > 47 |   expect(captured.question).toBe('hello');
         |                             ^
      48 |   expect(captured.dataset_ids).toEqual(['ds1']);
      49 |   expect(captured.page).toBe(1);
      50 |   expect(captured.page_size).toBe(30);
        at D:\ProjectPackage\RagflowAuth\fronted\e2e\tests\agents.search.spec.js:47:29

    attachment #1: screenshot (image/png) ──────────────────────────────────────────────────────────
    C:\Users\BJB110\AppData\Local\Temp\ragflowauth_playwright\agents.search-agents-searc-87587-ults-mock-regression-agents-chromium\test-failed-1.png
    ────────────────────────────────────────────────────────────────────────────────────────────────

    attachment #2: trace (application/zip) ─────────────────────────────────────────────────────────
    C:\Users\BJB110\AppData\Local\Temp\ragflowauth_playwright\agents.search-agents-searc-87587-ults-mock-regression-agents-chromium\trace.zip
    Usage:

        npx playwright show-trace C:\Users\BJB110\AppData\Local\Temp\ragflowauth_playwright\agents.search-agents-searc-87587-ults-mock-regression-agents-chromium\trace.zip

    ────────────────────────────────────────────────────────────────────────────────────────────────

  6) [chromium] › e2e\tests\audit.logs.action-completeness.spec.js:5:1 › audit logs page renders key actions @regression @audit 

    Error: [2mexpect([22m[31mlocator[39m[2m).[22mtoContainText[2m([22m[32mexpected[39m[2m)[22m failed

    Locator: getByTestId('audit-table')
    Expected substring: [32m"[7mauth_log[27min"[39m
    Received string:    [31m"[7m时间类型账号公司部门来源知识库文件3/1/2026, 5:48:51 PM登录admin3/1/2026, 5:48:52 PM退出登录admin3/1/2026, 5:48:53 PM查看/预览文档admin3/1/2026, 5:48:54 PM上传文档admin3/1/2026, 5:48:55 PM下载文档admin3/1/2026, 5:48:56 PM删除文档admin3/1/2026, 5:48:57 PMdocument_approveadmin3/1/2026, 5:48:58 PMdocument_rejectadmin3/1/2026, 5:48:59 PMpassword_changeadm[27min"[39m
    Timeout: 10000ms

    Call log:
    [2m  - Expect "toContainText" with timeout 10000ms[22m
    [2m  - waiting for getByTestId('audit-table')[22m
    [2m    13 × locator resolved to <table data-testid="audit-table">…</table>[22m
    [2m       - unexpected value "时间类型账号公司部门来源知识库文件3/1/2026, 5:48:51 PM登录admin3/1/2026, 5:48:52 PM退出登录admin3/1/2026, 5:48:53 PM查看/预览文档admin3/1/2026, 5:48:54 PM上传文档admin3/1/2026, 5:48:55 PM下载文档admin3/1/2026, 5:48:56 PM删除文档admin3/1/2026, 5:48:57 PMdocument_approveadmin3/1/2026, 5:48:58 PMdocument_rejectadmin3/1/2026, 5:48:59 PMpassword_changeadmin"[22m


      48 |     'password_change',
      49 |   ]) {
    > 50 |     await expect(table).toContainText(action);
         |                         ^
      51 |   }
      52 | });
      53 |
        at D:\ProjectPackage\RagflowAuth\fronted\e2e\tests\audit.logs.action-completeness.spec.js:50:25

    attachment #1: screenshot (image/png) ──────────────────────────────────────────────────────────
    C:\Users\BJB110\AppData\Local\Temp\ragflowauth_playwright\audit.logs.action-complete-f27c8-ey-actions-regression-audit-chromium\test-failed-1.png
    ────────────────────────────────────────────────────────────────────────────────────────────────

    attachment #2: trace (application/zip) ─────────────────────────────────────────────────────────
    C:\Users\BJB110\AppData\Local\Temp\ragflowauth_playwright\audit.logs.action-complete-f27c8-ey-actions-regression-audit-chromium\trace.zip
    Usage:

        npx playwright show-trace C:\Users\BJB110\AppData\Local\Temp\ragflowauth_playwright\audit.logs.action-complete-f27c8-ey-actions-regression-audit-chromium\trace.zip

    ────────────────────────────────────────────────────────────────────────────────────────────────

  7) [chromium] › e2e\tests\integration.chat.sessions.spec.js:5:1 › chat can create and delete session (real backend) @integration 

    Error: [2mexpect([22m[31mlocator[39m[2m).[22mtoHaveCount[2m([22m[32mexpected[39m[2m)[22m failed

    Locator:  getByTestId('chat-session-item-e71a229e155311f18d9f8eb0c0711940')
    Expected: [32m0[39m
    Received: [31m1[39m
    Timeout:  10000ms

    Call log:
    [2m  - Expect "toHaveCount" with timeout 10000ms[22m
    [2m  - waiting for getByTestId('chat-session-item-e71a229e155311f18d9f8eb0c0711940')[22m
    [2m    13 × locator resolved to 1 element[22m
    [2m       - unexpected value "1"[22m


      53 |   ]);
      54 |
    > 55 |   await expect(page.getByTestId(`chat-session-item-${sessionId}`)).toHaveCount(0);
         |                                                                    ^
      56 | });
      57 |
        at D:\ProjectPackage\RagflowAuth\fronted\e2e\tests\integration.chat.sessions.spec.js:55:68

    attachment #1: screenshot (image/png) ──────────────────────────────────────────────────────────
    C:\Users\BJB110\AppData\Local\Temp\ragflowauth_playwright\integration.chat.sessions--353f9-on-real-backend-integration-chromium\test-failed-1.png
    ────────────────────────────────────────────────────────────────────────────────────────────────

    attachment #2: video (video/webm) ──────────────────────────────────────────────────────────────
    C:\Users\BJB110\AppData\Local\Temp\ragflowauth_playwright\integration.chat.sessions--353f9-on-real-backend-integration-chromium\video.webm
    ────────────────────────────────────────────────────────────────────────────────────────────────

    Error Context: C:\Users\BJB110\AppData\Local\Temp\ragflowauth_playwright\integration.chat.sessions--353f9-on-real-backend-integration-chromium\error-context.md

    attachment #4: trace (application/zip) ─────────────────────────────────────────────────────────
    C:\Users\BJB110\AppData\Local\Temp\ragflowauth_playwright\integration.chat.sessions--353f9-on-real-backend-integration-chromium\trace.zip
    Usage:

        npx playwright show-trace C:\Users\BJB110\AppData\Local\Temp\ragflowauth_playwright\integration.chat.sessions--353f9-on-real-backend-integration-chromium\trace.zip

    ────────────────────────────────────────────────────────────────────────────────────────────────

  8) [chromium] › e2e\tests\integration.documents.conflict.overwrite.spec.js:22:1 › documents conflict -> approve-overwrite (real backend) @integration 

    [31mTest timeout of 180000ms exceeded.[39m

    Error: locator.setInputFiles: Test timeout of 180000ms exceeded.
    Call log:
    [2m  - waiting for getByTestId('upload-file-input')[22m


      39 |     fs.writeFileSync(filePath, `old ${filename}\n`, 'utf8');
      40 |     await page.goto(`${FRONTEND_BASE_URL}/upload`);
    > 41 |     await page.getByTestId('upload-file-input').setInputFiles(filePath);
         |     ^
      42 |     await page.getByTestId('upload-submit').click();
      43 |     await expect(page).toHaveURL(/\/documents/, { timeout: 30_000 });
      44 |
        at D:\ProjectPackage\RagflowAuth\fronted\e2e\tests\integration.documents.conflict.overwrite.spec.js:41:5

    attachment #1: screenshot (image/png) ──────────────────────────────────────────────────────────
    C:\Users\BJB110\AppData\Local\Temp\ragflowauth_playwright\integration.documents.conf-5b91f-te-real-backend-integration-chromium\test-failed-1.png
    ────────────────────────────────────────────────────────────────────────────────────────────────

    attachment #2: video (video/webm) ──────────────────────────────────────────────────────────────
    C:\Users\BJB110\AppData\Local\Temp\ragflowauth_playwright\integration.documents.conf-5b91f-te-real-backend-integration-chromium\video.webm
    ────────────────────────────────────────────────────────────────────────────────────────────────

    Error Context: C:\Users\BJB110\AppData\Local\Temp\ragflowauth_playwright\integration.documents.conf-5b91f-te-real-backend-integration-chromium\error-context.md

    attachment #4: trace (application/zip) ─────────────────────────────────────────────────────────
    C:\Users\BJB110\AppData\Local\Temp\ragflowauth_playwright\integration.documents.conf-5b91f-te-real-backend-integration-chromium\trace.zip
    Usage:

        npx playwright show-trace C:\Users\BJB110\AppData\Local\Temp\ragflowauth_playwright\integration.documents.conf-5b91f-te-real-backend-integration-chromium\trace.zip

    ────────────────────────────────────────────────────────────────────────────────────────────────

  9) [chromium] › e2e\tests\integration.flow.delete-removes-search.spec.js:13:1 › flow: delete approved document removes search hit and writes delete audit @integration @flow 

    [31mTest timeout of 300000ms exceeded.[39m

    Error: locator.selectOption: Test timeout of 300000ms exceeded.
    Call log:
    [2m  - waiting for getByTestId('upload-kb-select')[22m


       at ..\helpers\documentFlow.js:55

      53 | async function uploadDocumentViaUI(page, frontendBaseUrl, dataset, filePath) {
      54 |   await page.goto(`${frontendBaseUrl}/upload`);
    > 55 |   await page.getByTestId('upload-kb-select').selectOption(String(dataset?.name || dataset?.id || ''));
         |                                              ^
      56 |   const [uploadResp] = await Promise.all([
      57 |     page.waitForResponse((r) => {
      58 |       if (r.request().method() !== 'POST') return false;
        at uploadDocumentViaUI (D:\ProjectPackage\RagflowAuth\fronted\e2e\helpers\documentFlow.js:55:46)
        at D:\ProjectPackage\RagflowAuth\fronted\e2e\tests\integration.flow.delete-removes-search.spec.js:32:20

    attachment #1: screenshot (image/png) ──────────────────────────────────────────────────────────
    C:\Users\BJB110\AppData\Local\Temp\ragflowauth_playwright\integration.flow.delete-re-d2bf2-lete-audit-integration-flow-chromium\test-failed-1.png
    ────────────────────────────────────────────────────────────────────────────────────────────────

    attachment #2: video (video/webm) ──────────────────────────────────────────────────────────────
    C:\Users\BJB110\AppData\Local\Temp\ragflowauth_playwright\integration.flow.delete-re-d2bf2-lete-audit-integration-flow-chromium\video.webm
    ────────────────────────────────────────────────────────────────────────────────────────────────

    Error Context: C:\Users\BJB110\AppData\Local\Temp\ragflowauth_playwright\integration.flow.delete-re-d2bf2-lete-audit-integration-flow-chromium\error-context.md

    attachment #4: trace (application/zip) ─────────────────────────────────────────────────────────
    C:\Users\BJB110\AppData\Local\Temp\ragflowauth_playwright\integration.flow.delete-re-d2bf2-lete-audit-integration-flow-chromium\trace.zip
    Usage:

        npx playwright show-trace C:\Users\BJB110\AppData\Local\Temp\ragflowauth_playwright\integration.flow.delete-re-d2bf2-lete-audit-integration-flow-chromium\trace.zip

    ────────────────────────────────────────────────────────────────────────────────────────────────

  10) [chromium] › e2e\tests\integration.flow.upload-approve-search-logs.spec.js:13:1 › flow: upload -> approve -> searchable -> audit visible @integration @flow 

    [31mTest timeout of 240000ms exceeded.[39m

    Error: locator.selectOption: Test timeout of 240000ms exceeded.
    Call log:
    [2m  - waiting for getByTestId('upload-kb-select')[22m


       at ..\helpers\documentFlow.js:55

      53 | async function uploadDocumentViaUI(page, frontendBaseUrl, dataset, filePath) {
      54 |   await page.goto(`${frontendBaseUrl}/upload`);
    > 55 |   await page.getByTestId('upload-kb-select').selectOption(String(dataset?.name || dataset?.id || ''));
         |                                              ^
      56 |   const [uploadResp] = await Promise.all([
      57 |     page.waitForResponse((r) => {
      58 |       if (r.request().method() !== 'POST') return false;
        at uploadDocumentViaUI (D:\ProjectPackage\RagflowAuth\fronted\e2e\helpers\documentFlow.js:55:46)
        at D:\ProjectPackage\RagflowAuth\fronted\e2e\tests\integration.flow.upload-approve-search-logs.spec.js:32:20

    attachment #1: screenshot (image/png) ──────────────────────────────────────────────────────────
    C:\Users\BJB110\AppData\Local\Temp\ragflowauth_playwright\integration.flow.upload-ap-c2178-it-visible-integration-flow-chromium\test-failed-1.png
    ────────────────────────────────────────────────────────────────────────────────────────────────

    attachment #2: video (video/webm) ──────────────────────────────────────────────────────────────
    C:\Users\BJB110\AppData\Local\Temp\ragflowauth_playwright\integration.flow.upload-ap-c2178-it-visible-integration-flow-chromium\video.webm
    ────────────────────────────────────────────────────────────────────────────────────────────────

    Error Context: C:\Users\BJB110\AppData\Local\Temp\ragflowauth_playwright\integration.flow.upload-ap-c2178-it-visible-integration-flow-chromium\error-context.md

    attachment #4: trace (application/zip) ─────────────────────────────────────────────────────────
    C:\Users\BJB110\AppData\Local\Temp\ragflowauth_playwright\integration.flow.upload-ap-c2178-it-visible-integration-flow-chromium\trace.zip
    Usage:

        npx playwright show-trace C:\Users\BJB110\AppData\Local\Temp\ragflowauth_playwright\integration.flow.upload-ap-c2178-it-visible-integration-flow-chromium\trace.zip

    ────────────────────────────────────────────────────────────────────────────────────────────────

  11) [chromium] › e2e\tests\integration.flow.upload-reject-search-logs.spec.js:13:1 › flow: upload -> reject -> not searchable -> upload audit visible @integration @flow 

    [31mTest timeout of 240000ms exceeded.[39m

    Error: locator.selectOption: Test timeout of 240000ms exceeded.
    Call log:
    [2m  - waiting for getByTestId('upload-kb-select')[22m


       at ..\helpers\documentFlow.js:55

      53 | async function uploadDocumentViaUI(page, frontendBaseUrl, dataset, filePath) {
      54 |   await page.goto(`${frontendBaseUrl}/upload`);
    > 55 |   await page.getByTestId('upload-kb-select').selectOption(String(dataset?.name || dataset?.id || ''));
         |                                              ^
      56 |   const [uploadResp] = await Promise.all([
      57 |     page.waitForResponse((r) => {
      58 |       if (r.request().method() !== 'POST') return false;
        at uploadDocumentViaUI (D:\ProjectPackage\RagflowAuth\fronted\e2e\helpers\documentFlow.js:55:46)
        at D:\ProjectPackage\RagflowAuth\fronted\e2e\tests\integration.flow.upload-reject-search-logs.spec.js:32:20

    attachment #1: screenshot (image/png) ──────────────────────────────────────────────────────────
    C:\Users\BJB110\AppData\Local\Temp\ragflowauth_playwright\integration.flow.upload-re-7375c-it-visible-integration-flow-chromium\test-failed-1.png
    ────────────────────────────────────────────────────────────────────────────────────────────────

    attachment #2: video (video/webm) ──────────────────────────────────────────────────────────────
    C:\Users\BJB110\AppData\Local\Temp\ragflowauth_playwright\integration.flow.upload-re-7375c-it-visible-integration-flow-chromium\video.webm
    ────────────────────────────────────────────────────────────────────────────────────────────────

    Error Context: C:\Users\BJB110\AppData\Local\Temp\ragflowauth_playwright\integration.flow.upload-re-7375c-it-visible-integration-flow-chromium\error-context.md

    attachment #4: trace (application/zip) ─────────────────────────────────────────────────────────
    C:\Users\BJB110\AppData\Local\Temp\ragflowauth_playwright\integration.flow.upload-re-7375c-it-visible-integration-flow-chromium\trace.zip
    Usage:

        npx playwright show-trace C:\Users\BJB110\AppData\Local\Temp\ragflowauth_playwright\integration.flow.upload-re-7375c-it-visible-integration-flow-chromium\trace.zip

    ────────────────────────────────────────────────────────────────────────────────────────────────

  12) [chromium] › e2e\tests\integration.org-directory.audit.spec.js:5:1 › org directory create -> audit visible (real backend) @integration 

    TimeoutError: page.waitForURL: Timeout 30000ms exceeded.
    =========================== logs ===========================
    waiting for navigation until "load"
    ============================================================

       at ..\helpers\integration.js:53

      51 |     throw new Error(`UI login failed: ${loginResp.status()}`);
      52 |   }
    > 53 |   await page.waitForURL(/(\/|\/chat)$/, { timeout: 30_000 });
         |              ^
      54 | }
      55 |
      56 | module.exports = {
        at uiLogin (D:\ProjectPackage\RagflowAuth\fronted\e2e\helpers\integration.js:53:14)
        at D:\ProjectPackage\RagflowAuth\fronted\e2e\tests\integration.org-directory.audit.spec.js:16:3

    attachment #1: screenshot (image/png) ──────────────────────────────────────────────────────────
    C:\Users\BJB110\AppData\Local\Temp\ragflowauth_playwright\integration.org-directory.-64b48-le-real-backend-integration-chromium\test-failed-1.png
    ────────────────────────────────────────────────────────────────────────────────────────────────

    attachment #2: video (video/webm) ──────────────────────────────────────────────────────────────
    C:\Users\BJB110\AppData\Local\Temp\ragflowauth_playwright\integration.org-directory.-64b48-le-real-backend-integration-chromium\video.webm
    ────────────────────────────────────────────────────────────────────────────────────────────────

    Error Context: C:\Users\BJB110\AppData\Local\Temp\ragflowauth_playwright\integration.org-directory.-64b48-le-real-backend-integration-chromium\error-context.md

    attachment #4: trace (application/zip) ─────────────────────────────────────────────────────────
    C:\Users\BJB110\AppData\Local\Temp\ragflowauth_playwright\integration.org-directory.-64b48-le-real-backend-integration-chromium\trace.zip
    Usage:

        npx playwright show-trace C:\Users\BJB110\AppData\Local\Temp\ragflowauth_playwright\integration.org-directory.-64b48-le-real-backend-integration-chromium\trace.zip

    ────────────────────────────────────────────────────────────────────────────────────────────────

  13) [chromium] › e2e\tests\integration.permission-groups.crud.spec.js:5:1 › permission groups create -> edit -> delete (real backend) @integration 

    [31mTest timeout of 120000ms exceeded.[39m

    Error: locator.click: Test timeout of 120000ms exceeded.
    Call log:
    [2m  - waiting for getByTestId('pg-create-open')[22m


      18 |     await page.goto(`${FRONTEND_BASE_URL}/permission-groups`);
      19 |
    > 20 |     await page.getByTestId('pg-create-open').click();
         |                                              ^
      21 |     await page.getByTestId('pg-form-group-name').fill(groupName);
      22 |     await page.getByTestId('pg-form-description').fill('e2e desc');
      23 |     await page.getByTestId('pg-form-can-upload').check();
        at D:\ProjectPackage\RagflowAuth\fronted\e2e\tests\integration.permission-groups.crud.spec.js:20:46

    attachment #1: screenshot (image/png) ──────────────────────────────────────────────────────────
    C:\Users\BJB110\AppData\Local\Temp\ragflowauth_playwright\integration.permission-gro-f6e01-te-real-backend-integration-chromium\test-failed-1.png
    ────────────────────────────────────────────────────────────────────────────────────────────────

    attachment #2: video (video/webm) ──────────────────────────────────────────────────────────────
    C:\Users\BJB110\AppData\Local\Temp\ragflowauth_playwright\integration.permission-gro-f6e01-te-real-backend-integration-chromium\video.webm
    ────────────────────────────────────────────────────────────────────────────────────────────────

    Error Context: C:\Users\BJB110\AppData\Local\Temp\ragflowauth_playwright\integration.permission-gro-f6e01-te-real-backend-integration-chromium\error-context.md

    attachment #4: trace (application/zip) ─────────────────────────────────────────────────────────
    C:\Users\BJB110\AppData\Local\Temp\ragflowauth_playwright\integration.permission-gro-f6e01-te-real-backend-integration-chromium\trace.zip
    Usage:

        npx playwright show-trace C:\Users\BJB110\AppData\Local\Temp\ragflowauth_playwright\integration.permission-gro-f6e01-te-real-backend-integration-chromium\trace.zip

    ────────────────────────────────────────────────────────────────────────────────────────────────

  14) [chromium] › e2e\tests\integration.permission-groups.resources.spec.js:5:1 › permission groups resources endpoints (real backend) @integration 

    Error: [2mexpect([22m[31mreceived[39m[2m).[22mtoBe[2m([22m[32mexpected[39m[2m) // Object.is equality[22m

    Expected: [32m200[39m
    Received: [31m401[39m

      14 |
      15 |     const kbResp = await api.get('/api/permission-groups/resources/knowledge-bases', { headers });
    > 16 |     expect(kbResp.status()).toBe(200);
         |                             ^
      17 |     const kbJson = await kbResp.json();
      18 |     expect(typeof kbJson).toBe('object');
      19 |     expect(typeof kbJson.ok).toBe('boolean');
        at D:\ProjectPackage\RagflowAuth\fronted\e2e\tests\integration.permission-groups.resources.spec.js:16:29

    attachment #1: trace (application/zip) ─────────────────────────────────────────────────────────
    C:\Users\BJB110\AppData\Local\Temp\ragflowauth_playwright\integration.permission-gro-38555-ts-real-backend-integration-chromium\trace.zip
    Usage:

        npx playwright show-trace C:\Users\BJB110\AppData\Local\Temp\ragflowauth_playwright\integration.permission-gro-38555-ts-real-backend-integration-chromium\trace.zip

    ────────────────────────────────────────────────────────────────────────────────────────────────

  15) [chromium] › e2e\tests\integration.upload.reject.spec.js:15:1 › upload -> reject -> appears in records @integration 

    [31mTest timeout of 120000ms exceeded.[39m

    Error: locator.setInputFiles: Test timeout of 120000ms exceeded.
    Call log:
    [2m  - waiting for getByTestId('upload-file-input')[22m


      57 |     await page.goto(`${FRONTEND_BASE_URL}/upload`);
      58 |     // The file input is hidden; Playwright can still set files on it.
    > 59 |     await page.getByTestId('upload-file-input').setInputFiles(filePath);
         |     ^
      60 |     await page.getByTestId('upload-submit').click();
      61 |
      62 |     // Upload page auto-navigates to /documents.
        at D:\ProjectPackage\RagflowAuth\fronted\e2e\tests\integration.upload.reject.spec.js:59:5

    attachment #1: screenshot (image/png) ──────────────────────────────────────────────────────────
    C:\Users\BJB110\AppData\Local\Temp\ragflowauth_playwright\integration.upload.reject--8545b-ears-in-records-integration-chromium\test-failed-1.png
    ────────────────────────────────────────────────────────────────────────────────────────────────

    attachment #2: video (video/webm) ──────────────────────────────────────────────────────────────
    C:\Users\BJB110\AppData\Local\Temp\ragflowauth_playwright\integration.upload.reject--8545b-ears-in-records-integration-chromium\video.webm
    ────────────────────────────────────────────────────────────────────────────────────────────────

    Error Context: C:\Users\BJB110\AppData\Local\Temp\ragflowauth_playwright\integration.upload.reject--8545b-ears-in-records-integration-chromium\error-context.md

    attachment #4: trace (application/zip) ─────────────────────────────────────────────────────────
    C:\Users\BJB110\AppData\Local\Temp\ragflowauth_playwright\integration.upload.reject--8545b-ears-in-records-integration-chromium\trace.zip
    Usage:

        npx playwright show-trace C:\Users\BJB110\AppData\Local\Temp\ragflowauth_playwright\integration.upload.reject--8545b-ears-in-records-integration-chromium\trace.zip

    ────────────────────────────────────────────────────────────────────────────────────────────────

  16) [chromium] › e2e\tests\kbs.config.p0.spec.js:5:1 › knowledge config p0: list/detail/save/create-copy/delete-empty-only @regression @kbs 

    Error: [2mexpect([22m[31mlocator[39m[2m).[22mtoBeVisible[2m([22m[2m)[22m failed

    Locator: getByRole('button', { name: /知识库配置/ })
    Expected: visible
    Timeout: 10000ms
    Error: element(s) not found

    Call log:
    [2m  - Expect "toBeVisible" with timeout 10000ms[22m
    [2m  - waiting for getByRole('button', { name: /知识库配置/ })[22m


      79 |
      80 |   await page.goto('/kbs');
    > 81 |   await expect(page.getByRole('button', { name: /知识库配置/ })).toBeVisible();
         |                                                             ^
      82 |   await expect(page.getByText('ID: kb_nonempty')).toBeVisible();
      83 |   await expect(page.getByText('ID: kb_empty')).toBeVisible();
      84 |
        at D:\ProjectPackage\RagflowAuth\fronted\e2e\tests\kbs.config.p0.spec.js:81:61

    attachment #1: screenshot (image/png) ──────────────────────────────────────────────────────────
    C:\Users\BJB110\AppData\Local\Temp\ragflowauth_playwright\kbs.config.p0-knowledge-co-699f6-e-empty-only-regression-kbs-chromium\test-failed-1.png
    ────────────────────────────────────────────────────────────────────────────────────────────────

    attachment #2: trace (application/zip) ─────────────────────────────────────────────────────────
    C:\Users\BJB110\AppData\Local\Temp\ragflowauth_playwright\kbs.config.p0-knowledge-co-699f6-e-empty-only-regression-kbs-chromium\trace.zip
    Usage:

        npx playwright show-trace C:\Users\BJB110\AppData\Local\Temp\ragflowauth_playwright\kbs.config.p0-knowledge-co-699f6-e-empty-only-regression-kbs-chromium\trace.zip

    ────────────────────────────────────────────────────────────────────────────────────────────────

  Slow test file: [chromium] › e2e\tests\integration.flow.delete-removes-search.spec.js (5.2m)
  Consider running tests from slow files in parallel. See: https://playwright.dev/docs/test-parallel
  16 failed
    [chromium] › e2e\tests\admin.permission-groups.crud.spec.js:6:1 › admin can CRUD permission groups via UI @regression @admin 
    [chromium] › e2e\tests\admin.permission-groups.resources.error.spec.js:5:1 › permission groups handles resources API failures gracefully @regression @admin 
    [chromium] › e2e\tests\admin.permission-groups.resources.spec.js:6:1 › permission groups can select knowledge bases and chats @regression @admin 
    [chromium] › e2e\tests\admin.users.create.spec.js:6:1 › admin can create user via UI @regression @admin 
    [chromium] › e2e\tests\agents.search.spec.js:5:1 › agents search sends expected request and renders results (mock) @regression @agents 
    [chromium] › e2e\tests\audit.logs.action-completeness.spec.js:5:1 › audit logs page renders key actions @regression @audit 
    [chromium] › e2e\tests\integration.chat.sessions.spec.js:5:1 › chat can create and delete session (real backend) @integration 
    [chromium] › e2e\tests\integration.documents.conflict.overwrite.spec.js:22:1 › documents conflict -> approve-overwrite (real backend) @integration 
    [chromium] › e2e\tests\integration.flow.delete-removes-search.spec.js:13:1 › flow: delete approved document removes search hit and writes delete audit @integration @flow 
    [chromium] › e2e\tests\integration.flow.upload-approve-search-logs.spec.js:13:1 › flow: upload -> approve -> searchable -> audit visible @integration @flow 
    [chromium] › e2e\tests\integration.flow.upload-reject-search-logs.spec.js:13:1 › flow: upload -> reject -> not searchable -> upload audit visible @integration @flow 
    [chromium] › e2e\tests\integration.org-directory.audit.spec.js:5:1 › org directory create -> audit visible (real backend) @integration 
    [chromium] › e2e\tests\integration.permission-groups.crud.spec.js:5:1 › permission groups create -> edit -> delete (real backend) @integration 
    [chromium] › e2e\tests\integration.permission-groups.resources.spec.js:5:1 › permission groups resources endpoints (real backend) @integration 
    [chromium] › e2e\tests\integration.upload.reject.spec.js:15:1 › upload -> reject -> appears in records @integration 
    [chromium] › e2e\tests\kbs.config.p0.spec.js:5:1 › knowledge config p0: list/detail/save/create-copy/delete-empty-only @regression @kbs 
  4 skipped
  77 passed (5.5m)

To open last HTML report run:
[36m[39m
[36m  npx playwright show-report[39m
[36m[39m
```

