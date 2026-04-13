// @ts-check
const { expect } = require('@playwright/test');
const { realAdminTest } = require('../helpers/auth');
const { mockJson } = require('../helpers/mock');

realAdminTest('admin create-sub-admin modal hides other sub-admin occupied knowledge roots @regression @admin', async ({ page }) => {
  await page.route('**/api/users**', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([
        {
          user_id: 'sub-occupied',
          username: 'sub_admin_a',
          full_name: 'Sub Admin A',
          role: 'sub_admin',
          status: 'active',
          company_id: 1,
          department_id: 10,
          managed_kb_root_node_id: 'node-owned',
          managed_kb_root_path: '/Root A/Owned',
        },
      ]),
    });
  });

  await mockJson(page, '**/api/permission-groups**', []);
  await mockJson(page, '**/api/org/companies', [{ id: 1, name: 'E2E Company' }]);
  await mockJson(page, '**/api/org/departments', [
    { id: 10, company_id: 1, name: 'QA', path_name: 'E2E Company / QA' },
  ]);
  await mockJson(page, '**/api/org/tree', [
    {
      id: 1,
      node_type: 'company',
      name: 'E2E Company',
      children: [
        {
          id: 10,
          node_type: 'department',
          name: 'QA',
          path_name: 'E2E Company / QA',
          children: [
            {
              id: 1001,
              node_type: 'person',
              name: 'Alice',
              employee_user_id: 'alice-001',
              company_id: 1,
              department_id: 10,
              children: [],
            },
          ],
        },
      ],
    },
  ]);
  await page.route('**/api/knowledge/directories?company_id=1', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        nodes: [
          { id: 'node-root-a', name: 'Root A', parent_id: '', path: '/Root A' },
          { id: 'node-owned', name: 'Owned', parent_id: 'node-root-a', path: '/Root A/Owned' },
          { id: 'node-free', name: 'Free', parent_id: 'node-root-a', path: '/Root A/Free' },
          { id: 'node-root-b', name: 'Root B', parent_id: '', path: '/Root B' },
        ],
        datasets: [],
        bindings: {},
      }),
    });
  });

  await page.goto('/users');
  await page.getByTestId('users-create-open').click();

  const fullNameInput = page.getByTestId('users-create-full-name');
  await fullNameInput.click();
  await fullNameInput.fill('Alice');
  await page.getByTestId('users-create-full-name-result-alice-001').click();
  await page.getByTestId('users-create-user-type').selectOption('sub_admin');

  await expect(page.getByTestId('users-kb-root-selector')).toBeVisible();
  await expect(page.getByTestId('users-kb-root-node-node-root-a')).toBeDisabled();
  await expect(page.getByTestId('users-kb-root-node-node-root-b')).toBeVisible();
  await expect(page.getByTestId('users-kb-root-node-node-owned')).toHaveCount(0);

  await page.getByTestId('users-kb-root-toggle-node-root-a').click();

  await expect(page.getByTestId('users-kb-root-node-node-free')).toBeVisible();
  await expect(page.getByTestId('users-kb-root-node-node-free')).toBeEnabled();
  await expect(page.getByTestId('users-kb-root-node-node-owned')).toHaveCount(0);
});
