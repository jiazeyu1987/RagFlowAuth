// @ts-check
const { test, expect, request } = require('@playwright/test');
const { FRONTEND_BASE_URL, BACKEND_BASE_URL, preflightAdmin, uiLogin } = require('../helpers/integration');

test('users assign permission groups (real backend) @integration', async ({ page }) => {
  test.setTimeout(120_000);

  const pre = await preflightAdmin();
  if (!pre.ok) test.skip(true, pre.reason);

  const username = `e2e_user_${Date.now()}_${Math.random().toString(16).slice(2, 8)}`;
  const password = 'Passw0rd!123';
  const email = 'e2e@example.com';

  let userId = null;
  let companyId = null;
  let departmentId = null;
  let groupId = null;

  await uiLogin(page);
  await expect(page).toHaveURL(/\/$/);

  try {
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

      const groupResp = await seedApi.post('/api/permission-groups', {
        headers,
        data: {
          group_name: `e2e_group_${Date.now()}_${Math.random().toString(16).slice(2, 8)}`,
          description: 'e2e group',
          can_download: true,
          can_upload: false,
          can_review: false,
          can_delete: false,
        },
      });
      if (!groupResp.ok()) test.skip(true, `create permission group failed: ${groupResp.status()}`);
      const createdGroup = await groupResp.json();
      groupId = createdGroup?.data?.group_id ?? null;
      if (groupId == null) test.skip(true, 'create permission group did not return group_id');
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

    await page.getByTestId(`users-edit-groups-${userId}`).click();
    await expect(page.getByTestId('users-group-modal')).toBeVisible();
    await page.getByTestId(`users-group-checkbox-${groupId}`).check();

    const [updateResp] = await Promise.all([
      page.waitForResponse((r) => r.url().includes(`/api/users/${userId}`) && r.request().method() === 'PUT'),
      page.getByTestId('users-group-save').click(),
    ]);
    expect(updateResp.ok()).toBeTruthy();

    const updated = await updateResp.json();
    const gids = updated?.group_ids || (updated?.permission_groups || []).map((pg) => pg.group_id);
    expect(gids).toContain(groupId);

    await expect(page.getByTestId('users-group-modal')).toHaveCount(0);
  } finally {
    const api = await request.newContext({ baseURL: BACKEND_BASE_URL });
    try {
      const headers = { Authorization: `Bearer ${pre.tokens.access_token}` };
      if (userId != null) await api.delete(`/api/users/${userId}`, { headers });
      if (groupId != null) await api.delete(`/api/permission-groups/${groupId}`, { headers });
      if (departmentId != null) await api.delete(`/api/org/departments/${departmentId}`, { headers });
      if (companyId != null) await api.delete(`/api/org/companies/${companyId}`, { headers });
    } finally {
      await api.dispose();
    }
  }
});

