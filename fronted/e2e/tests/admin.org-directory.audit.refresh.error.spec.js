// @ts-check
const { expect } = require('@playwright/test');
const { adminTest } = require('../helpers/auth');

adminTest('org directory audit refresh shows error on failure @regression @admin', async ({ page }) => {
  await page.route('**/api/org/companies**', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) });
  });

  await page.route('**/api/org/departments**', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) });
  });

  let auditCalls = 0;
  await page.route('**/api/org/audit**', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    auditCalls += 1;
    if (auditCalls === 1) {
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) });
    }
    return route.fulfill({ status: 500, contentType: 'application/json', body: JSON.stringify({ detail: 'audit failed' }) });
  });

  await page.goto('/org-directory');
  await page.getByTestId('org-tab-audit').click();
  await page.getByTestId('org-audit-refresh').click();
  await expect(page.getByText('Error: audit failed')).toBeVisible();
});

