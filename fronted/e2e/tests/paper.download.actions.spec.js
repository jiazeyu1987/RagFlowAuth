// @ts-check
const { expect } = require('@playwright/test');
const { adminTest } = require('../helpers/auth');

adminTest('paper download actions: current and history operations @regression @tools @paper', async ({ page }) => {
  let createBody = null;
  let addAllBody = null;
  let addHistoryBody = null;
  let deleteHistoryBody = null;
  let deleteSessionCalls = 0;

  let historyRows = [
    {
      history_key: '导丝',
      keyword_display: '导丝',
      downloaded_count: 2,
      analyzed_count: 0,
      added_count: 0,
    },
  ];

  await page.route('**/api/paper-download/**', async (route) => {
    const req = route.request();
    const method = req.method();
    const pathname = new URL(req.url()).pathname;

    if (pathname === '/api/paper-download/sessions' && method === 'POST') {
      createBody = req.postDataJSON();
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          session: { session_id: 'paper_s1', status: 'completed' },
          items: [
            {
              session_id: 'paper_s1',
              item_id: 'paper_item_1',
              title: 'Guidewire Current Result',
              filename: 'guidewire-current.pdf',
              status: 'downloaded',
              has_file: true,
            },
          ],
          summary: { total: 1, downloaded: 1 },
          source_stats: { arxiv: { total: 1, downloaded: 1 } },
          source_errors: {},
        }),
      });
    }

    if (pathname === '/api/paper-download/sessions/paper_s1/add-all-to-local-kb' && method === 'POST') {
      addAllBody = req.postDataJSON();
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ success: 1, failed: 0 }),
      });
    }

    if (pathname === '/api/paper-download/sessions/paper_s1' && method === 'DELETE') {
      deleteSessionCalls += 1;
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ deleted_items: 1, deleted_docs: 1 }),
      });
    }

    if (pathname === '/api/paper-download/history/keywords' && method === 'GET') {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ history: historyRows }),
      });
    }

    if (pathname === '/api/paper-download/history/keywords/delete' && method === 'POST') {
      deleteHistoryBody = req.postDataJSON();
      historyRows = [];
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ deleted_sessions: 1, deleted_items: 2, deleted_files: 2 }),
      });
    }

    if (pathname.endsWith('/add-all-to-local-kb') && pathname.includes('/api/paper-download/history/keywords/') && method === 'POST') {
      addHistoryBody = req.postDataJSON();
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ success: 2, failed: 0 }),
      });
    }

    if (pathname.startsWith('/api/paper-download/history/keywords/') && method === 'GET') {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          session: { session_id: 'paper_hist_1', status: 'completed' },
          items: [
            {
              session_id: 'paper_hist_1',
              item_id: 'paper_hist_item_1',
              title: 'Guidewire History Result',
              filename: 'guidewire-history.pdf',
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

  await page.goto('/tools/paper-download');

  await page.locator('textarea').first().fill('导丝');
  await Promise.all([
    page.waitForResponse((resp) => resp.url().includes('/api/paper-download/sessions') && resp.request().method() === 'POST'),
    page.getByRole('button', { name: 'Run Download' }).click(),
  ]);

  expect(createBody).toBeTruthy();
  expect(createBody.keyword_text).toBe('导丝');
  await expect(page.getByText('Guidewire Current Result')).toBeVisible();

  await Promise.all([
    page.waitForResponse((resp) => resp.url().includes('/api/paper-download/sessions/paper_s1/add-all-to-local-kb') && resp.request().method() === 'POST'),
    page.getByRole('button', { name: 'Add All To KB' }).click(),
  ]);
  expect(addAllBody).toBeTruthy();
  expect(String(addAllBody.kb_ref || '')).not.toBe('');

  page.once('dialog', async (dialog) => dialog.accept());
  await Promise.all([
    page.waitForResponse((resp) => new URL(resp.url()).pathname === '/api/paper-download/sessions/paper_s1' && resp.request().method() === 'DELETE'),
    page.getByRole('button', { name: 'Delete All' }).click(),
  ]);
  expect(deleteSessionCalls).toBe(1);

  await page.getByRole('button', { name: 'History' }).click();
  await expect(page.getByText('Guidewire History Result')).toBeVisible();

  await Promise.all([
    page.waitForResponse((resp) => new URL(resp.url()).pathname.endsWith('/add-all-to-local-kb') && resp.request().method() === 'POST'),
    page.getByRole('button', { name: 'Add to KB' }).first().click(),
  ]);
  expect(addHistoryBody).toBeTruthy();
  expect(String(addHistoryBody.kb_ref || '')).not.toBe('');

  page.once('dialog', async (dialog) => dialog.accept());
  await Promise.all([
    page.waitForResponse((resp) => new URL(resp.url()).pathname === '/api/paper-download/history/keywords/delete' && resp.request().method() === 'POST'),
    page.getByRole('button', { name: 'Delete' }).first().click(),
  ]);

  expect(deleteHistoryBody).toEqual({ history_key: '导丝' });
  await expect(page.getByText('No history keywords')).toBeVisible();
});
