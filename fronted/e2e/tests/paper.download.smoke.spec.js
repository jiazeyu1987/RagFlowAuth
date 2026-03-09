// @ts-check
const { expect } = require('@playwright/test');
const { adminTest } = require('../helpers/auth');

adminTest('paper download smoke: run once and render result @regression @tools @paper', async ({ page }) => {
  let createBody = null;

  await page.route('**/api/paper-download/sessions', async (route) => {
    if (route.request().method() !== 'POST') return route.fallback();
    createBody = route.request().postDataJSON();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        session: { session_id: 'paper_s1', status: 'completed' },
        items: [
          {
            session_id: 'paper_s1',
            item_id: 'paper_item_1',
            title: 'Guidewire Overview',
            filename: 'guidewire-overview.pdf',
            status: 'downloaded',
            has_file: true,
          },
        ],
        summary: { total: 1, downloaded: 1 },
        source_stats: { arxiv: { total: 1, downloaded: 1 } },
        source_errors: {},
      }),
    });
  });

  await page.route('**/api/paper-download/history/keywords**', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    const pathname = new URL(route.request().url()).pathname;
    if (/\/api\/paper-download\/history\/keywords\/[^/]+$/.test(pathname)) {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          session: { session_id: 'paper_hist_1', status: 'completed' },
          items: [
            {
              session_id: 'paper_hist_1',
              item_id: 'paper_hist_item_1',
              title: 'Guidewire History Doc',
              filename: 'guidewire-history.pdf',
              status: 'downloaded',
              has_file: true,
            },
          ],
          summary: { total: 1, downloaded: 1 },
        }),
      });
    }

    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        history: [
          {
            history_key: '导丝',
            keyword_display: '导丝',
            downloaded_count: 1,
            analyzed_count: 0,
            added_count: 0,
          },
        ],
      }),
    });
  });

  await page.goto('/tools/paper-download');

  await page.locator('textarea').first().fill('导丝');

  await Promise.all([
    page.waitForResponse((resp) => resp.url().includes('/api/paper-download/sessions') && resp.request().method() === 'POST'),
    page.getByRole('button', { name: 'Run Download' }).click(),
  ]);

  expect(createBody).toBeTruthy();
  expect(createBody.keyword_text).toBe('导丝');
  expect(createBody.use_and).toBe(true);
  expect(createBody.sources).toBeTruthy();

  await expect(page.getByText('Guidewire Overview')).toBeVisible();

  await page.getByRole('button', { name: 'History' }).click();
  await expect(page.getByText('Guidewire History Doc')).toBeVisible();
});
