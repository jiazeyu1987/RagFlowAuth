// @ts-check
const { expect } = require('@playwright/test');
const { adminTest } = require('../helpers/auth');

adminTest('collection workbench supports task control and batch ingest @regression @tools', async ({ page }) => {
  await page.route('**/api/security/feature-flags', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        paper_plag_enabled: true,
        egress_policy_enabled: true,
        research_ui_layout_enabled: true,
      }),
    });
  });

  const tasks = [
    {
      task_id: 'paper_task_1',
      task_kind: 'paper_download',
      status: 'running',
      progress_percent: 40,
      total_items: 10,
      downloaded_items: 4,
      failed_items: 0,
      can_pause: false,
      can_resume: false,
      can_cancel: true,
      can_retry: false,
      source_errors: {},
      keyword_text: 'mental health',
      created_at_ms: 1700000000000,
      updated_at_ms: 1700000001000,
    },
  ];

  await page.route('**/api/tasks/metrics**', async (route) => {
    const requestUrl = new URL(route.request().url());
    if (requestUrl.searchParams.get('kind') !== 'collection') return route.fallback();
    const failedCount = tasks.filter((task) => task.status === 'failed').length;
    const backlogCount = tasks.filter((task) => ['pending', 'running', 'canceling'].includes(task.status)).length;
    const statusCounts = tasks.reduce((acc, task) => {
      acc[task.status] = (acc[task.status] || 0) + 1;
      return acc;
    }, {});
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        task_kind: 'collection',
        total_tasks: tasks.length,
        failed_tasks: failedCount,
        backlog_tasks: backlogCount,
        failure_rate: tasks.length ? failedCount / tasks.length : 0,
        status_counts: statusCounts,
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
        total_tasks: tasks.length,
        tasks,
      }),
    });
  });

  await page.route('**/api/tasks/paper_task_1/cancel**', async (route) => {
    if (route.request().method() !== 'POST') return route.fallback();
    tasks[0] = {
      ...tasks[0],
      status: 'canceling',
      can_cancel: false,
      updated_at_ms: 1700000002000,
    };
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(tasks[0]),
    });
  });

  await page.route('**/api/paper-download/sessions/paper_task_1/add-all-to-local-kb', async (route) => {
    if (route.request().method() !== 'POST') return route.fallback();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ success: 4, failed: 0 }),
    });
  });

  await page.goto('/tools/collection-workbench');

  const row = page.getByTestId('collection-task-row-paper_task_1');
  await expect(row).toBeVisible();
  await expect(row).toContainText('Running');

  await page.getByLabel('select task paper_task_1').check();
  await Promise.all([
    page.waitForResponse((resp) => resp.url().includes('/add-all-to-local-kb') && resp.request().method() === 'POST'),
    page.getByTestId('collection-batch-ingest').click(),
  ]);
  await expect(page.getByText('Batch ingest done: success 1, failed 0')).toBeVisible();

  await Promise.all([
    page.waitForResponse((resp) => resp.url().includes('/api/tasks/paper_task_1/cancel') && resp.request().method() === 'POST'),
    page.getByTestId('collection-task-cancel-paper_task_1').click(),
  ]);
  await expect(row).toContainText('Canceling');
});
