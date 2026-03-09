// @ts-check
const { expect } = require('@playwright/test');
const { adminTest, viewerTest } = require('../helpers/auth');

viewerTest('viewer cannot access /users @rbac', async ({ page }) => {
  await page.goto('/users');
  await expect(page).toHaveURL(/\/unauthorized$/);
  await expect(page.getByTestId('unauthorized-title')).toBeVisible();
});

viewerTest('viewer cannot access /chat-configs @rbac', async ({ page }) => {
  await page.goto('/chat-configs');
  await expect(page).toHaveURL(/\/unauthorized$/);
  await expect(page.getByTestId('unauthorized-title')).toBeVisible();
});

adminTest('/audit alias redirects to records tab in /documents @regression @rbac', async ({ page }) => {
  await page.route('**/api/users**', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) });
  });
  await page.route('**/api/knowledge/documents**', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ documents: [] }) });
  });
  await page.route('**/api/knowledge/deletions**', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ deletions: [] }) });
  });
  await page.route('**/api/ragflow/downloads**', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ downloads: [] }) });
  });

  await page.goto('/audit');
  await expect(page).toHaveURL(/\/documents\?tab=records$/);
  await expect(page.getByTestId('documents-page')).toBeVisible();
  await expect(page.getByTestId('audit-page')).toBeVisible();
});

adminTest('authorized user can visit /unauthorized route directly @rbac', async ({ page }) => {
  await page.goto('/unauthorized');
  await expect(page).toHaveURL(/\/unauthorized$/);
  await expect(page.getByTestId('unauthorized-title')).toBeVisible();
});
