// @ts-check
const { expect } = require('@playwright/test');
const { adminTest } = require('../helpers/auth');

adminTest('audit logs page renders key actions @regression @audit', async ({ page }) => {
  await page.route('**/api/org/companies', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) });
  });
  await page.route('**/api/org/departments', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) });
  });

  await page.route('**/api/audit/events**', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    const now = Date.now();
    const items = [
      { id: 1, action: 'auth_login', actor: 'u1', username: 'admin', target_type: 'auth', target_id: '', detail: 'ok', created_at_ms: now - 9000 },
      { id: 2, action: 'auth_logout', actor: 'u1', username: 'admin', target_type: 'auth', target_id: '', detail: 'ok', created_at_ms: now - 8000 },
      { id: 3, action: 'document_preview', actor: 'u1', username: 'admin', target_type: 'document', target_id: 'd1', detail: 'ok', created_at_ms: now - 7000 },
      { id: 4, action: 'document_upload', actor: 'u1', username: 'admin', target_type: 'document', target_id: 'd1', detail: 'ok', created_at_ms: now - 6000 },
      { id: 5, action: 'document_download', actor: 'u1', username: 'admin', target_type: 'document', target_id: 'd1', detail: 'ok', created_at_ms: now - 5000 },
      { id: 6, action: 'document_delete', actor: 'u1', username: 'admin', target_type: 'document', target_id: 'd1', detail: 'ok', created_at_ms: now - 4000 },
      { id: 7, action: 'document_approve', actor: 'u1', username: 'admin', target_type: 'document', target_id: 'd2', detail: 'ok', created_at_ms: now - 3000 },
      { id: 8, action: 'document_reject', actor: 'u1', username: 'admin', target_type: 'document', target_id: 'd3', detail: 'ok', created_at_ms: now - 2000 },
      { id: 9, action: 'password_change', actor: 'u1', username: 'admin', target_type: 'auth', target_id: 'u1', detail: 'ok', created_at_ms: now - 1000 },
    ];
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ total: items.length, items }),
    });
  });

  await page.goto('/logs');
  await expect(page.getByTestId('audit-total')).toHaveText('9');
  const table = page.getByTestId('audit-table');
  for (const action of [
    'auth_login',
    'auth_logout',
    'document_preview',
    'document_upload',
    'document_download',
    'document_delete',
    'document_approve',
    'document_reject',
    'password_change',
  ]) {
    await expect(table).toContainText(action);
  }
});
