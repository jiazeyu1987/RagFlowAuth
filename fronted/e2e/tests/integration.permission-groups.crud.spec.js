// @ts-check
const { test, expect, request } = require('@playwright/test');
const { FRONTEND_BASE_URL, BACKEND_BASE_URL, preflightAdmin, uiLogin } = require('../helpers/integration');

test('permission groups create -> edit -> delete (real backend) @integration', async ({ page }) => {
  test.setTimeout(120_000);

  const pre = await preflightAdmin();
  if (!pre.ok) test.skip(true, pre.reason);

  const groupName = `e2e_group_${Date.now()}_${Math.random().toString(16).slice(2, 8)}`;
  let groupId = null;

  await uiLogin(page);
  await expect(page).toHaveURL(/\/chat$/);

  try {
    await page.goto(`${FRONTEND_BASE_URL}/permission-groups`);

    await page.getByTestId('pg-create-open').click();
    await page.getByTestId('pg-form-group-name').fill(groupName);
    await page.getByTestId('pg-form-description').fill('e2e desc');
    await page.getByTestId('pg-form-can-upload').check();

    const [createResp] = await Promise.all([
      page.waitForResponse((r) => r.url().includes('/api/permission-groups') && r.request().method() === 'POST'),
      page.getByTestId('pg-form-submit').click(),
    ]);
    const created = await createResp.json();
    groupId = created?.data?.group_id || created?.group_id || null;
    await expect(page.getByText(groupName, { exact: true })).toBeVisible({ timeout: 30_000 });

    if (groupId == null) test.fail(true, 'create permission group did not return group_id');

    await page.getByTestId(`pg-edit-${groupId}`).click();
    await page.getByTestId('pg-form-description').fill('e2e desc updated');
    await page.getByTestId('pg-form-can-review').check();

    await Promise.all([
      page.waitForResponse((r) => r.url().includes(`/api/permission-groups/${groupId}`) && r.request().method() === 'PUT'),
      page.getByTestId('pg-form-submit').click(),
    ]);

    await page.getByTestId(`pg-edit-${groupId}`).click();
    await expect(page.getByTestId('pg-form-description')).toHaveValue('e2e desc updated');
    await expect(page.getByTestId('pg-form-can-review')).toBeChecked();
    await page.getByTestId('pg-form-cancel').click();

    await page.getByTestId(`pg-delete-${groupId}`).click();
    await Promise.all([
      page.waitForResponse((r) => r.url().includes(`/api/permission-groups/${groupId}`) && r.request().method() === 'DELETE'),
      page.getByTestId('pg-delete-confirm').click(),
    ]);

    await expect(page.getByText(groupName)).toHaveCount(0);
  } finally {
    const api = await request.newContext({ baseURL: BACKEND_BASE_URL });
    try {
      if (groupId != null) {
        const headers = { Authorization: `Bearer ${pre.tokens.access_token}` };
        await api.delete(`/api/permission-groups/${groupId}`, { headers });
      }
    } finally {
      await api.dispose();
    }
  }
});
