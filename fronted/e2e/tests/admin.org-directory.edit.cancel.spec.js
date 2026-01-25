// @ts-check
const { expect } = require('@playwright/test');
const { adminTest } = require('../helpers/auth');

adminTest('org directory edit prompt can be cancelled @regression @admin', async ({ page }) => {
  const companies = [{ id: 1, name: 'E2E Company', updated_at_ms: Date.now() }];

  await page.route('**/api/org/companies**', async (route) => {
    const url = new URL(route.request().url());
    const method = route.request().method();

    if (method === 'GET') {
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(companies) });
    }

    if (method === 'PUT' && url.pathname.endsWith('/api/org/companies/1')) {
      const body = route.request().postDataJSON();
      companies[0] = { ...companies[0], name: body.name, updated_at_ms: Date.now() };
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(companies[0]) });
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

  let updateCalled = false;
  page.on('request', (req) => {
    if (req.method() === 'PUT' && req.url().includes('/api/org/companies/1')) updateCalled = true;
  });

  await page.goto('/org-directory');
  await expect(page.getByText('E2E Company', { exact: true })).toBeVisible();

  page.once('dialog', async (dialog) => {
    await dialog.dismiss();
  });
  await page.getByTestId('org-company-edit-1').click();

  await page.waitForTimeout(300);
  expect(updateCalled).toBeFalsy();
  await expect(page.getByText('E2E Company', { exact: true })).toBeVisible();
});

