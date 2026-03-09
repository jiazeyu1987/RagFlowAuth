// @ts-check
const { expect } = require('@playwright/test');
const { adminTest } = require('../helpers/auth');

adminTest('paper download running stop and item add/delete failure branches @regression @tools @paper', async ({ page }) => {
  let status = 'running';
  let stopCalled = 0;

  await page.route('**/api/paper-download/**', async (route) => {
    const req = route.request();
    const method = req.method();
    const pathname = new URL(req.url()).pathname;

    if (pathname === '/api/paper-download/history/keywords' && method === 'GET') {
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ history: [] }) });
    }

    if (pathname === '/api/paper-download/sessions' && method === 'POST') {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          session: { session_id: 'paper_run_1', status },
          items: [
            {
              session_id: 'paper_run_1',
              item_id: 'paper_fail_1',
              title: 'Paper Fail Item',
              filename: 'paper-fail.pdf',
              status: 'downloaded',
              has_file: false,
            },
          ],
          summary: { total: 1, downloaded: 1 },
          source_stats: {},
          source_errors: {},
        }),
      });
    }

    if (pathname === '/api/paper-download/sessions/paper_run_1' && method === 'GET') {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          session: { session_id: 'paper_run_1', status },
          items: [
            {
              session_id: 'paper_run_1',
              item_id: 'paper_fail_1',
              title: 'Paper Fail Item',
              filename: 'paper-fail.pdf',
              status: 'downloaded',
              has_file: false,
            },
          ],
          summary: { total: 1, downloaded: 1 },
          source_stats: {},
          source_errors: {},
        }),
      });
    }

    if (pathname === '/api/paper-download/sessions/paper_run_1/stop' && method === 'POST') {
      stopCalled += 1;
      status = 'stopped';
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ status: 'stopped' }) });
    }

    if (pathname === '/api/paper-download/sessions/paper_run_1/items/paper_fail_1/add-to-local-kb' && method === 'POST') {
      return route.fulfill({ status: 500, contentType: 'application/json', body: JSON.stringify({ detail: 'add_failed_for_test' }) });
    }

    if (pathname === '/api/paper-download/sessions/paper_run_1/items/paper_fail_1' && method === 'DELETE') {
      return route.fulfill({ status: 500, contentType: 'application/json', body: JSON.stringify({ detail: 'delete_failed_for_test' }) });
    }

    return route.fallback();
  });

  await page.goto('/tools/paper-download');

  await page.locator('textarea').first().fill('导丝');
  await Promise.all([
    page.waitForResponse((resp) => new URL(resp.url()).pathname === '/api/paper-download/sessions' && resp.request().method() === 'POST'),
    page.getByRole('button', { name: 'Run Download' }).click(),
  ]);

  await expect(page.getByText('Paper Fail Item')).toBeVisible();
  await expect(page.getByTestId('download-view-paper_fail_1')).toBeDisabled();

  await Promise.all([
    page.waitForResponse((resp) => new URL(resp.url()).pathname === '/api/paper-download/sessions/paper_run_1/stop' && resp.request().method() === 'POST'),
    page.getByTestId('download-stop').click(),
  ]);
  expect(stopCalled).toBe(1);

  await Promise.all([
    page.waitForResponse((resp) => new URL(resp.url()).pathname.endsWith('/add-to-local-kb') && resp.request().method() === 'POST'),
    page.getByTestId('download-add-paper_fail_1').click(),
  ]);
  await expect(page.getByText('add_failed_for_test')).toBeVisible();

  page.once('dialog', async (dialog) => dialog.accept());
  await Promise.all([
    page.waitForResponse((resp) => new URL(resp.url()).pathname === '/api/paper-download/sessions/paper_run_1/items/paper_fail_1' && resp.request().method() === 'DELETE'),
    page.getByTestId('download-delete-paper_fail_1').click(),
  ]);
  await expect(page.getByText('delete_failed_for_test')).toBeVisible();
});
