// @ts-check
const { expect } = require('@playwright/test');
const { adminTest } = require('../helpers/auth');

adminTest('browser dataset keyword filter and recent-5 history work @regression @browser', async ({ page }) => {
  await page.route('**/api/datasets', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        datasets: [
          { id: 'd1', name: '展厅' },
          { id: 'd2', name: '知识库调研' },
          { id: 'd3', name: 'intlife' },
        ],
      }),
    });
  });
  await page.route('**/api/ragflow/documents?*', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ documents: [] }) });
  });

  await page.goto('/browser');
  await expect(page.getByTestId('browser-dataset-d1')).toBeVisible();
  await expect(page.getByTestId('browser-dataset-d2')).toBeVisible();
  await expect(page.getByTestId('browser-dataset-d3')).toBeVisible();

  const input = page.getByTestId('browser-dataset-filter');
  await input.fill('调研');
  await input.press('Enter');
  await expect(page.getByTestId('browser-dataset-d2')).toBeVisible();
  await expect(page.getByTestId('browser-dataset-d1')).toHaveCount(0);

  await page.getByTestId('browser-dataset-filter-clear').click();
  await expect(page.getByTestId('browser-dataset-d1')).toBeVisible();
  await expect(page.getByTestId('browser-dataset-d2')).toBeVisible();
  await expect(page.getByTestId('browser-dataset-d3')).toBeVisible();

  for (const kw of ['k1', 'k2', 'k3', 'k4', 'k5', 'k6']) {
    await input.fill(kw);
    await input.press('Enter');
  }

  await expect(page.getByText('k6').first()).toBeVisible();
  await expect(page.getByText('k5').first()).toBeVisible();
  await expect(page.getByText('k2').first()).toBeVisible();
  // oldest one should be evicted, keeping only latest 5.
  await expect(page.getByText('k1').first()).toHaveCount(0);
});

