// @ts-check
const { expect } = require('@playwright/test');
const { adminTest, viewerTest } = require('../helpers/auth');

viewerTest('search configs route is admin-only @regression @search-configs @rbac', async ({ page }) => {
  await page.goto('/search-configs');
  await expect(page).toHaveURL(/\/unauthorized$/);
  await expect(page.getByTestId('unauthorized-title')).toBeVisible();
});

adminTest('search configs save api failure shows detail error @regression @search-configs', async ({ page }) => {
  const configs = [{ id: 'sc_1', name: 'Config One', config: { top_k: 6 } }];

  await page.route('**/api/search/configs', async (route) => {
    const method = route.request().method();
    if (method === 'GET') {
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ configs }) });
    }
    return route.fallback();
  });

  await page.route('**/api/search/configs/*', async (route) => {
    const method = route.request().method();
    if (method === 'GET') {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ config: configs[0] }),
      });
    }
    if (method === 'PUT') {
      return route.fulfill({ status: 500, contentType: 'application/json', body: JSON.stringify({ detail: 'save_failed_test' }) });
    }
    return route.fallback();
  });

  await page.goto('/search-configs');

  await expect(page.getByText('ID: sc_1')).toBeVisible();
  await page.getByPlaceholder('Config name').fill('Config One Updated');
  await page.getByRole('button', { name: 'Save' }).click();

  await expect(page.getByText('save_failed_test')).toBeVisible();
});
