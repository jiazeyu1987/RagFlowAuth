// @ts-check
const { expect } = require('@playwright/test');
const { adminTest } = require('../helpers/auth');

async function openAssertCloseExcelModal(page, { baselineBox = null } = {}) {
  const modal = page.getByTestId('document-preview-modal');
  await expect(modal).toBeVisible({ timeout: 30_000 });

  const box = await modal.boundingBox();
  expect(box).toBeTruthy();
  expect(box.width).toBeGreaterThan(900);
  expect(box.height).toBeGreaterThan(500);

  // Excel table mode should render at least one <table>.
  await expect(modal.locator('table').first()).toBeVisible();

  // Modal sizing should be consistent across entry points (within small tolerance).
  if (baselineBox) {
    expect(Math.abs(box.width - baselineBox.width)).toBeLessThanOrEqual(25);
    expect(Math.abs(box.height - baselineBox.height)).toBeLessThanOrEqual(25);
  }

  await page.keyboard.press('Escape');
  await expect(modal).toBeHidden({ timeout: 10_000 });
  return box;
}

adminTest('unified preview modal behaves consistently across 4 entry points (mock) @regression @preview', async ({ page }) => {
  const filename = 'demo.xlsx';
  const ragflowDatasetId = 'ds1';
  const ragflowDocId = 'doc1';
  const knowledgeDocId = 'k1';

  const excelHtml = '<table><tbody><tr><td>A1</td><td>B1</td></tr><tr><td>A2</td><td>B2</td></tr></tbody></table>';

  // Shared: datasets (used by /browser, /agents, /documents).
  await page.route('**/api/datasets', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ datasets: [{ id: ragflowDatasetId, name: '展厅' }], count: 1 }),
    });
  });

  // /browser: ragflow documents list.
  await page.route('**/api/ragflow/documents?*', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ documents: [{ id: ragflowDocId, name: filename, status: 'ok' }], count: 1 }),
    });
  });

  // /agents: search results.
  await page.route('**/api/search', async (route) => {
    if (route.request().method() !== 'POST') return route.fallback();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        chunks: [
          {
            id: 'c1',
            content: 'chunk for preview',
            dataset_id: ragflowDatasetId,
            doc_id: ragflowDocId,
            doc_name: filename,
          },
        ],
        total: 1,
        page: 1,
        page_size: 30,
      }),
    });
  });

  // /documents: local pending docs list.
  await page.route('**/api/knowledge/documents**', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    const url = new URL(route.request().url());
    if (url.searchParams.get('status') !== 'pending') return route.fallback();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        documents: [
          {
            doc_id: knowledgeDocId,
            filename,
            status: 'pending',
            uploaded_at_ms: Date.now(),
            kb_id: ragflowDatasetId,
            uploaded_by: 'u1',
          },
        ],
        count: 1,
      }),
    });
  });

  // /chat: chats + sessions.
  await page.route('**/api/chats/my', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ chats: [{ id: 'chat1', name: '行政聊天' }] }),
    });
  });
  await page.route('**/api/chats/chat1/sessions', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        sessions: [
          {
            id: 's1',
            name: '会话1',
            messages: [
              {
                role: 'assistant',
                content: `这里引用文件 [ID:1]`,
                sources: [
                  {},
                  {
                    doc_id: ragflowDocId,
                    dataset_id: ragflowDatasetId,
                    doc_name: filename,
                    chunk: 'A1,B1',
                  },
                ],
              },
            ],
          },
        ],
      }),
    });
  });

  // Unified preview gateway (ragflow + knowledge).
  await page.route(`**/api/preview/documents/ragflow/${ragflowDocId}/preview?*`, async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ type: 'excel', filename, sheets: { Sheet1: excelHtml } }),
    });
  });
  await page.route(`**/api/preview/documents/knowledge/${knowledgeDocId}/preview**`, async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ type: 'excel', filename, sheets: { Sheet1: excelHtml } }),
    });
  });

  // 1) DocumentBrowser
  await page.goto('/browser');
  await page.getByTestId(`browser-dataset-toggle-${ragflowDatasetId}`).click();
  await expect(page.getByTestId(`browser-doc-row-${ragflowDatasetId}-${ragflowDocId}`)).toBeVisible();
  await page.getByTestId(`browser-doc-view-${ragflowDatasetId}-${ragflowDocId}`).click();
  const baseline = await openAssertCloseExcelModal(page);

  // 2) Agents search
  await page.goto('/agents');
  await page.getByPlaceholder(/搜索/).fill('demo');
  await page.getByRole('button', { name: /搜索/ }).click();
  await expect(page.getByText('chunk for preview')).toBeVisible();
  await page.getByTestId(`agents-doc-view-${ragflowDatasetId}-${ragflowDocId}`).click();
  await openAssertCloseExcelModal(page, { baselineBox: baseline });

  // 3) DocumentReview
  await page.goto('/documents');
  const row = page.locator('tr', { hasText: filename });
  await expect(row).toBeVisible();
  await page.getByTestId(`docs-preview-${knowledgeDocId}`).click();
  await openAssertCloseExcelModal(page, { baselineBox: baseline });

  // 4) Chat citations
  await page.goto('/chat');
  await expect(page.getByTestId('chat-source-view-1')).toBeVisible({ timeout: 30_000 });
  await page.getByTestId('chat-source-view-1').click();
  await openAssertCloseExcelModal(page, { baselineBox: baseline });
});
