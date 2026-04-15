// @ts-check
const { expect } = require('@playwright/test');
const { adminTest, mockAuthMe } = require('../helpers/auth');
const { mockJson } = require('../helpers/mock');

adminTest('quality system config file categories create and deactivate with reasons @regression @admin', async ({ page }) => {
  await mockAuthMe(page);
  await mockJson(page, '**/api/inbox**', { items: [], total: 0, unread_count: 0 });

  const configState = {
    positions: [],
    file_categories: [
      { id: 101, name: '产品技术要求', seeded_from_json: true, is_active: true },
      { id: 102, name: '工艺流程图', seeded_from_json: true, is_active: true },
    ],
  };

  let capturedCreateBody = null;
  let capturedDeactivateBody = null;

  await page.route('**/api/admin/quality-system-config', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(configState) });
  });

  await page.route('**/api/admin/quality-system-config/file-categories', async (route) => {
    if (route.request().method() !== 'POST') return route.fallback();
    capturedCreateBody = route.request().postDataJSON();
    const created = {
      id: 201,
      name: capturedCreateBody.name,
      seeded_from_json: false,
      is_active: true,
    };
    configState.file_categories.push(created);
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(created) });
  });

  await page.route('**/api/admin/quality-system-config/file-categories/101/deactivate', async (route) => {
    if (route.request().method() !== 'POST') return route.fallback();
    capturedDeactivateBody = route.request().postDataJSON();
    configState.file_categories = configState.file_categories.filter((item) => item.id !== 101);
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ id: 101, name: '产品技术要求', seeded_from_json: true, is_active: false }),
    });
  });

  await page.goto('/quality-system-config');
  await page.getByTestId('quality-system-config-tab-categories').click();
  await expect(page.getByTestId('quality-system-config-category-101')).toBeVisible();
  await expect(page.getByTestId('quality-system-config-category-102')).toBeVisible();

  await page.getByTestId('quality-system-config-category-input').fill('新增文件小类');
  page.once('dialog', async (dialog) => {
    expect(dialog.type()).toBe('prompt');
    await dialog.accept('Add custom category');
  });
  await page.getByTestId('quality-system-config-category-add').click();

  expect(capturedCreateBody).toEqual({
    name: '新增文件小类',
    change_reason: 'Add custom category',
  });
  await expect(page.getByTestId('quality-system-config-category-201')).toContainText('新增文件小类');

  let dialogIndex = 0;
  const dialogHandler = async (dialog) => {
    dialogIndex += 1;
    if (dialogIndex === 1) {
      expect(dialog.type()).toBe('confirm');
      await dialog.accept();
      return;
    }
    expect(dialog.type()).toBe('prompt');
    await dialog.accept('Retire seeded category');
    page.off('dialog', dialogHandler);
  };
  page.on('dialog', dialogHandler);
  await page.getByTestId('quality-system-config-category-remove-101').click();

  expect(capturedDeactivateBody).toEqual({ change_reason: 'Retire seeded category' });
  await expect(page.getByTestId('quality-system-config-category-101')).toHaveCount(0);
  await page.reload();
  await expect(page.getByTestId('quality-system-config-category-101')).toHaveCount(0);
});

adminTest('quality system config category dialogs can cancel without submitting @regression @admin', async ({ page }) => {
  await mockAuthMe(page);
  await mockJson(page, '**/api/inbox**', { items: [], total: 0, unread_count: 0 });
  await mockJson(page, '**/api/admin/quality-system-config', {
    positions: [],
    file_categories: [
      { id: 301, name: '标签、合格证', seeded_from_json: true, is_active: true },
    ],
  });

  let createCount = 0;
  let deactivateCount = 0;
  await page.route('**/api/admin/quality-system-config/file-categories', async (route) => {
    if (route.request().method() !== 'POST') return route.fallback();
    createCount += 1;
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({}) });
  });
  await page.route('**/api/admin/quality-system-config/file-categories/301/deactivate', async (route) => {
    if (route.request().method() !== 'POST') return route.fallback();
    deactivateCount += 1;
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({}) });
  });

  await page.goto('/quality-system-config');
  await page.getByTestId('quality-system-config-tab-categories').click();
  await page.getByTestId('quality-system-config-category-input').fill('尝试取消');

  page.once('dialog', async (dialog) => {
    expect(dialog.type()).toBe('prompt');
    await dialog.dismiss();
  });
  await page.getByTestId('quality-system-config-category-add').click();
  expect(createCount).toBe(0);

  page.once('dialog', async (dialog) => {
    expect(dialog.type()).toBe('confirm');
    await dialog.dismiss();
  });
  await page.getByTestId('quality-system-config-category-remove-301').click();
  expect(deactivateCount).toBe(0);
});
