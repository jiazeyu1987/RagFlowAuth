// @ts-check
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { expect } = require('@playwright/test');
const { adminTest } = require('../helpers/auth');

adminTest('upload submit is disabled when no file selected (mock) @regression @upload', async ({ page }) => {
  await page.route('**/api/datasets', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ datasets: [{ id: 'ds1', name: 'kb-one' }], count: 1 }),
    });
  });

  await page.goto('/upload');
  await expect(page.getByTestId('upload-submit')).toBeDisabled();
  await expect(page.getByTestId('upload-error')).toHaveCount(0);
});

adminTest('upload accepts files larger than 16MB (mock) @regression @upload', async ({ page }) => {
  let uploadCalled = false;

  await page.route('**/api/datasets', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ datasets: [{ id: 'ds1', name: 'kb-one' }], count: 1 }),
    });
  });

  await page.route('**/api/documents/knowledge/upload?*', async (route) => {
    if (route.request().method() !== 'POST') return route.fallback();
    uploadCalled = true;
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ filename: 'big.txt', doc_id: 'd_big' }),
    });
  });

  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'ragflowauth-e2e-'));
  const filePath = path.join(tmpDir, `big_${Date.now()}.txt`);
  try {
    fs.writeFileSync(filePath, Buffer.alloc(16 * 1024 * 1024 + 1, 0x61));

    await page.goto('/upload');
    await page.getByTestId('upload-file-input').setInputFiles(filePath);
    await expect(page.getByTestId('upload-submit')).toBeEnabled();
    await page.getByTestId('upload-submit').click();
    await expect(page.getByTestId('upload-success')).toBeVisible();
    expect(uploadCalled).toBe(true);
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
    { id: 'ds1', name: 'kb-one' },
    { id: 'ds2', name: 'kb-two' },
  ];

  let capturedKbId = null;

  await page.route('**/api/datasets', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ datasets, count: datasets.length }) });
  });

  await page.route('**/api/documents/knowledge/upload?*', async (route) => {
    if (route.request().method() !== 'POST') return route.fallback();
    const url = new URL(route.request().url());
    capturedKbId = url.searchParams.get('kb_id');
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ filename: 'hello.txt', doc_id: 'd1' }) });
  });

  await page.goto('/upload');
  await page.getByTestId('upload-kb-select').selectOption('kb-two');

  const projectRoot = path.resolve(__dirname, '..', '..');
  const filePath = path.join(projectRoot, 'e2e', 'fixtures', 'files', 'hello.txt');
  await page.getByTestId('upload-file-input').setInputFiles(filePath);
  await page.getByTestId('upload-submit').click();

  expect(capturedKbId).toBe('kb-two');
  await expect(page.getByTestId('upload-success')).toBeVisible();
  await expect(page).toHaveURL(/\/documents/, { timeout: 15_000 });
});

adminTest('upload kb selector shows hierarchical dataset path (mock) @regression @upload', async ({ page }) => {
  const datasets = [
    { id: 'ds_root', name: 'kb-root' },
    { id: 'ds_nested', name: 'kb-guidewire' },
  ];

  let capturedKbId = null;

  await page.route('**/api/datasets', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ datasets, count: datasets.length }) });
  });

  await page.route('**/api/knowledge/directories', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        nodes: [
          { id: 'n1', name: 'clinical', parent_id: null, path: '/clinical' },
          { id: 'n2', name: 'intervention', parent_id: 'n1', path: '/clinical/intervention' },
        ],
        datasets: [
          { id: 'ds_root', name: 'kb-root', node_id: null, node_path: '/' },
          { id: 'ds_nested', name: 'kb-guidewire', node_id: 'n2', node_path: '/clinical/intervention' },
        ],
      }),
    });
  });

  await page.route('**/api/documents/knowledge/upload?*', async (route) => {
    if (route.request().method() !== 'POST') return route.fallback();
    const url = new URL(route.request().url());
    capturedKbId = url.searchParams.get('kb_id');
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ filename: 'hello.txt', doc_id: 'd1' }) });
  });

  await page.goto('/upload');
  await expect(page.getByTestId('upload-kb-select')).toContainText('/clinical/intervention/kb-guidewire');

  await page.getByTestId('upload-kb-select').selectOption('kb-guidewire');

  const projectRoot = path.resolve(__dirname, '..', '..');
  const filePath = path.join(projectRoot, 'e2e', 'fixtures', 'files', 'hello.txt');
  await page.getByTestId('upload-file-input').setInputFiles(filePath);
  await page.getByTestId('upload-submit').click();

  expect(capturedKbId).toBe('kb-guidewire');
});

