// @ts-check
const { expect } = require('@playwright/test');
const { adminTest } = require('../helpers/auth');

adminTest('upload allowed extensions save sends change_reason @regression @admin', async ({ page }) => {
  let capturedPut = null;

  await page.route('**/api/datasets', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ datasets: [{ id: 'ds-a', name: 'kb-a' }], count: 1 }),
    });
  });

  await page.route('**/api/knowledge/settings/allowed-extensions', async (route) => {
    if (route.request().method() === 'GET') {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ allowed_extensions: ['.pdf', '.txt'], updated_at_ms: 1 }),
      });
    }
    if (route.request().method() === 'PUT') {
      capturedPut = route.request().postDataJSON();
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          allowed_extensions: capturedPut.allowed_extensions,
          updated_at_ms: 2,
        }),
      });
    }
    return route.fallback();
  });

  await page.goto('/upload');
  await page.getByPlaceholder('输入后缀，例如 .dwg 或 dwg').fill('.dwg');
  await page.getByRole('button', { name: '添加后缀' }).click();

  page.once('dialog', async (dialog) => {
    expect(dialog.type()).toBe('prompt');
    await dialog.accept('Allow CAD drawing uploads');
  });
  await page.getByRole('button', { name: '保存配置' }).click();

  expect(capturedPut).toBeTruthy();
  expect(capturedPut.allowed_extensions).toContain('.dwg');
  expect(capturedPut.change_reason).toBe('Allow CAD drawing uploads');
  await expect(page.getByText('文件后缀配置已保存并记录变更原因')).toBeVisible();
});
