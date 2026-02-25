// @ts-check
const { expect } = require('@playwright/test');
const { adminTest } = require('../helpers/auth');

adminTest('browser supports selecting docs and batch download (mock) @regression @browser', async ({ page }) => {
  const dataset = { id: 'ds1', name: 'kb-one' };
  const docs = [
    { id: 'doc_a', name: 'a.txt', status: 'ready' },
    { id: 'doc_b', name: 'b.txt', status: 'ready' },
  ];

  let capturedBatchBody = null;

  await page.route('**/api/datasets', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ datasets: [dataset], count: 1 }),
    });
  });

  await page.route('**/api/ragflow/documents?*', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ documents: docs, count: docs.length }),
    });
  });

  await page.route('**/api/documents/ragflow/batch/download', async (route) => {
    if (route.request().method() !== 'POST') return route.fallback();
    capturedBatchBody = route.request().postDataJSON();
    return route.fulfill({
      status: 200,
      headers: {
        'Content-Type': 'application/zip',
        'Content-Disposition': "attachment; filename*=UTF-8''e2e.zip",
      },
      body: 'ZIP',
    });
  });

  await page.goto('/browser');
  await page.getByTestId('browser-dataset-toggle-ds1').click();
  await expect(page.getByTestId('browser-doc-row-ds1-doc_a')).toBeVisible();

  await page.getByTestId('browser-doc-select-ds1-doc_a').check();
  await expect(page.getByTestId('browser-batch-download')).toBeVisible();
  await page.getByTestId('browser-batch-download').click();

  expect(capturedBatchBody).toBeTruthy();
  expect(Array.isArray(capturedBatchBody.documents)).toBe(true);
  expect(capturedBatchBody.documents).toEqual([
    { doc_id: 'doc_a', dataset: 'kb-one', name: 'a.txt' },
  ]);

  await expect(page.getByTestId('browser-batch-download')).toHaveCount(0);
});
