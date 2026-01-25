// @ts-check
const { expect } = require('@playwright/test');
const { adminTest } = require('../helpers/auth');

adminTest('documents supports select-all and batch download (mock) @regression @documents', async ({ page }) => {
  const docs = [
    { doc_id: 'd1', filename: 'a.txt', status: 'pending', uploaded_at_ms: Date.now(), kb_id: 'kb1', uploaded_by: 'u1' },
    { doc_id: 'd2', filename: 'b.txt', status: 'pending', uploaded_at_ms: Date.now(), kb_id: 'kb1', uploaded_by: 'u1' },
  ];

  let capturedBody = null;

  await page.route('**/api/datasets', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ datasets: [{ id: 'kb1', name: 'kb1' }] }) });
  });

  await page.route('**/api/knowledge/documents**', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    const url = new URL(route.request().url());
    if (url.searchParams.get('status') !== 'pending') return route.fallback();
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ documents: docs, count: docs.length }) });
  });

  await page.route('**/api/knowledge/documents/batch/download', async (route) => {
    if (route.request().method() !== 'POST') return route.fallback();
    capturedBody = route.request().postDataJSON();
    await route.fulfill({
      status: 200,
      headers: {
        'Content-Type': 'application/zip',
        'Content-Disposition': "attachment; filename*=UTF-8''e2e.zip",
      },
      body: 'ZIP',
    });
  });

  await page.goto('/documents');
  await expect(page.locator('tr', { hasText: 'a.txt' })).toBeVisible();

  await page.getByRole('button', { name: '全选' }).click();
  await page.getByRole('button', { name: /下载选中/ }).click();

  expect(capturedBody).toBeTruthy();
  expect(Array.isArray(capturedBody.doc_ids)).toBe(true);
  expect(capturedBody.doc_ids).toEqual(['d1', 'd2']);
});

