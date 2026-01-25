// @ts-check
const { expect } = require('@playwright/test');
const { adminTest, viewerTest } = require('../helpers/auth');

adminTest('dashboard shows stats cards and quick actions (mock) @regression @dashboard', async ({ page }) => {
  await page.route('**/api/knowledge/stats', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        pending_documents: 3,
        approved_documents: 10,
        rejected_documents: 2,
        total_documents: 15,
      }),
    });
  });

  await page.goto('/');

  await expect(page.getByTestId('layout-user-name')).toBeVisible();
  await expect(page.getByRole('heading', { name: /欢迎/ })).toBeVisible();
  await expect(page.getByRole('heading', { name: /快速操作/ })).toBeVisible();

  // Quick actions should be present for admin.
  await expect(page.getByRole('button', { name: /上传/ })).toBeVisible();
  await expect(page.getByRole('button', { name: /文档管理/ })).toBeVisible();
});

adminTest('dashboard stats 500 falls back to zeros (mock) @regression @dashboard', async ({ page }) => {
  let statsCalled = false;

  await page.route('**/api/knowledge/stats', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    statsCalled = true;
    await route.fulfill({ status: 500, contentType: 'application/json', body: JSON.stringify({ detail: 'stats failed' }) });
  });

  await page.goto('/');

  await expect(page.getByTestId('layout-user-name')).toBeVisible();
  await expect(page.getByRole('heading', { name: /快速操作/ })).toBeVisible();
  expect(statsCalled).toBe(true);
});

adminTest('dashboard stats empty payload does not crash (mock) @regression @dashboard', async ({ page }) => {
  await page.route('**/api/knowledge/stats', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({}) });
  });

  await page.goto('/');
  await expect(page.getByTestId('layout-user-name')).toBeVisible();
  await expect(page.getByRole('heading', { name: /快速操作/ })).toBeVisible();
});

viewerTest('dashboard viewer sees only browse action and can navigate (mock) @regression @dashboard', async ({ page }) => {
  let statsCalled = false;

  await page.route('**/api/knowledge/stats', async (route) => {
    statsCalled = true;
    return route.fallback();
  });

  await page.goto('/');
  await expect(page.getByTestId('layout-user-name')).toBeVisible();

  await expect(page.getByRole('button', { name: /浏览文档/ })).toBeVisible();
  await expect(page.getByRole('button', { name: /上传/ })).toHaveCount(0);
  await expect(page.getByRole('button', { name: /文档管理/ })).toHaveCount(0);
  expect(statsCalled).toBe(false);

  await page.getByRole('button', { name: /浏览文档/ }).click();
  await expect(page).toHaveURL(/\/browser/);
});
