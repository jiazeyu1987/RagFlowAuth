// @ts-check
const { expect } = require('@playwright/test');
const { adminTest } = require('../helpers/auth');
const { mockJson } = require('../helpers/mock');

adminTest('audit records filter by status and switch tabs (mock) @regression @audit', async ({ page }) => {
  await mockJson(page, '**/api/users**', [
    { user_id: 'u1', username: 'alice' },
    { user_id: 'u2', username: 'bob' },
  ]);

  await mockJson(page, '**/api/knowledge/documents**', {
    documents: [
      { doc_id: 'd1', kb_id: 'kb1', filename: 'a.txt', uploaded_by: 'u1', reviewed_by: 'u2', status: 'approved', uploaded_at_ms: 1, reviewed_at_ms: 2 },
      { doc_id: 'd2', kb_id: 'kb1', filename: 'b.txt', uploaded_by: 'u1', reviewed_by: null, status: 'rejected', uploaded_at_ms: 3, reviewed_at_ms: 4 },
    ],
  });

  await mockJson(page, '**/api/knowledge/deletions**', {
    deletions: [{ id: 'del1', kb_id: 'kb1', filename: 'x.txt', original_uploader: 'u1', original_reviewer: 'u2', deleted_by: 'u2', deleted_at_ms: 5 }],
  });

  await mockJson(page, '**/api/ragflow/downloads**', {
    downloads: [{ id: 'down1', kb_id: 'kb1', filename: 'y.txt', downloaded_by: 'u1', downloaded_at_ms: 6, is_batch: false }],
  });

  await page.goto('/documents?tab=records');
  await page.getByTestId('documents-tab-records').click();

  await expect(page.getByTestId('audit-tab-documents')).toBeVisible();
  await page.getByTestId('audit-filter-status').selectOption('rejected');

  await expect(page.getByTestId('audit-doc-row-d2')).toBeVisible();
  await expect(page.getByTestId('audit-doc-row-d1')).toHaveCount(0);

  await page.getByTestId('audit-tab-deletions').click();
  await expect(page.getByTestId('audit-deletion-row-del1')).toBeVisible();

  await page.getByTestId('audit-tab-downloads').click();
  await expect(page.getByTestId('audit-download-row-down1')).toBeVisible();
});

