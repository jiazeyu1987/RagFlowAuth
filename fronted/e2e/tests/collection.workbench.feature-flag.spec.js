// @ts-check
const { expect } = require('@playwright/test');
const { adminTest } = require('../helpers/auth');

adminTest('collection workbench falls back to legacy layout when flag disabled @regression @tools', async ({ page }) => {
  await page.route('**/api/security/feature-flags', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        paper_plag_enabled: true,
        egress_policy_enabled: true,
        research_ui_layout_enabled: false,
      }),
    });
  });

  await page.route('**/api/tasks/metrics**', async (route) => {
    const requestUrl = new URL(route.request().url());
    if (requestUrl.searchParams.get('kind') !== 'collection') return route.fallback();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        task_kind: 'collection',
        total_tasks: 0,
        failed_tasks: 0,
        backlog_tasks: 0,
        failure_rate: 0,
        status_counts: {},
      }),
    });
  });

  await page.route('**/api/tasks?**', async (route) => {
    const requestUrl = new URL(route.request().url());
    if (requestUrl.pathname !== '/api/tasks') return route.fallback();
    if (requestUrl.searchParams.get('kind') !== 'collection') return route.fallback();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        task_kind: 'collection',
        status_filter: [],
        limit: 200,
        total_tasks: 0,
        tasks: [],
      }),
    });
  });

  await page.goto('/tools/collection-workbench');

  await expect(page.getByTestId('collection-workbench-page')).toBeVisible();
  await expect(page.getByTestId('collection-workbench-legacy-layout')).toBeVisible();
  await expect(page.getByTestId('collection-workbench-shell')).toHaveCount(0);
});
