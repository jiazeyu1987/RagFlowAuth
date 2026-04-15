// @ts-check
const { test, expect, request } = require('@playwright/test');
const { FRONTEND_BASE_URL, BACKEND_BASE_URL, preflightAdmin, uiLogin, ADMIN_USER } = require('../helpers/integration');

test('quality system file category create/deactivate persists and appears in audit logs @integration', async ({ page }) => {
  test.setTimeout(120_000);

  const pre = await preflightAdmin();
  if (!pre.ok) test.skip(true, pre.reason);

  const api = await request.newContext({ baseURL: BACKEND_BASE_URL });
  const headers = { Authorization: `Bearer ${pre.tokens.access_token}` };
  const categoryName = `E2E文件小类_${Date.now()}_${Math.random().toString(16).slice(2, 8)}`;
  let categoryId = null;

  try {
    await uiLogin(page);

    await page.goto(`${FRONTEND_BASE_URL}/quality-system-config`);
    await page.getByTestId('quality-system-config-tab-categories').click();
    await page.getByTestId('quality-system-config-category-input').fill(categoryName);

    page.once('dialog', async (dialog) => {
      expect(dialog.type()).toBe('prompt');
      await dialog.accept('Integration category create');
    });
    await page.getByTestId('quality-system-config-category-add').click();
    await expect(page.getByText(categoryName, { exact: true })).toBeVisible();

    const configResp = await api.get('/api/admin/quality-system-config', { headers });
    if (!configResp.ok()) {
      throw new Error(`load config failed: ${configResp.status()}`);
    }
    const configJson = await configResp.json();
    categoryId = configJson.file_categories.find((item) => item.name === categoryName)?.id ?? null;
    if (categoryId == null) test.fail(true, 'created category id not found');

    await page.reload();
    await page.getByTestId('quality-system-config-tab-categories').click();
    await expect(page.getByText(categoryName, { exact: true })).toBeVisible();

    let dialogIndex = 0;
    const dialogHandler = async (dialog) => {
      dialogIndex += 1;
      if (dialogIndex === 1) {
        expect(dialog.type()).toBe('confirm');
        await dialog.accept();
        return;
      }
      expect(dialog.type()).toBe('prompt');
      await dialog.accept('Integration category deactivate');
      page.off('dialog', dialogHandler);
    };
    page.on('dialog', dialogHandler);
    await page.getByTestId(`quality-system-config-category-remove-${categoryId}`).click();
    await expect(page.getByText(categoryName, { exact: true })).toHaveCount(0);

    await page.reload();
    await page.getByTestId('quality-system-config-tab-categories').click();
    await expect(page.getByText(categoryName, { exact: true })).toHaveCount(0);

    await page.goto(`${FRONTEND_BASE_URL}/logs`);
    await expect(page.getByTestId('audit-logs-page')).toBeVisible();
    await page.getByTestId('audit-filter-source').selectOption('quality_system_config');
    await page.getByTestId('audit-filter-username').fill(ADMIN_USER);
    await page.getByTestId('audit-filter-resource-id').fill(categoryName);
    await page.getByTestId('audit-apply').click();

    await expect(page.getByTestId('audit-total')).not.toHaveText('0', { timeout: 30_000 });
    await expect(page.getByTestId('audit-table')).toContainText(categoryName);
    await expect(page.getByTestId('audit-table')).toContainText('体系配置');

    await page.getByTestId('audit-filter-action').selectOption('quality_system_file_category_create');
    await page.getByTestId('audit-apply').click();
    await expect(page.getByTestId('audit-table')).toContainText('新增体系文件小类');

    await page.getByTestId('audit-filter-action').selectOption('quality_system_file_category_deactivate');
    await page.getByTestId('audit-apply').click();
    await expect(page.getByTestId('audit-table')).toContainText('停用体系文件小类');
  } finally {
    if (categoryId != null) {
      await api.post(`/api/admin/quality-system-config/file-categories/${categoryId}/deactivate`, {
        headers,
        data: { change_reason: 'E2E cleanup' },
      });
    }
    await api.dispose();
  }
});
