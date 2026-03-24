// @ts-check
const { expect } = require('@playwright/test');
const { adminTest, viewerTest } = require('../helpers/auth');

adminTest('package drawing tool: query and import flow @regression @tools', async ({ page }) => {
  await page.route('**/api/package-drawing/by-model**', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    const url = route.request().url();
    const model = new URL(url).searchParams.get('model');
    if (model !== 'MD-001') {
      return route.fulfill({
        status: 404,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'model_not_found' }),
      });
    }
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        model: 'MD-001',
        barcode: '6901234567890',
        parameters: {
          材质: 'PE',
          规格: '120x80',
        },
        images: [
          {
            type: 'url',
            url: 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8Xw8AAoMBgQpV6fMAAAAASUVORK5CYII=',
          },
        ],
      }),
    });
  });

  await page.route('**/api/package-drawing/import', async (route) => {
    if (route.request().method() !== 'POST') return route.fallback();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        filename: 'sample.xlsx',
        rows_scanned: 3,
        total: 2,
        success: 2,
        failed: 0,
        errors: [],
      }),
    });
  });

  await page.goto('/tools/package-drawing');
  await expect(page.getByTestId('package-drawing-page')).toBeVisible();
  await expect(page.getByTestId('package-drawing-tab-query')).toBeVisible();
  await expect(page.getByTestId('package-drawing-tab-import')).toBeVisible();

  await page.getByTestId('package-drawing-query-model').fill('MD-001');
  await page.getByTestId('package-drawing-query-submit').click();
  await expect(page.getByTestId('package-drawing-query-result')).toContainText('MD-001');
  await expect(page.getByTestId('package-drawing-image-list').locator('img')).toHaveCount(1);

  await page.getByTestId('package-drawing-tab-import').click();
  await page.getByTestId('package-drawing-import-file').setInputFiles({
    name: 'sample.xlsx',
    mimeType: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    buffer: Buffer.from('mock-xlsx'),
  });
  await page.getByTestId('package-drawing-import-submit').click();
  await expect(page.getByTestId('package-drawing-import-summary')).toContainText('成功：2');
});

viewerTest('package drawing tool: viewer can query but cannot import @regression @rbac @tools', async ({ page }) => {
  await page.route('**/api/package-drawing/by-model**', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    await route.fulfill({
      status: 404,
      contentType: 'application/json',
      body: JSON.stringify({ detail: 'model_not_found' }),
    });
  });

  await page.goto('/tools/package-drawing');
  await expect(page.getByTestId('package-drawing-page')).toBeVisible();
  await expect(page.getByTestId('package-drawing-tab-import')).toHaveCount(0);
});
