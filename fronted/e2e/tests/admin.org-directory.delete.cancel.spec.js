// @ts-check
const { expect } = require('@playwright/test');
const { adminTest } = require('../helpers/auth');

adminTest('org directory delete confirm can be cancelled @regression @admin', async ({ page }) => {
  const companies = [{ id: 1, name: 'E2E Company', updated_at_ms: Date.now() }];

  await page.route('**/api/org/companies**', async (route) => {
    const url = new URL(route.request().url());
    const method = route.request().method();

    if (method === 'GET') {
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(companies) });
    }

    if (method === 'DELETE' && url.pathname.endsWith('/api/org/companies/1')) {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ok: true }) });
      return;
    }

    return route.fallback();
  });

  await page.route('**/api/org/departments**', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) });
  });

  await page.route('**/api/org/audit**', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) });
  });

  let deleteCalled = false;
  page.on('request', (req) => {
    if (req.method() === 'DELETE' && req.url().includes('/api/org/companies/1')) deleteCalled = true;
  });

  await page.goto('/org-directory');
  await expect(page.getByTestId('org-company-row-1')).toBeVisible();

  page.once('dialog', async (dialog) => {
    await dialog.dismiss();
  });
  await page.getByTestId('org-company-delete-1').click();

  await page.waitForTimeout(300);
  expect(deleteCalled).toBeFalsy();
  await expect(page.getByTestId('org-company-row-1')).toBeVisible();
});

