// @ts-check
const { expect } = require('@playwright/test');
const { adminTest } = require('../helpers/auth');

adminTest('document list shows only current company records (mock) @regression @documents', async ({ page }) => {
  const companyDocs = [
    {
      doc_id: 'company-a-doc-1',
      filename: 'company-a-only.txt',
      file_size: 12,
      mime_type: 'text/plain',
      uploaded_by: 'tenant_user_a',
      uploaded_by_name: 'tenant-user-a',
      status: 'pending',
      uploaded_at_ms: Date.now(),
      reviewed_by: null,
      reviewed_at_ms: null,
      review_notes: null,
      ragflow_doc_id: null,
      kb_id: 'kb-company-a',
    },
  ];

  await page.route('**/api/datasets', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ datasets: [{ id: 'kb-company-a', name: 'kb-company-a' }], count: 1 }),
    });
  });

  await page.route('**/api/knowledge/documents**', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    const url = new URL(route.request().url());
    if (url.searchParams.get('status') !== 'pending') return route.fallback();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ documents: companyDocs, count: companyDocs.length }),
    });
  });

  await page.goto('/documents');
  await expect(page.getByTestId('docs-approve-company-a-doc-1')).toBeVisible();
  await expect(page.getByTestId('docs-approve-company-b-doc-1')).toHaveCount(0);
});
