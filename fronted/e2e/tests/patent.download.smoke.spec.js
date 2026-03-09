// @ts-check
const { expect } = require('@playwright/test');
const { adminTest } = require('../helpers/auth');

adminTest('patent download smoke: run once and render result @regression @tools @patent', async ({ page }) => {
  let createBody = null;

  await page.route('**/api/patent-download/sessions', async (route) => {
    if (route.request().method() !== 'POST') return route.fallback();
    createBody = route.request().postDataJSON();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        session: { session_id: 'patent_s1', status: 'completed' },
        items: [
          {
            session_id: 'patent_s1',
            item_id: 'patent_item_1',
            title: 'Guidewire Inflation Device Patent',
            filename: 'guidewire-patent.pdf',
            status: 'downloaded',
            has_file: true,
          },
        ],
        summary: { total: 1, downloaded: 1 },
        source_stats: { google_patents: { total: 1, downloaded: 1 } },
        source_errors: {},
      }),
    });
  });

  await page.route('**/api/patent-download/history/keywords**', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    const pathname = new URL(route.request().url()).pathname;
    if (/\/api\/patent-download\/history\/keywords\/[^/]+$/.test(pathname)) {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          session: { session_id: 'patent_hist_1', status: 'completed' },
          items: [
            {
              session_id: 'patent_hist_1',
              item_id: 'patent_hist_item_1',
              title: 'Guidewire Patent History Doc',
              filename: 'guidewire-history-patent.pdf',
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

  await page.goto('/tools/patent-download');

  await page.locator('textarea').first().fill('导丝');

  await Promise.all([
    page.waitForResponse((resp) => resp.url().includes('/api/patent-download/sessions') && resp.request().method() === 'POST'),
    page.getByRole('button', { name: 'Run Download' }).click(),
  ]);

  expect(createBody).toBeTruthy();
  expect(createBody.keyword_text).toBe('导丝');
  expect(createBody.use_and).toBe(true);
  expect(createBody.sources).toBeTruthy();

  await expect(page.getByText('Guidewire Inflation Device Patent')).toBeVisible();

  await page.getByRole('button', { name: 'History' }).click();
  await expect(page.getByText('Guidewire Patent History Doc')).toBeVisible();
});
