// @ts-check
const { expect } = require('@playwright/test');
const { adminTest } = require('../helpers/auth');

adminTest('notification settings can save channel and retry failed job @regression @admin', async ({ page }) => {
  let putBody = null;
  let retryHit = false;
  const now = Date.now();

  /** @type {Array<any>} */
  let channels = [];
  /** @type {Array<any>} */
  let jobs = [
    {
      job_id: 101,
      channel_id: 'email-main',
      event_type: 'review_todo_approval',
      payload: { doc_id: 'doc-1' },
      status: 'failed',
      attempts: 1,
      max_attempts: 3,
      last_error: 'smtp_down',
      created_at_ms: now,
      sent_at_ms: null,
      next_retry_at_ms: null,
    },
  ];

  await page.route('**/api/admin/notifications/channels**', async (route) => {
    const method = route.request().method();
    if (method === 'GET') {
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ items: channels, count: channels.length }) });
    }
    if (method === 'PUT') {
      const payload = route.request().postDataJSON();
      putBody = payload;
      const id = route.request().url().split('/').pop();
      const item = {
        channel_id: id,
        channel_type: payload.channel_type,
        name: payload.name,
        enabled: payload.enabled,
        config: payload.config || {},
        created_at_ms: now,
        updated_at_ms: Date.now(),
      };
      channels = [item];
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(item) });
    }
    return route.fallback();
  });

  await page.route('**/api/admin/notifications/jobs/*/retry', async (route) => {
    if (route.request().method() !== 'POST') return route.fallback();
    retryHit = true;
    const id = Number(route.request().url().split('/').slice(-2, -1)[0]);
    jobs = jobs.map((item) => (
      item.job_id === id
        ? { ...item, status: 'sent', attempts: 0, last_error: null, sent_at_ms: Date.now() }
        : item
    ));
    const updated = jobs.find((item) => item.job_id === id);
    return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(updated) });
  });

  await page.route('**/api/admin/notifications/jobs/**/logs**', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        items: [{ id: 1, job_id: 101, channel_id: 'email-main', status: 'failed', error: 'smtp_down', attempted_at_ms: now }],
        count: 1,
      }),
    });
  });

  await page.route('**/api/admin/notifications/jobs**', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ items: jobs, count: jobs.length }) });
  });

  await page.route('**/api/admin/notifications/dispatch**', async (route) => {
    if (route.request().method() !== 'POST') return route.fallback();
    return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ total: 0, items: [] }) });
  });

  await page.goto('/notification-settings');
  await expect(page.getByTestId('notification-settings-page')).toBeVisible();

  await page.getByTestId('notification-channel-id').fill('email-main');
  await page.getByTestId('notification-channel-name').fill('Main Email');
  await page.getByTestId('notification-channel-type').selectOption('email');
  await page.getByTestId('notification-channel-config').fill('{"to_emails":["qa@example.com"]}');
  await page.getByTestId('notification-save-channel').click();

  expect(putBody).toBeTruthy();
  expect(putBody.channel_type).toBe('email');
  expect(putBody.enabled).toBe(true);
  expect(Array.isArray(putBody.config.to_emails)).toBeTruthy();

  await expect(page.getByText('email-main').first()).toBeVisible();

  await page.getByTestId('notification-retry-101').click();
  expect(retryHit).toBeTruthy();
  await expect(page.getByText('sent').first()).toBeVisible();
});
