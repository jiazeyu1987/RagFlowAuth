// @ts-check
const { expect } = require('@playwright/test');
const { adminTest } = require('../helpers/auth');

adminTest('search configs: list loading failure branch @regression @search-configs', async ({ page }) => {
  await page.route('**/api/search/configs', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    return route.fulfill({
      status: 500,
      contentType: 'application/json',
      body: JSON.stringify({ detail: 'list_failed_test' }),
    });
  });

  await page.goto('/search-configs');
  await expect(page.getByText('list_failed_test')).toBeVisible();
});

adminTest('search configs: detail loading failure branch @regression @search-configs', async ({ page }) => {
  await page.route('**/api/search/configs', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ configs: [{ id: 'sc_1', name: 'Config One', config: {} }] }),
    });
  });

  await page.route('**/api/search/configs/sc_1', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    return route.fulfill({
      status: 500,
      contentType: 'application/json',
      body: JSON.stringify({ detail: 'detail_failed_test' }),
    });
  });

  await page.goto('/search-configs');
  await expect(page.getByText('detail_failed_test')).toBeVisible();
});

adminTest('search configs: delete and create failure branches @regression @search-configs', async ({ page }) => {
  await page.route('**/api/search/configs', async (route) => {
    const method = route.request().method();
    if (method === 'GET') {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ configs: [{ id: 'sc_1', name: 'Config One', config: { top_k: 5 } }] }),
      });
    }
    if (method === 'POST') {
      return route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'create_failed_test' }),
      });
    }
    return route.fallback();
  });

  await page.route('**/api/search/configs/sc_1', async (route) => {
    const method = route.request().method();
    if (method === 'GET') {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ config: { id: 'sc_1', name: 'Config One', config: { top_k: 5 } } }),
      });
    }
    if (method === 'DELETE') {
      return route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'delete_failed_test' }),
      });
    }
    return route.fallback();
  });

  await page.goto('/search-configs');
  await expect(page.getByText('ID: sc_1')).toBeVisible();

  page.once('dialog', async (dialog) => dialog.accept());
  await page.getByRole('button', { name: 'Del' }).click();
  await expect(page.getByText('delete_failed_test')).toBeVisible();

  await page.getByRole('button', { name: 'New' }).click();
  await page.getByPlaceholder('Input name').fill('Create Failure Config');
  await page.locator('textarea').nth(1).fill('{\n  "top_k": 8\n}');
  await page.getByRole('button', { name: 'Create' }).click();
  await expect(page.getByText('create_failed_test')).toBeVisible();
});
