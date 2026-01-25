// @ts-check
const { expect } = require('@playwright/test');
const { adminTest } = require('../helpers/auth');
const { mockJson } = require('../helpers/mock');

adminTest('users list client-side filters work @regression @admin', async ({ page }) => {
  const groups = [
    { group_id: 101, group_name: 'viewer', description: 'viewer' },
    { group_id: 102, group_name: 'uploader', description: 'uploader' },
  ];

  const createdA = new Date('2026-01-10T12:00:00Z').getTime();
  const createdB = new Date('2026-01-20T12:00:00Z').getTime();
  const createdC = new Date('2025-12-20T12:00:00Z').getTime();

  const users = [
    {
      user_id: 'u_a',
      username: 'alice',
      email: 'alice@example.com',
      company_id: 1,
      company_name: 'E2E鍏徃A',
      department_id: 10,
      department_name: 'E2E閮ㄩ棬10',
      role: 'viewer',
      status: 'active',
      group_id: null,
      group_ids: [101],
      group_name: null,
      permission_groups: [{ group_id: 101, group_name: 'viewer' }],
      created_at_ms: createdA,
      last_login_at_ms: null,
    },
    {
      user_id: 'u_b',
      username: 'bob',
      email: 'bob@example.com',
      company_id: 2,
      company_name: 'E2E鍏徃B',
      department_id: 20,
      department_name: 'E2E閮ㄩ棬20',
      role: 'viewer',
      status: 'inactive',
      group_id: null,
      group_ids: [102],
      group_name: null,
      permission_groups: [{ group_id: 102, group_name: 'uploader' }],
      created_at_ms: createdB,
      last_login_at_ms: null,
    },
    {
      user_id: 'u_c',
      username: 'carol',
      email: 'carol@example.com',
      company_id: 1,
      company_name: 'E2E鍏徃A',
      department_id: 20,
      department_name: 'E2E閮ㄩ棬20',
      role: 'viewer',
      status: 'active',
      group_id: null,
      group_ids: [],
      group_name: null,
      permission_groups: [],
      created_at_ms: createdC,
      last_login_at_ms: null,
    },
  ];

  await page.route('**/api/users**', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(users) });
  });

  await mockJson(page, '**/api/permission-groups', { ok: true, data: groups });
  await mockJson(page, '**/api/org/companies', [
    { id: 1, name: 'E2E鍏徃A' },
    { id: 2, name: 'E2E鍏徃B' },
  ]);
  await mockJson(page, '**/api/org/departments', [
    { id: 10, name: 'E2E閮ㄩ棬10' },
    { id: 20, name: 'E2E閮ㄩ棬20' },
  ]);

  await page.goto('/users');

  await expect(page.getByTestId('users-row-u_a')).toBeVisible();
  await expect(page.getByTestId('users-row-u_b')).toBeVisible();
  await expect(page.getByTestId('users-row-u_c')).toBeVisible();

  await page.getByTestId('users-filter-company').selectOption('1');
  await expect(page.getByTestId('users-row-u_b')).toHaveCount(0);
  await expect(page.getByTestId('users-row-u_a')).toBeVisible();
  await expect(page.getByTestId('users-row-u_c')).toBeVisible();

  await page.getByTestId('users-filter-department').selectOption('10');
  await expect(page.getByTestId('users-row-u_c')).toHaveCount(0);
  await expect(page.getByTestId('users-row-u_a')).toBeVisible();

  await page.getByTestId('users-filter-reset').click();
  await expect(page.getByTestId('users-row-u_a')).toBeVisible();
  await expect(page.getByTestId('users-row-u_b')).toBeVisible();
  await expect(page.getByTestId('users-row-u_c')).toBeVisible();

  await page.getByTestId('users-filter-status').selectOption('inactive');
  await expect(page.getByTestId('users-row-u_a')).toHaveCount(0);
  await expect(page.getByTestId('users-row-u_c')).toHaveCount(0);
  await expect(page.getByTestId('users-row-u_b')).toBeVisible();

  await page.getByTestId('users-filter-reset').click();
  await page.getByTestId('users-filter-group').selectOption('101');
  await expect(page.getByTestId('users-row-u_b')).toHaveCount(0);
  await expect(page.getByTestId('users-row-u_c')).toHaveCount(0);
  await expect(page.getByTestId('users-row-u_a')).toBeVisible();

  await page.getByTestId('users-filter-reset').click();
  await page.getByTestId('users-filter-q').fill('car');
  await expect(page.getByTestId('users-row-u_a')).toHaveCount(0);
  await expect(page.getByTestId('users-row-u_b')).toHaveCount(0);
  await expect(page.getByTestId('users-row-u_c')).toBeVisible();

  await page.getByTestId('users-filter-reset').click();
  await page.getByTestId('users-filter-created-from').fill('2026-01-01');
  await page.getByTestId('users-filter-created-to').fill('2026-01-31');
  await expect(page.getByTestId('users-row-u_c')).toHaveCount(0);
  await expect(page.getByTestId('users-row-u_a')).toBeVisible();
  await expect(page.getByTestId('users-row-u_b')).toBeVisible();
});

