// @ts-check
const { expect } = require('@playwright/test');
const { adminTest, mockAuthMe } = require('../helpers/auth');
const { mockJson } = require('../helpers/mock');

const EXISTING_SUB_ADMIN = {
  user_id: 'sub-admin-1',
  username: 'sub_admin_owner',
  full_name: 'Sub Admin Owner',
  role: 'sub_admin',
  status: 'active',
  company_id: 1,
  department_id: 10,
  managed_kb_root_node_id: 'node-sub-admin-1',
};

const EMPLOYEE_TREE = [
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
            name: '张三',
            employee_user_id: 'emp-zhangsan',
            company_id: 1,
            department_id: 10,
            children: [],
          },
        ],
      },
    ],
  },
];

async function mockUserCreatePage(page, users) {
  await mockAuthMe(page);
  await page.route('**/api/users**', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(users),
    });
  });

  await mockJson(page, '**/api/permission-groups/assignable', { groups: [] });
  await mockJson(page, '**/api/org/companies', [{ id: 1, name: 'E2E Company' }]);
  await mockJson(page, '**/api/org/departments', [
    { id: 10, company_id: 1, name: 'QA', path_name: 'E2E Company / QA' },
  ]);
  await mockJson(page, '**/api/org/tree', EMPLOYEE_TREE);
}

async function selectEmployeeAndManager(page) {
  const fullNameInput = page.getByTestId('users-create-full-name');
  await fullNameInput.click();
  await fullNameInput.fill('张');
  await page.getByTestId('users-create-full-name-result-emp-zhangsan').click();
  await page.getByTestId('users-create-sub-admin').selectOption('sub-admin-1');
}

adminTest('admin create user autofills username from employee pinyin @regression @admin', async ({ page }) => {
  const users = [EXISTING_SUB_ADMIN];
  await mockUserCreatePage(page, users);

  let capturedCreateBody = null;
  await page.route('**/api/users', async (route) => {
    if (route.request().method() !== 'POST') return route.fallback();
    capturedCreateBody = route.request().postDataJSON();
    const createdUser = {
      user_id: 'u-created',
      username: capturedCreateBody.username,
      full_name: capturedCreateBody.full_name,
      employee_user_id: capturedCreateBody.employee_user_id,
      role: capturedCreateBody.role,
      status: 'active',
      company_id: capturedCreateBody.company_id,
      department_id: capturedCreateBody.department_id,
      manager_user_id: capturedCreateBody.manager_user_id,
    };
    users.unshift(createdUser);
    await route.fulfill({
      status: 201,
      contentType: 'application/json',
      body: JSON.stringify({ user: createdUser }),
    });
  });

  await page.goto('/users');
  await page.getByTestId('users-create-open').click();

  await selectEmployeeAndManager(page);

  await expect(page.getByTestId('users-create-username')).toHaveValue('zhangsan');
  await page.getByTestId('users-create-submit').click();

  await expect.poll(() => capturedCreateBody).toBeTruthy();
  expect(capturedCreateBody).toMatchObject({
    username: 'zhangsan',
    full_name: '张三',
    employee_user_id: 'emp-zhangsan',
    company_id: 1,
    department_id: 10,
    manager_user_id: 'sub-admin-1',
    role: 'viewer',
  });
  await expect(page.getByTestId('users-create-form')).toHaveCount(0);
});

adminTest('admin create user keeps auto-generated pinyin on duplicate error without suffixing @regression @admin', async ({ page }) => {
  const users = [EXISTING_SUB_ADMIN];
  await mockUserCreatePage(page, users);

  let capturedCreateBody = null;
  await page.route('**/api/users', async (route) => {
    if (route.request().method() !== 'POST') return route.fallback();
    capturedCreateBody = route.request().postDataJSON();
    await route.fulfill({
      status: 409,
      contentType: 'application/json',
      body: JSON.stringify({ detail: 'username_already_exists' }),
    });
  });

  await page.goto('/users');
  await page.getByTestId('users-create-open').click();

  await selectEmployeeAndManager(page);

  await expect(page.getByTestId('users-create-username')).toHaveValue('zhangsan');
  await page.getByTestId('users-create-submit').click();

  await expect.poll(() => capturedCreateBody?.username || '').toBe('zhangsan');
  await expect(page.getByTestId('users-create-username')).toHaveValue('zhangsan');
  await expect(page.getByTestId('users-create-error')).toHaveText('用户账号已存在');
  await expect(page.getByTestId('users-create-form')).toBeVisible();
});
