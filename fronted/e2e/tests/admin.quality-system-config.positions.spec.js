// @ts-check
const { expect } = require('@playwright/test');
const { adminTest, mockAuthMe } = require('../helpers/auth');
const { mockJson } = require('../helpers/mock');

adminTest('quality system config position assignment saves reason and persists after reload @regression @admin', async ({ page }) => {
  await mockAuthMe(page);
  await mockJson(page, '**/api/inbox**', { items: [], total: 0, unread_count: 0 });

  const configState = {
    positions: [
      {
        id: 1,
        name: 'QA',
        in_signoff: true,
        in_compiler: true,
        in_approver: false,
        seeded_from_json: true,
        assigned_users: [
          {
            user_id: 'u-qa-2',
            username: 'qa_user_2',
            full_name: 'QA User Two',
            employee_user_id: 'emp-qa-2',
            status: 'active',
            company_id: 1,
            company_name: 'Company A',
            department_id: 10,
            department_name: 'Dept A',
          },
        ],
      },
    ],
    file_categories: [
      { id: 101, name: '产品技术要求', seeded_from_json: true, is_active: true },
    ],
  };

  let capturedUpdateBody = null;
  await page.route('**/api/admin/quality-system-config', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(configState) });
  });

  await page.route('**/api/admin/quality-system-config/users**', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    const url = new URL(route.request().url());
    const q = String(url.searchParams.get('q') || '').trim().toLowerCase();
    const items = [
      {
        user_id: 'u-qa-1',
        username: 'qa_user_1',
        full_name: 'QA User One',
        employee_user_id: 'emp-qa-1',
        status: 'active',
        company_id: 1,
        company_name: 'Company A',
        department_id: 10,
        department_name: 'Dept A',
      },
      {
        user_id: 'u-qa-2',
        username: 'qa_user_2',
        full_name: 'QA User Two',
        employee_user_id: 'emp-qa-2',
        status: 'active',
        company_id: 1,
        company_name: 'Company A',
        department_id: 10,
        department_name: 'Dept A',
      },
    ].filter((item) => !q || JSON.stringify(item).toLowerCase().includes(q));
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(items) });
  });

  await page.route('**/api/admin/quality-system-config/positions/1/assignments', async (route) => {
    if (route.request().method() !== 'PUT') return route.fallback();
    capturedUpdateBody = route.request().postDataJSON();
    configState.positions[0] = {
      ...configState.positions[0],
      assigned_users: [
        {
          user_id: 'u-qa-1',
          username: 'qa_user_1',
          full_name: 'QA User One',
          employee_user_id: 'emp-qa-1',
          status: 'active',
          company_id: 1,
          company_name: 'Company A',
          department_id: 10,
          department_name: 'Dept A',
        },
        {
          user_id: 'u-qa-2',
          username: 'qa_user_2',
          full_name: 'QA User Two',
          employee_user_id: 'emp-qa-2',
          status: 'active',
          company_id: 1,
          company_name: 'Company A',
          department_id: 10,
          department_name: 'Dept A',
        },
      ],
    };
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(configState.positions[0]) });
  });

  await page.goto('/quality-system-config');
  await expect(page.getByTestId('quality-system-config-position-1')).toContainText('QA');
  await expect(page.getByTestId('quality-system-config-position-1')).toContainText('审核会签');
  await expect(page.getByTestId('quality-system-config-position-1')).toContainText('编制');

  await page.getByTestId('quality-system-config-position-users-1-input').click();
  await page.getByTestId('quality-system-config-position-users-1-input').fill('qa');
  await expect(page.getByTestId('quality-system-config-position-users-1-result-u-qa-1')).toBeVisible();
  await page.getByTestId('quality-system-config-position-users-1-result-u-qa-1').click();

  page.once('dialog', async (dialog) => {
    expect(dialog.type()).toBe('prompt');
    await dialog.accept('Assign QA owners');
  });
  await page.getByTestId('quality-system-config-position-save-1').click();

  expect(capturedUpdateBody).toBeTruthy();
  expect(capturedUpdateBody.user_ids).toEqual(['u-qa-2', 'u-qa-1']);
  expect(capturedUpdateBody.change_reason).toBe('Assign QA owners');
  await expect(page.getByTestId('quality-system-config-notice')).toContainText('Position assignments saved.');

  await page.reload();
  await expect(page.getByTestId('quality-system-config-position-users-1-chip-u-qa-2')).toBeVisible();
  await expect(page.getByTestId('quality-system-config-position-users-1-chip-u-qa-1')).toBeVisible();
});

adminTest('quality system config position assignment prompt cancel does not submit @regression @admin', async ({ page }) => {
  await mockAuthMe(page);
  await mockJson(page, '**/api/inbox**', { items: [], total: 0, unread_count: 0 });
  await mockJson(page, '**/api/admin/quality-system-config', {
    positions: [
      {
        id: 3,
        name: '文档管理员',
        in_signoff: true,
        in_compiler: false,
        in_approver: false,
        seeded_from_json: true,
        assigned_users: [],
      },
    ],
    file_categories: [],
  });

  let putCount = 0;
  await page.route('**/api/admin/quality-system-config/users**', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([
        {
          user_id: 'u-doc-1',
          username: 'doc_user_1',
          full_name: 'Doc User One',
          employee_user_id: 'emp-doc-1',
          status: 'active',
        },
      ]),
    });
  });
  await page.route('**/api/admin/quality-system-config/positions/3/assignments', async (route) => {
    if (route.request().method() !== 'PUT') return route.fallback();
    putCount += 1;
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({}) });
  });

  await page.goto('/quality-system-config');
  await page.getByTestId('quality-system-config-position-users-3-input').fill('doc');
  await page.getByTestId('quality-system-config-position-users-3-result-u-doc-1').click();

  page.once('dialog', async (dialog) => {
    expect(dialog.type()).toBe('prompt');
    await dialog.dismiss();
  });
  await page.getByTestId('quality-system-config-position-save-3').click();

  expect(putCount).toBe(0);
});
