// @ts-check
const { test, expect, request } = require('@playwright/test');
const { FRONTEND_BASE_URL, BACKEND_BASE_URL, preflightAdmin, uiLogin } = require('../helpers/integration');

test('users create -> delete (real backend) @integration', async ({ page }) => {
  test.setTimeout(120_000);

  const pre = await preflightAdmin();
  if (!pre.ok) test.skip(true, pre.reason);

  const username = `e2e_user_${Date.now()}_${Math.random().toString(16).slice(2, 8)}`;
  const password = 'Passw0rd!123';
  const email = 'e2e@example.com';
  let userId = null;
  let companyId = null;
  let departmentId = null;

  await uiLogin(page);
  await expect(page).toHaveURL(/\/$/);

  try {
    // Company/Department are required fields in the UI. Create minimal fixtures to keep the test isolated.
    const seedApi = await request.newContext({ baseURL: BACKEND_BASE_URL });
    try {
      const headers = { Authorization: `Bearer ${pre.tokens.access_token}` };

      const companyResp = await seedApi.post('/api/org/companies', { headers, data: { name: `e2e_company_${Date.now()}` } });
      if (!companyResp.ok()) test.skip(true, `create company failed: ${companyResp.status()}`);
      const company = await companyResp.json();
      companyId = company?.id ?? null;
      if (companyId == null) test.skip(true, 'create company did not return id');

      const deptResp = await seedApi.post('/api/org/departments', { headers, data: { name: `e2e_dept_${Date.now()}` } });
      if (!deptResp.ok()) test.skip(true, `create department failed: ${deptResp.status()}`);
      const dept = await deptResp.json();
      departmentId = dept?.id ?? null;
      if (departmentId == null) test.skip(true, 'create department did not return id');
    } finally {
      await seedApi.dispose();
    }

    await page.goto(`${FRONTEND_BASE_URL}/users`);

    await page.getByTestId('users-create-open').click();
    await page.getByTestId('users-create-username').fill(username);
    await page.getByTestId('users-create-password').fill(password);
    await page.getByTestId('users-create-email').fill(email);
    await page.getByTestId('users-create-company').selectOption(String(companyId));
    await page.getByTestId('users-create-department').selectOption(String(departmentId));

    const [createResp] = await Promise.all([
      page.waitForResponse((r) => r.url().includes('/api/users') && r.request().method() === 'POST'),
      page.getByTestId('users-create-submit').click(),
    ]);
    const created = await createResp.json();
    userId = created?.user_id || null;

    if (userId == null) test.fail(true, 'create user did not return user_id');

    await expect(page.getByTestId(`users-row-${userId}`)).toBeVisible({ timeout: 30_000 });

    page.once('dialog', async (dialog) => {
      if (dialog.type() === 'confirm') await dialog.accept();
      else await dialog.dismiss();
    });
    await Promise.all([
      page.waitForResponse((r) => r.url().includes(`/api/users/${userId}`) && r.request().method() === 'DELETE'),
      page.getByTestId(`users-delete-${userId}`).click(),
    ]);

    await expect(page.getByTestId(`users-row-${userId}`)).toHaveCount(0);
  } finally {
    const api = await request.newContext({ baseURL: BACKEND_BASE_URL });
    try {
      const headers = { Authorization: `Bearer ${pre.tokens.access_token}` };
      if (userId != null) await api.delete(`/api/users/${userId}`, { headers });
      if (departmentId != null) await api.delete(`/api/org/departments/${departmentId}`, { headers });
      if (companyId != null) await api.delete(`/api/org/companies/${companyId}`, { headers });
    } finally {
      await api.dispose();
    }
  }
});
