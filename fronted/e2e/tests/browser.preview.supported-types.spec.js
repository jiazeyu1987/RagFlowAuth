// @ts-check
const { test, expect } = require('@playwright/test');
const { adminStorageStatePath } = require('../helpers/auth');

test.use({ storageState: adminStorageStatePath });

test('browser preview supports md/pdf/docx/xlsx/xls/csv/txt @regression @browser @preview', async ({ page }) => {
  await page.route('**/api/auth/me', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        user_id: 'u_admin_no_download',
        username: 'viewer_no_download',
        role: 'viewer',
        status: 'active',
        permissions: { can_upload: false, can_review: false, can_download: false, can_delete: false },
      }),
    });
  });
  await page.route('**/api/me/kbs', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ kb_ids: ['ds1'] }) });
  });
  await page.route('**/api/auth/refresh', async (route) => {
    if (route.request().method() !== 'POST') return route.fallback();
    return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ access_token: 'e2e_access_token', token_type: 'bearer' }) });
  });

  await page.route('**/api/datasets', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ datasets: [{ id: 'ds1', name: 'kb-one' }] }),
    });
  });

  await page.route('**/api/ragflow/documents?*', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        documents: [
          { id: 'md1', name: 'a.md', created_at: '2025-01-01' },
          { id: 'pdf1', name: 'b.pdf', created_at: '2025-01-01' },
          { id: 'docx1', name: 'c.docx', created_at: '2025-01-01' },
          { id: 'xlsx1', name: 'd.xlsx', created_at: '2025-01-01' },
          { id: 'xls1', name: 'e.xls', created_at: '2025-01-01' },
          { id: 'csv1', name: 'f.csv', created_at: '2025-01-01' },
          { id: 'txt1', name: 'g.txt', created_at: '2025-01-01' },
        ],
      }),
    });
  });

  const previewPayloadById = {
    md1: { type: 'text', filename: 'a.md', content: '# M1\n- item' },
    pdf1: { type: 'pdf', filename: 'b.pdf', content: 'JVBERi0xLjQKJSBtb2NrIHBkZg==' },
    docx1: { type: 'docx', filename: 'c.docx', html: '<h2>DocxTitle</h2><p>DocxBody</p>' },
    xlsx1: { type: 'excel', filename: 'd.xlsx', sheets: { Sheet1: '<table><tbody><tr><td>X1</td></tr></tbody></table>' } },
    xls1: { type: 'excel', filename: 'e.xls', sheets: { Sheet1: '<table><tbody><tr><td>X2</td></tr></tbody></table>' } },
    csv1: { type: 'text', filename: 'f.csv', content: 'A,B\n1,2\n' },
    txt1: { type: 'text', filename: 'g.txt', content: 'plain text line' },
  };
  await page.route('**/api/preview/documents/ragflow/*/preview?*', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    const parts = new URL(route.request().url()).pathname.split('/');
    const docId = parts[parts.length - 2];
    const payload = previewPayloadById[docId] || { type: 'text', filename: 'unknown.txt', content: 'unknown' };
    return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(payload) });
  });

  await page.goto('/browser');
  await page.getByTestId('browser-dataset-toggle-ds1').click();

  const openAndClose = async (docId, assertFn) => {
    await page.getByTestId(`browser-doc-view-ds1-${docId}`).click();
    const modal = page.getByTestId('document-preview-modal');
    await expect(modal).toBeVisible();
    await assertFn(modal);
    await page.keyboard.press('Escape');
    await expect(modal).toBeHidden();
  };

  await openAndClose('md1', async (modal) => expect(modal.locator('h1')).toContainText('M1'));
  await openAndClose('pdf1', async (modal) => expect(modal.locator('iframe[title="pdf-preview"]')).toBeVisible());
  await openAndClose('docx1', async (modal) => expect(modal).toContainText('DocxTitle'));
  await openAndClose('xlsx1', async (modal) => expect(modal.getByText('X1')).toBeVisible());
  await openAndClose('xls1', async (modal) => expect(modal.getByText('X2')).toBeVisible());
  await openAndClose('csv1', async (modal) => expect(modal.locator('table')).toBeVisible());
  await openAndClose('txt1', async (modal) => expect(modal.getByText('plain text line')).toBeVisible());
});
