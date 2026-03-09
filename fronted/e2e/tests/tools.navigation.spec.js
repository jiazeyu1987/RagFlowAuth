// @ts-check
const { expect } = require('@playwright/test');
const { adminTest } = require('../helpers/auth');

adminTest('tools navigation: key cards route to target pages @regression @tools', async ({ page }) => {
  await page.route('**/api/nas/files**', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        current_path: '',
        parent_path: null,
        items: [
          {
            name: 'guidewire.txt',
            path: 'docs/guidewire.txt',
            is_dir: false,
            size: 1024,
            modified_at: 1700000000,
          },
        ],
      }),
    });
  });

  await page.route('**/api/datasets', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ datasets: [{ id: 'kb1', name: '展厅聊天' }] }),
    });
  });

  await page.route('**/api/drug-admin/provinces', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        validated_on: '2026-03-08',
        source: 'e2e-mock',
        provinces: [{ name: '国家药监局' }],
      }),
    });
  });

  await page.goto('/tools');

  await expect(page.getByTestId('tool-card-paper_download')).toBeVisible();
  await expect(page.getByTestId('tool-card-patent_download')).toBeVisible();
  await expect(page.getByTestId('tool-card-nas_browser')).toBeVisible();
  await expect(page.getByTestId('tool-card-drug_admin')).toBeVisible();
  await expect(page.getByTestId('tool-card-nmpa')).toBeVisible();

  await page.getByTestId('tool-card-paper_download').click();
  await expect(page).toHaveURL(/\/tools\/paper-download$/);
  await expect(page.getByTestId('paper-download-page')).toBeVisible();

  await page.goto('/tools');
  await page.getByTestId('tool-card-patent_download').click();
  await expect(page).toHaveURL(/\/tools\/patent-download$/);
  await expect(page.getByTestId('patent-download-page')).toBeVisible();

  await page.goto('/tools');
  await page.getByTestId('tool-card-nas_browser').click();
  await expect(page).toHaveURL(/\/tools\/nas-browser$/);
  await expect(page.getByTestId('nas-browser-page')).toBeVisible();

  await page.goto('/tools');
  await page.getByTestId('tool-card-drug_admin').click();
  await expect(page).toHaveURL(/\/tools\/drug-admin$/);
  await expect(page.locator('#drug-admin-province')).toBeVisible();

  await page.goto('/tools');
  await page.getByTestId('tool-card-nmpa').click();
  await expect(page).toHaveURL(/\/tools\/nmpa$/);
  await expect(page.getByTestId('layout-header-title')).toHaveText('NMPA');
});
