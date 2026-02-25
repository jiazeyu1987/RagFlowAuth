// @ts-check
const { test, expect } = require('@playwright/test');
const { adminStorageStatePath } = require('../helpers/auth');

test.use({ storageState: adminStorageStatePath });

test('viewer without download permission can view but not download in browser @regression @browser @rbac', async ({ page }) => {
  await page.route('**/api/auth/me', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        user_id: 'u_viewer_no_dl',
        username: 'viewer_no_dl',
        role: 'viewer',
        permissions: { can_upload: false, can_review: false, can_download: false, can_delete: false },
      }),
    });
  });
  await page.route('**/api/me/kbs', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ kb_ids: ['ds1'] }) });
  });
  await page.route('**/api/auth/refresh', async (route) => {
    if (route.request().method() !== 'POST') return route.fallback();
    return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ access_token: 'e2e_access_token', token_type: 'bearer' }) });
  });

  await page.route('**/api/datasets', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ datasets: [{ id: 'ds1', name: '展厅' }] }),
    });
  });
  await page.route('**/api/ragflow/documents?*', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ documents: [{ id: 'doc1', name: 'a.txt', created_at: '2025-01-01' }] }),
    });
  });
  await page.route('**/api/preview/documents/ragflow/doc1/preview?*', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ type: 'text', filename: 'a.txt', content: 'hello' }) });
  });

  await page.goto('/browser');
  await page.getByTestId('browser-dataset-toggle-ds1').click();

  await expect(page.getByTestId('browser-doc-view-ds1-doc1')).toBeVisible();
  await expect(page.getByTestId('browser-doc-download-ds1-doc1')).toHaveCount(0);

  await page.getByTestId('browser-doc-view-ds1-doc1').click();
  const modal = page.getByTestId('document-preview-modal');
  await expect(modal).toBeVisible();
  await expect(modal.getByText('hello')).toBeVisible();
});

