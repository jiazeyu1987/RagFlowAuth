// @ts-check
const { expect } = require('@playwright/test');
const { adminTest, mockAuthMe, viewerTest } = require('../helpers/auth');
const { mockJson } = require('../helpers/mock');

const baseConfig = {
  positions: [
    {
      id: 1,
      name: 'QA',
      in_signoff: true,
      in_compiler: false,
      in_approver: false,
      seeded_from_json: true,
      assigned_users: [],
    },
  ],
  file_categories: [
    { id: 101, name: '产品技术要求', seeded_from_json: true, is_active: true },
  ],
};

async function mockPageBootstrap(page, authOverrides = {}) {
  await mockAuthMe(page, authOverrides);
  await mockJson(page, '**/api/inbox**', { items: [], total: 0, unread_count: 0 });
  await mockJson(page, '**/api/admin/quality-system-config', baseConfig);
}

adminTest('admin can open quality system config from navigation @regression @admin', async ({ page }) => {
  await mockPageBootstrap(page);

  await page.goto('/chat');
  await expect(page.getByTestId('nav-quality-system-config')).toBeVisible();
  await page.getByTestId('nav-quality-system-config').click();

  await expect(page).toHaveURL(/\/quality-system-config$/);
  await expect(page.getByTestId('quality-system-config-page')).toBeVisible();
  await expect(page.getByTestId('quality-system-config-tab-positions')).toBeVisible();
  await expect(page.getByTestId('quality-system-config-tab-categories')).toBeVisible();
});

viewerTest('non-admin cannot see quality system config navigation or access page @regression @rbac', async ({ page }) => {
  await mockPageBootstrap(page, {
    role: 'viewer',
    capabilities: {
      users: { manage: { scope: 'none', targets: [] } },
    },
  });

  await page.goto('/chat');
  await expect(page.getByTestId('nav-quality-system-config')).toHaveCount(0);

  await page.goto('/quality-system-config');
  await expect(page).toHaveURL(/\/unauthorized$|\/chat$|\/login$/);
});
