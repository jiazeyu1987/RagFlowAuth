// @ts-check
const { expect } = require('@playwright/test');
const { adminTest } = require('../helpers/auth');

adminTest('admin can approve a pending document (mocked local docs) @regression @documents', async ({ page }) => {
  const docs = [
    {
      doc_id: 'local1',
      filename: 'e2e_pending.txt',
      file_size: 12,
      mime_type: 'text/plain; charset=utf-8',
      uploaded_by: 'u1',
      uploaded_by_name: 'admin',
      status: 'pending',
      uploaded_at_ms: Date.now(),
      reviewed_by: null,
      reviewed_by_name: null,
      reviewed_at_ms: null,
      review_notes: null,
      ragflow_doc_id: null,
      kb_id: '展厅',
    },
  ];

  await page.route('**/api/datasets', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        datasets: [{ id: 'ds1', name: '展厅' }],
        count: 1,
      }),
    });
  });

  await page.route('**/api/knowledge/documents/local1/conflict', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ conflict: false }),
    });
  });

  await page.route('**/api/knowledge/documents**', async (route) => {
    const method = route.request().method();
    if (method !== 'GET') return route.fallback();

    const url = new URL(route.request().url());
    const status = url.searchParams.get('status');
    if (status === 'pending') {
      const pending = docs.filter((d) => d.status === 'pending');
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ documents: pending, count: pending.length }),
      });
    }

    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ documents: docs, count: docs.length }),
    });
  });

  const approveReqPromise = page.waitForRequest('**/api/knowledge/documents/local1/approve');
  await page.route('**/api/knowledge/documents/local1/approve', async (route) => {
    if (route.request().method() !== 'POST') return route.fallback();
    const body = route.request().postDataJSON();
    expect(body).toHaveProperty('review_notes');
    docs[0] = { ...docs[0], status: 'approved', reviewed_at_ms: Date.now(), reviewed_by: 'admin' };
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ok: true }) });
  });

  await page.goto('/documents');

  // Wait for table to render.
  await expect(page.getByRole('columnheader', { name: '文档名称' })).toBeVisible();

  const row = page.locator('tr', { hasText: 'e2e_pending.txt' });
  await expect(row).toBeVisible();
  page.once('dialog', async (dialog) => dialog.accept());
  await row.getByRole('button', { name: '通过' }).click();

  await approveReqPromise;
  await expect(page.locator('tr', { hasText: 'e2e_pending.txt' })).toHaveCount(0);
});
