// @ts-check
const { test, expect, request } = require('@playwright/test');
const { FRONTEND_BASE_URL, BACKEND_BASE_URL, preflightAdmin, uiLogin, ADMIN_USER } = require('../helpers/integration');

test('quality system position assignments persist and appear in audit logs @integration', async ({ page }) => {
  test.setTimeout(120_000);

  const pre = await preflightAdmin();
  if (!pre.ok) test.skip(true, pre.reason);

  const api = await request.newContext({ baseURL: BACKEND_BASE_URL });
  const headers = { Authorization: `Bearer ${pre.tokens.access_token}` };
  let qaPositionId = null;
  let userA = null;
  let userB = null;

  try {
    const configResp = await api.get('/api/admin/quality-system-config', { headers });
    if (!configResp.ok()) {
      throw new Error(`load config failed: ${configResp.status()}`);
    }
    const configJson = await configResp.json();
    qaPositionId = configJson.positions.find((item) => item.name === 'QA')?.id ?? null;
    if (qaPositionId == null) test.fail(true, 'QA position id not found');

    const usersResp = await api.get('/api/admin/quality-system-config/users?limit=10', { headers });
    if (!usersResp.ok()) {
      throw new Error(`load assignable users failed: ${usersResp.status()}`);
    }
    const users = await usersResp.json();
    const candidates = users.filter((item) => String(item.user_id || '') !== String(pre.tokens?.sub || ''));
    if (candidates.length < 2) test.skip(true, 'not enough assignable active bound users in environment');
    [userA, userB] = candidates;

    const seedAssignmentResp = await api.put(
      `/api/admin/quality-system-config/positions/${qaPositionId}/assignments`,
      {
        headers,
        data: {
          user_ids: [userA.user_id],
          change_reason: 'E2E setup',
        },
      }
    );
    if (!seedAssignmentResp.ok()) {
      throw new Error(`seed assignment failed: ${seedAssignmentResp.status()}`);
    }

    await uiLogin(page);

    await page.goto(`${FRONTEND_BASE_URL}/quality-system-config`);
    const prefix = `quality-system-config-position-users-${qaPositionId}`;

    await page.getByTestId(`${prefix}-input`).fill(String(userB.employee_user_id || userB.username || ''));
    await page.getByTestId(`${prefix}-result-${userB.user_id}`).click();

    page.once('dialog', async (dialog) => {
      expect(dialog.type()).toBe('prompt');
      await dialog.accept('Integration assignment update');
    });
    await page.getByTestId(`quality-system-config-position-save-${qaPositionId}`).click();
    await expect(page.getByTestId('quality-system-config-notice')).toContainText('Position assignments saved.');

    await page.reload();
    await expect(page.getByTestId(`${prefix}-chip-${userA.user_id}`)).toBeVisible();
    await expect(page.getByTestId(`${prefix}-chip-${userB.user_id}`)).toBeVisible();

    await page.goto(`${FRONTEND_BASE_URL}/logs`);
    await expect(page.getByTestId('audit-logs-page')).toBeVisible();
    await page.getByTestId('audit-filter-action').selectOption('quality_system_position_assignments_update');
    await page.getByTestId('audit-filter-source').selectOption('quality_system_config');
    await page.getByTestId('audit-filter-resource-id').fill('QA');
    await page.getByTestId('audit-filter-username').fill(ADMIN_USER);
    await page.getByTestId('audit-apply').click();

    await expect(page.getByTestId('audit-total')).not.toHaveText('0', { timeout: 30_000 });
    await expect(page.getByTestId('audit-table')).toContainText('更新体系岗位分配');
    await expect(page.getByTestId('audit-table')).toContainText('体系配置');
    await expect(page.getByTestId('audit-table')).toContainText('QA');
  } finally {
    try {
      if (qaPositionId != null) {
        await api.put(`/api/admin/quality-system-config/positions/${qaPositionId}/assignments`, {
          headers,
          data: { user_ids: [], change_reason: 'E2E cleanup' },
        });
      }
    } finally {
      await api.dispose();
    }
  }
});
