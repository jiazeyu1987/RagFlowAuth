// @ts-check
const { expect } = require('@playwright/test');
const { operatorTest } = require('../helpers/auth');

operatorTest('messages center supports read-state toggle and mark-all-read @regression', async ({ page }) => {
  const now = Date.now();

  /** @type {Array<any>} */
  let messages = [
    {
      job_id: 901,
      channel_id: 'inapp-main',
      channel_name: 'In App',
      event_type: 'review_todo_approval',
      payload: { doc_id: 'doc-1', filename: 'doc-1.pdf', current_step_name: 'QA Review' },
      status: 'sent',
      recipient_user_id: 'u1',
      recipient_username: 'operator',
      recipient_address: 'u1',
      created_at_ms: now,
      sent_at_ms: now,
      read_at_ms: null,
    },
  ];

  const calcUnreadCount = () => messages.filter((item) => !item.read_at_ms).length;

  await page.route('**/api/me/messages/mark-all-read', async (route) => {
    if (route.request().method() !== 'POST') return route.fallback();
    let updated = 0;
    messages = messages.map((item) => {
      if (item.read_at_ms) return item;
      updated += 1;
      return { ...item, read_at_ms: Date.now() };
    });
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ updated_count: updated }),
    });
  });

  await page.route('**/api/me/messages/*/read-state', async (route) => {
    if (route.request().method() !== 'PATCH') return route.fallback();
    const id = Number(route.request().url().split('/').slice(-2, -1)[0]);
    const body = route.request().postDataJSON() || {};
    const read = !!body.read;
    messages = messages.map((item) => (
      item.job_id === id
        ? { ...item, read_at_ms: read ? Date.now() : null }
        : item
    ));
    const item = messages.find((x) => x.job_id === id);
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(item || {}),
    });
  });

  await page.route('**/api/me/messages**', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    const url = new URL(route.request().url());
    const unreadOnly = url.searchParams.get('unread_only') === 'true';
    const items = unreadOnly ? messages.filter((item) => !item.read_at_ms) : messages;
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        items,
        count: items.length,
        total: messages.length,
        unread_count: calcUnreadCount(),
      }),
    });
  });

  await page.goto('/messages');
  await expect(page.getByTestId('messages-page')).toBeVisible();
  await expect(page.getByTestId('messages-unread-count')).toContainText('1');

  await page.getByTestId('messages-toggle-read-901').click();
  await expect(page.getByTestId('messages-unread-count')).toContainText('0');

  await page.getByTestId('messages-toggle-read-901').click();
  await expect(page.getByTestId('messages-unread-count')).toContainText('1');

  await page.getByTestId('messages-mark-all-read').click();
  await expect(page.getByTestId('messages-unread-count')).toContainText('0');
});

