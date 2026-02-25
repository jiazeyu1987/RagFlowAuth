// @ts-check
const { expect } = require('@playwright/test');
const { adminTest } = require('../helpers/auth');

async function openAssertMarkdownModal(page, headingText) {
  const modal = page.getByTestId('document-preview-modal');
  await expect(modal).toBeVisible({ timeout: 30_000 });
  await expect(modal.locator('h1')).toContainText(headingText);
  // Should render markdown, not raw "# heading" text line.
  await expect(modal.getByText(`# ${headingText}`, { exact: false })).toHaveCount(0);
  await page.keyboard.press('Escape');
  await expect(modal).toBeHidden({ timeout: 10_000 });
}

adminTest('unified preview renders markdown in 4 entries @regression @preview', async ({ page }) => {
  const filename = 'demo.md';
  const ragflowDatasetId = 'ds1';
  const ragflowDocId = 'doc1';
  const knowledgeDocId = 'k1';
  const mdText = '# 一级标题\n- 行1\n';

  await page.route('**/api/datasets', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ datasets: [{ id: ragflowDatasetId, name: 'kb-one' }] }) });
  });
  await page.route('**/api/ragflow/documents?*', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ documents: [{ id: ragflowDocId, name: filename, status: 'ok' }] }) });
  });
  await page.route('**/api/search', async (route) => {
    if (route.request().method() !== 'POST') return route.fallback();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        chunks: [{ id: 'c1', content: 'md chunk', dataset_id: ragflowDatasetId, doc_id: ragflowDocId, doc_name: filename }],
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
      body: JSON.stringify({ documents: [{ doc_id: knowledgeDocId, filename, status: 'pending', uploaded_at_ms: Date.now(), kb_id: ragflowDatasetId, uploaded_by: 'u1' }] }),
    });
  });
  await page.route('**/api/chats/my', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ chats: [{ id: 'chat1', name: 'chat-1' }] }) });
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
            messages: [{ role: 'assistant', content: '引用 [ID:1]', sources: [{}, { doc_id: ragflowDocId, dataset_id: ragflowDatasetId, doc_name: filename, chunk: mdText }] }],
          },
        ],
      }),
    });
  });
  await page.route(`**/api/preview/documents/ragflow/${ragflowDocId}/preview?*`, async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ type: 'text', filename, content: mdText }) });
  });
  await page.route(`**/api/preview/documents/knowledge/${knowledgeDocId}/preview**`, async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ type: 'text', filename, content: mdText }) });
  });

  await page.goto('/browser');
  await page.getByTestId(`browser-dataset-toggle-${ragflowDatasetId}`).click();
  await page.getByTestId(`browser-doc-view-${ragflowDatasetId}-${ragflowDocId}`).click();
  await openAssertMarkdownModal(page, '一级标题');

  await page.goto('/agents');
  await page.getByPlaceholder(/搜索|关键/).fill('md');
  await page.getByRole('button', { name: /搜索/ }).click();
  await page.getByTestId(`agents-doc-view-${ragflowDatasetId}-${ragflowDocId}`).click();
  await openAssertMarkdownModal(page, '一级标题');

  await page.goto('/documents');
  await page.getByTestId(`docs-preview-${knowledgeDocId}`).click();
  await openAssertMarkdownModal(page, '一级标题');

  await page.goto('/chat');
  await page.getByTestId('chat-source-view-1').click();
  await openAssertMarkdownModal(page, '一级标题');
});

