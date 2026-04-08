// @ts-check
const fs = require('node:fs');
const path = require('node:path');
const { test, expect } = require('@playwright/test');
const { adminStorageStatePath, reviewerTest, subAdminTest } = require('../helpers/auth');

const SCREENSHOT_DIR = path.resolve(__dirname, '..', '..', '..', 'output', 'playwright');

function ensureScreenshotDir() {
  fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });
}

async function saveEvidenceScreenshot(page, fileName) {
  ensureScreenshotDir();
  await page.screenshot({ path: path.join(SCREENSHOT_DIR, fileName), fullPage: true });
}

async function stubInbox(page) {
  await page.route('**/api/inbox**', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ items: [], count: 0, unread_count: 0 }),
    });
  });
}

async function stubDocumentAuditData(page) {
  await stubInbox(page);
  await page.route('**/api/users**', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) });
  });
  await page.route('**/api/knowledge/documents**', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ documents: [], count: 0 }),
    });
  });
  await page.route('**/api/knowledge/deletions**', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ deletions: [], count: 0 }),
    });
  });
  await page.route('**/api/ragflow/downloads**', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ downloads: [] }),
    });
  });
}

async function stubDataSecurityData(page) {
  await stubInbox(page);
  await page.route('**/api/admin/data-security/settings', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        enabled: false,
        interval_minutes: 60,
        target_mode: 'local',
        target_local_dir: 'D:\\backup\\ragflowauth',
        target_ip: '',
        target_share_name: '',
        target_subdir: '',
        ragflow_compose_path: '/app/ragflow_compose/docker-compose.yml',
        ragflow_stop_services: false,
        full_backup_include_images: false,
        auth_db_path: 'data/auth.db',
        last_run_at_ms: null,
        local_backup_target_path: '/app/data/backups',
        local_backup_pack_count: 0,
        windows_backup_target_path: 'D:\\backup\\ragflowauth',
        windows_backup_pack_count: 0,
      }),
    });
  });
  await page.route('**/api/admin/data-security/backup/jobs**', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ jobs: [] }),
    });
  });
  await page.route('**/api/admin/data-security/restore-drills**', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ items: [] }),
    });
  });
}

reviewerTest('reviewer menu metadata matches document-history route access @regression @rbac @refactor-access-control', async ({ page }) => {
  await stubDocumentAuditData(page);

  await page.goto('/chat');
  await expect(page.getByTestId('nav-document-history')).toBeVisible();

  await page.goto('/document-history');
  await expect(page).toHaveURL(/\/document-history$/);
  await expect(page.getByTestId('audit-page')).toBeVisible();
  await saveEvidenceScreenshot(page, 'rbac-reviewer-document-history.png');
});

test.describe('forced viewer without document-history capability', () => {
  test.use({ storageState: adminStorageStatePath });

  test('viewer menu metadata hides document-history and direct route stays blocked @regression @rbac @refactor-access-control', async ({ page }) => {
    await stubInbox(page);
    await page.route('**/api/auth/me', async (route) => {
      if (route.request().method() !== 'GET') return route.fallback();
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          user_id: 'viewer-denied',
          username: 'viewer-denied',
          full_name: 'Viewer Denied',
          role: 'viewer',
          status: 'active',
          permission_groups: [],
          permissions: {
            can_upload: false,
            can_review: false,
            can_download: false,
            can_copy: false,
            can_delete: false,
            can_manage_kb_directory: false,
            can_view_kb_config: false,
            can_view_tools: false,
            accessible_tools: [],
          },
          capabilities: {
            kb_documents: {
              upload: { scope: 'none' },
              review: { scope: 'none' },
              view: { scope: 'none' },
              download: { scope: 'none' },
              copy: { scope: 'none' },
              delete: { scope: 'none' },
            },
            kb_directory: {
              manage: { scope: 'none' },
            },
            kbs_config: {
              view: { scope: 'none' },
            },
            tools: {
              view: { scope: 'none' },
            },
          },
          accessible_kb_ids: [],
        }),
      });
    });
    await page.route('**/api/auth/refresh', async (route) => {
      if (route.request().method() !== 'POST') return route.fallback();
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ access_token: 'denied_viewer_token', token_type: 'bearer' }),
      });
    });

    await page.goto('/change-password');
    await expect(page.getByTestId('change-password-old')).toBeVisible();
    await expect(page.getByTestId('nav-document-history')).toHaveCount(0);

    await page.goto('/document-history');
    await expect(page).toHaveURL(/\/unauthorized$/);
    await expect(page.getByTestId('unauthorized-title')).toBeVisible();
    await saveEvidenceScreenshot(page, 'rbac-viewer-document-history-blocked.png');
  });
});

subAdminTest('sub-admin route access can differ from nav visibility through shared route metadata @regression @rbac @refactor-access-control', async ({ page }) => {
  await stubDataSecurityData(page);

  await page.goto('/chat');
  await expect(page.getByTestId('nav-data-security')).toHaveCount(0);

  await page.goto('/data-security');
  await expect(page).toHaveURL(/\/data-security$/);
  await expect(page.getByTestId('data-security-page')).toBeVisible();
  await saveEvidenceScreenshot(page, 'rbac-sub-admin-data-security-route.png');
});
