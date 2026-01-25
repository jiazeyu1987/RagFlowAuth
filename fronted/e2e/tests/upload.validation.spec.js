// @ts-check
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { expect } = require('@playwright/test');
const { adminTest } = require('../helpers/auth');

adminTest('upload submit with no file shows validation error (mock) @regression @upload', async ({ page }) => {
  await page.route('**/api/datasets', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ datasets: [{ id: 'ds1', name: '灞曞巺' }], count: 1 }),
    });
  });

  await page.goto('/upload');

  // UI prevents normal click (button disabled), but we still validate the guard in handler.
  await page.locator('form').dispatchEvent('submit');
  await expect(page.getByTestId('upload-error')).toBeVisible();
  await expect(page.getByTestId('upload-error')).toContainText('请选择文件');
});

adminTest('upload rejects files larger than 16MB (mock) @regression @upload', async ({ page }) => {
  await page.route('**/api/datasets', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ datasets: [{ id: 'ds1', name: '灞曞巺' }], count: 1 }),
    });
  });

  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'ragflowauth-e2e-'));
  const filePath = path.join(tmpDir, `big_${Date.now()}.txt`);
  try {
    fs.writeFileSync(filePath, Buffer.alloc(16 * 1024 * 1024 + 1, 0x61));

    await page.goto('/upload');
    await page.getByTestId('upload-file-input').setInputFiles(filePath);

    await expect(page.getByTestId('upload-error')).toBeVisible();
    await expect(page.getByTestId('upload-error')).toContainText('16MB');
  } finally {
    try {
      fs.rmSync(tmpDir, { recursive: true, force: true });
    } catch {
      // ignore
    }
  }
});

adminTest('upload datasets 500 shows error banner (mock) @regression @upload', async ({ page }) => {
  await page.route('**/api/datasets', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    await route.fulfill({ status: 500, contentType: 'application/json', body: JSON.stringify({ detail: 'datasets failed' }) });
  });

  await page.goto('/upload');
  await expect(page.getByTestId('upload-error')).toBeVisible();
});

adminTest('upload datasets network timeout shows error banner (mock) @regression @upload', async ({ page }) => {
  await page.route('**/api/datasets', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    await route.abort('timedout');
  });

  await page.goto('/upload');
  await expect(page.getByTestId('upload-error')).toBeVisible();
});

adminTest('upload uses selected kb_id in request query (mock) @regression @upload', async ({ page }) => {
  const datasets = [
    { id: 'ds1', name: '灞曞巺' },
    { id: 'ds2', name: '第二库' },
  ];

  let capturedKbId = null;

  await page.route('**/api/datasets', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ datasets, count: datasets.length }) });
  });

  await page.route('**/api/knowledge/upload?*', async (route) => {
    if (route.request().method() !== 'POST') return route.fallback();
    const url = new URL(route.request().url());
    capturedKbId = url.searchParams.get('kb_id');
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ filename: 'hello.txt' }) });
  });

  await page.goto('/upload');

  await page.getByTestId('upload-kb-select').selectOption('第二库');

  const projectRoot = path.resolve(__dirname, '..', '..');
  const filePath = path.join(projectRoot, 'e2e', 'fixtures', 'files', 'hello.txt');
  await page.getByTestId('upload-file-input').setInputFiles(filePath);
  await page.getByTestId('upload-submit').click();

  expect(capturedKbId).toBe('第二库');

  await expect(page.getByTestId('upload-success')).toBeVisible();
  await expect(page).toHaveURL(/\/documents/, { timeout: 10_000 });
});
