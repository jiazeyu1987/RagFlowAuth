// @ts-check
const { expect } = require('@playwright/test');
const { adminTest } = require('../helpers/auth');

adminTest('agents supports multi-kb search params and unified preview for md/pdf/docx @regression @agents @preview', async ({ page }) => {
  await page.route('**/api/auth/me', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        user_id: 'u_viewer_no_download',
        username: 'viewer',
        role: 'viewer',
        status: 'active',
        permissions: { can_upload: false, can_review: false, can_download: false, can_delete: false },
      }),
    });
  });
  await page.route('**/api/me/kbs', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ kb_ids: ['ds1', 'ds2'] }) });
  });

  const datasets = [
    { id: 'ds1', name: 'kb-hall' },
    { id: 'ds2', name: 'kb-research' },
  ];

  await page.route('**/api/datasets', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ datasets, count: datasets.length }),
    });
  });

  let capturedBody = null;
  await page.route('**/api/search**', async (route) => {
    if (route.request().method() !== 'POST') return route.fallback();
    capturedBody = route.request().postDataJSON();
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        chunks: [
          { id: 'c1', content: '# Title\n- A', dataset_id: 'ds1', doc_id: 'md1', doc_name: 'a.md', similarity: 0.9 },
          { id: 'c2', content: 'pdf chunk', dataset_id: 'ds2', doc_id: 'pdf1', doc_name: 'b.pdf', similarity: 0.8 },
          { id: 'c3', content: 'docx chunk', dataset_id: 'ds2', doc_id: 'docx1', doc_name: 'c.docx', similarity: 0.7 },
        ],
        total: 3,
        page: 1,
        page_size: 30,
      }),
    });
  });

  await page.route('**/api/preview/documents/ragflow/md1/preview?*', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ type: 'text', filename: 'a.md', content: '# Title\n- A' }),
    });
  });
  await page.route('**/api/preview/documents/ragflow/pdf1/preview?*', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ type: 'pdf', filename: 'b.pdf', content: 'JVBERi0xLjQKJSBtb2NrIHBkZg==' }),
    });
  });
  await page.route('**/api/preview/documents/ragflow/docx1/preview?*', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ type: 'docx', filename: 'c.docx', html: '<h2>DocxTitle</h2><p>DocxBody</p>' }),
    });
  });

  await page.goto('/agents');
  await page.getByPlaceholder(/搜索|关键|问题/).fill('医疗');
  await page.locator('input[type="range"]').first().fill('0.35');
  await page.getByRole('button', { name: /搜索/ }).click();

  expect(capturedBody).toBeTruthy();
  expect(Array.isArray(capturedBody.dataset_ids)).toBeTruthy();
  expect(new Set(capturedBody.dataset_ids)).toEqual(new Set(['ds1', 'ds2']));
  expect(Number(capturedBody.similarity_threshold)).toBeCloseTo(0.35, 2);

  await page.getByTestId('agents-doc-view-ds1-md1').click();
  let modal = page.getByTestId('document-preview-modal');
  await expect(modal).toContainText('a.md');
  await expect(modal.locator('h1')).toContainText('Title');
  await page.keyboard.press('Escape');
  await expect(modal).toBeHidden();

  await page.getByTestId('agents-doc-view-ds2-pdf1').click();
  modal = page.getByTestId('document-preview-modal');
  await expect(modal).toContainText('b.pdf');
  await expect(modal.locator('iframe[title="pdf-preview"]')).toBeVisible();
  await page.keyboard.press('Escape');

  await page.getByTestId('agents-doc-view-ds2-docx1').click();
  modal = page.getByTestId('document-preview-modal');
  await expect(modal).toContainText('c.docx');
  await expect(modal.getByText('DocxTitle')).toBeVisible();
});
