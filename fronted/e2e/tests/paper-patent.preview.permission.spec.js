// @ts-check
const { test, expect } = require('@playwright/test');
const { adminStorageStatePath } = require('../helpers/auth');

test.use({ storageState: adminStorageStatePath });

async function mockNoDownloadAuth(page) {
  await page.route('**/api/auth/me', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        user_id: 'u_viewer_no_dl_tools',
        username: 'viewer_no_dl_tools',
        role: 'viewer',
        status: 'active',
        permissions: { can_upload: false, can_review: false, can_download: false, can_delete: false },
      }),
    });
  });

  await page.route('**/api/me/kbs', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ kb_ids: ['kb_1'] }) });
  });

  await page.route('**/api/auth/refresh', async (route) => {
    if (route.request().method() !== 'POST') return route.fallback();
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ access_token: 'e2e_access_token', token_type: 'bearer' }),
    });
  });
}

test('paper preview in no-download role never calls paper item download API @regression @tools @paper @rbac', async ({ page }) => {
  await mockNoDownloadAuth(page);

  let previewCalls = 0;
  let downloadCalls = 0;

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
          session: { session_id: 'paper_s1', status: 'completed' },
          items: [
            {
              session_id: 'paper_s1',
              item_id: 'paper_item_1',
              title: 'Paper Preview Doc',
              filename: 'paper-preview.docx',
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

    if (pathname === '/api/paper-download/sessions/paper_s1/items/paper_item_1/preview' && method === 'GET') {
      previewCalls += 1;
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          type: 'text',
          filename: 'paper-preview.docx',
          content: 'paper preview without download permission',
        }),
      });
    }

    if (pathname === '/api/paper-download/sessions/paper_s1/items/paper_item_1/download' && method === 'GET') {
      downloadCalls += 1;
      return route.fulfill({ status: 200, contentType: 'application/octet-stream', body: 'mock-download' });
    }

    return route.fallback();
  });

  await page.goto('/tools/paper-download');
  await page.locator('textarea').first().fill('导丝');
  await page.getByRole('button', { name: 'Run Download' }).click();

  await expect(page.getByText('Paper Preview Doc')).toBeVisible();
  await page.getByTestId('download-view-paper_item_1').click();

  const modal = page.getByTestId('document-preview-modal');
  await expect(modal).toBeVisible();
  await expect(modal).toContainText('paper preview without download permission');
  expect(previewCalls).toBe(1);
  expect(downloadCalls).toBe(0);
});

test('patent preview in no-download role never calls patent item download API @regression @tools @patent @rbac', async ({ page }) => {
  await mockNoDownloadAuth(page);

  let previewCalls = 0;
  let downloadCalls = 0;

  await page.route('**/api/patent-download/**', async (route) => {
    const req = route.request();
    const method = req.method();
    const pathname = new URL(req.url()).pathname;

    if (pathname === '/api/patent-download/history/keywords' && method === 'GET') {
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ history: [] }) });
    }

    if (pathname === '/api/patent-download/sessions' && method === 'POST') {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          session: { session_id: 'patent_s1', status: 'completed' },
          items: [
            {
              session_id: 'patent_s1',
              item_id: 'patent_item_1',
              title: 'Patent Preview Doc',
              filename: 'patent-preview.docx',
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

    if (pathname === '/api/patent-download/sessions/patent_s1/items/patent_item_1/preview' && method === 'GET') {
      previewCalls += 1;
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          type: 'text',
          filename: 'patent-preview.docx',
          content: 'patent preview without download permission',
        }),
      });
    }

    if (pathname === '/api/patent-download/sessions/patent_s1/items/patent_item_1/download' && method === 'GET') {
      downloadCalls += 1;
      return route.fulfill({ status: 200, contentType: 'application/octet-stream', body: 'mock-download' });
    }

    return route.fallback();
  });

  await page.goto('/tools/patent-download');
  await page.locator('textarea').first().fill('导丝');
  await page.getByRole('button', { name: 'Run Download' }).click();

  await expect(page.getByText('Patent Preview Doc')).toBeVisible();
  await page.getByTestId('download-view-patent_item_1').click();

  const modal = page.getByTestId('document-preview-modal');
  await expect(modal).toBeVisible();
  await expect(modal).toContainText('patent preview without download permission');
  expect(previewCalls).toBe(1);
  expect(downloadCalls).toBe(0);
});
