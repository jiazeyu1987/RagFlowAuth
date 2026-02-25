// @ts-check
const { expect } = require('@playwright/test');
const { adminTest } = require('../helpers/auth');

async function openAssertCloseTableModal(page, { baselineBox = null } = {}) {
  const modal = page.getByTestId('document-preview-modal');
  await expect(modal).toBeVisible({ timeout: 30_000 });

  const box = await modal.boundingBox();
  expect(box).toBeTruthy();
  expect(box.width).toBeGreaterThan(900);
  expect(box.height).toBeGreaterThan(500);

  await expect(modal.locator('table').first()).toBeVisible();

  if (baselineBox) {
    expect(Math.abs(box.width - baselineBox.width)).toBeLessThanOrEqual(25);
    expect(Math.abs(box.height - baselineBox.height)).toBeLessThanOrEqual(25);
  }

  await page.keyboard.press('Escape');
  await expect(modal).toBeHidden({ timeout: 10_000 });
  return box;
}

adminTest('unified preview modal behaves consistently across 4 entry points (mock) @regression @preview', async ({ page }) => {
  const filename = 'demo.csv';
  const ragflowDatasetId = 'ds1';
  const ragflowDocId = 'doc1';
  const knowledgeDocId = 'k1';
  const csvText = 'A,B\n1,2\n3,4\n';

  await page.route('**/api/datasets', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ datasets: [{ id: ragflowDatasetId, name: 'kb-one' }], count: 1 }),
    });
  });

  await page.route('**/api/ragflow/documents?*', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ documents: [{ id: ragflowDocId, name: filename, status: 'ok' }], count: 1 }),
    });
  });

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

  await page.route('**/api/chats/my', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ chats: [{ id: 'chat1', name: 'chat-1' }] }),
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
            name: 'session-1',
            messages: [
              {
                role: 'assistant',
                content: '引用文件 [ID:1]',
                sources: [
                  {},
                  {
                    doc_id: ragflowDocId,
                    dataset_id: ragflowDatasetId,
                    doc_name: filename,
                    chunk: 'A,B',
                  },
                ],
              },
            ],
          },
        ],
      }),
    });
  });

  await page.route(`**/api/preview/documents/ragflow/${ragflowDocId}/preview?*`, async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ type: 'text', filename, content: csvText }),
    });
  });
  await page.route(`**/api/preview/documents/knowledge/${knowledgeDocId}/preview**`, async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ type: 'text', filename, content: csvText }),
    });
  });

  await page.goto('/browser');
  await page.getByTestId(`browser-dataset-toggle-${ragflowDatasetId}`).click();
  await expect(page.getByTestId(`browser-doc-row-${ragflowDatasetId}-${ragflowDocId}`)).toBeVisible();
  await page.getByTestId(`browser-doc-view-${ragflowDatasetId}-${ragflowDocId}`).click();
  const baseline = await openAssertCloseTableModal(page);

  await page.goto('/agents');
  await page.getByPlaceholder(/搜索|关键/).fill('demo');
  await page.getByRole('button', { name: /搜索/ }).click();
  await expect(page.getByText('chunk for preview')).toBeVisible();
  await page.getByTestId(`agents-doc-view-${ragflowDatasetId}-${ragflowDocId}`).click();
  await openAssertCloseTableModal(page, { baselineBox: baseline });

  await page.goto('/documents');
  const row = page.locator('tr', { hasText: filename });
  await expect(row).toBeVisible();
  await page.getByTestId(`docs-preview-${knowledgeDocId}`).click();
  await openAssertCloseTableModal(page, { baselineBox: baseline });

  await page.goto('/chat');
  await expect(page.getByTestId('chat-source-view-1')).toBeVisible({ timeout: 30_000 });
  await page.getByTestId('chat-source-view-1').click();
  await openAssertCloseTableModal(page, { baselineBox: baseline });
});
