// @ts-check
const { expect } = require('@playwright/test');
const { adminTest } = require('../helpers/auth');

adminTest('patent download actions: current and history operations @regression @tools @patent', async ({ page }) => {
  let createBody = null;
  let addAllBody = null;
  let addHistoryBody = null;
  let deleteHistoryBody = null;
  let deleteSessionCalls = 0;

  let historyRows = [
    {
      history_key: '导丝',
      keyword_display: '导丝',
      downloaded_count: 1,
      analyzed_count: 0,
      added_count: 0,
    },
  ];

  await page.route('**/api/patent-download/**', async (route) => {
    const req = route.request();
    const method = req.method();
    const pathname = new URL(req.url()).pathname;

    if (pathname === '/api/patent-download/sessions' && method === 'POST') {
      createBody = req.postDataJSON();
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          session: { session_id: 'patent_s1', status: 'completed' },
          items: [
            {
              session_id: 'patent_s1',
              item_id: 'patent_item_1',
              title: 'Guidewire Patent Current',
              filename: 'guidewire-patent-current.pdf',
              status: 'downloaded',
              has_file: true,
            },
          ],
          summary: { total: 1, downloaded: 1 },
          source_stats: { google_patents: { total: 1, downloaded: 1 } },
          source_errors: {},
        }),
      });
    }

    if (pathname === '/api/patent-download/sessions/patent_s1/add-all-to-local-kb' && method === 'POST') {
      addAllBody = req.postDataJSON();
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ success: 1, failed: 0 }),
      });
    }

    if (pathname === '/api/patent-download/sessions/patent_s1' && method === 'DELETE') {
      deleteSessionCalls += 1;
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ deleted_items: 1, deleted_docs: 1 }),
      });
    }

    if (pathname === '/api/patent-download/history/keywords' && method === 'GET') {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ history: historyRows }),
      });
    }

    if (pathname === '/api/patent-download/history/keywords/delete' && method === 'POST') {
      deleteHistoryBody = req.postDataJSON();
      historyRows = [];
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ deleted_sessions: 1, deleted_items: 1, deleted_files: 1 }),
      });
    }

    if (pathname.endsWith('/add-all-to-local-kb') && pathname.includes('/api/patent-download/history/keywords/') && method === 'POST') {
      addHistoryBody = req.postDataJSON();
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ success: 1, failed: 0 }),
      });
    }

    if (pathname.startsWith('/api/patent-download/history/keywords/') && method === 'GET') {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          session: { session_id: 'patent_hist_1', status: 'completed' },
          items: [
            {
              session_id: 'patent_hist_1',
              item_id: 'patent_hist_item_1',
              title: 'Guidewire Patent History',
              filename: 'guidewire-patent-history.pdf',
              status: 'downloaded',
              has_file: true,
            },
          ],
          summary: { total: 1, downloaded: 1 },
        }),
      });
    }

    return route.fallback();
  });

  await page.goto('/tools/patent-download');

  await page.locator('textarea').first().fill('导丝');
  await Promise.all([
    page.waitForResponse((resp) => resp.url().includes('/api/patent-download/sessions') && resp.request().method() === 'POST'),
    page.getByRole('button', { name: 'Run Download' }).click(),
  ]);

  expect(createBody).toBeTruthy();
  expect(createBody.keyword_text).toBe('导丝');
  await expect(page.getByText('Guidewire Patent Current')).toBeVisible();

  await Promise.all([
    page.waitForResponse((resp) => resp.url().includes('/api/patent-download/sessions/patent_s1/add-all-to-local-kb') && resp.request().method() === 'POST'),
    page.getByRole('button', { name: 'Add All To KB' }).click(),
  ]);
  expect(addAllBody).toBeTruthy();
  expect(String(addAllBody.kb_ref || '')).not.toBe('');

  page.once('dialog', async (dialog) => dialog.accept());
  await Promise.all([
    page.waitForResponse((resp) => new URL(resp.url()).pathname === '/api/patent-download/sessions/patent_s1' && resp.request().method() === 'DELETE'),
    page.getByRole('button', { name: 'Delete All' }).click(),
  ]);
  expect(deleteSessionCalls).toBe(1);

  await page.getByRole('button', { name: 'History' }).click();
  await expect(page.getByText('Guidewire Patent History')).toBeVisible();

  await Promise.all([
    page.waitForResponse((resp) => new URL(resp.url()).pathname.endsWith('/add-all-to-local-kb') && resp.request().method() === 'POST'),
    page.getByRole('button', { name: 'Add to KB' }).first().click(),
  ]);
  expect(addHistoryBody).toBeTruthy();
  expect(String(addHistoryBody.kb_ref || '')).not.toBe('');

  page.once('dialog', async (dialog) => dialog.accept());
  await Promise.all([
    page.waitForResponse((resp) => new URL(resp.url()).pathname === '/api/patent-download/history/keywords/delete' && resp.request().method() === 'POST'),
    page.getByRole('button', { name: 'Delete' }).first().click(),
  ]);

  expect(deleteHistoryBody).toEqual({ history_key: '导丝' });
  await expect(page.getByText('No history keywords')).toBeVisible();
});
