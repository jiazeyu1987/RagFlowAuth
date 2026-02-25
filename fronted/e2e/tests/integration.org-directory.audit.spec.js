// @ts-check
const { test, expect, request } = require('@playwright/test');
const { FRONTEND_BASE_URL, BACKEND_BASE_URL, preflightAdmin, uiLogin } = require('../helpers/integration');

test('org directory create -> audit visible (real backend) @integration', async ({ page }) => {
  test.setTimeout(120_000);

  const pre = await preflightAdmin();
  if (!pre.ok) test.skip(true, pre.reason);

  const companyName = `e2e_company_${Date.now()}_${Math.random().toString(16).slice(2, 8)}`;
  const deptName = `e2e_dept_${Date.now()}_${Math.random().toString(16).slice(2, 8)}`;
  let companyId = null;
  let deptId = null;

  await uiLogin(page);
  await expect(page).toHaveURL(/\/chat$/);

  try {
    await page.goto(`${FRONTEND_BASE_URL}/org-directory`);

    const [companyResp] = await Promise.all([
      page.waitForResponse((r) => r.url().includes('/api/org/companies') && r.request().method() === 'POST'),
      (async () => {
        await page.getByTestId('org-company-name').fill(companyName);
        await page.getByTestId('org-company-add').click();
      })(),
    ]);
    const company = await companyResp.json();
    companyId = company?.id;
    await expect(page.getByText(companyName, { exact: true })).toBeVisible();

    await page.getByTestId('org-tab-departments').click();
    const [deptResp] = await Promise.all([
      page.waitForResponse((r) => r.url().includes('/api/org/departments') && r.request().method() === 'POST'),
      (async () => {
        await page.getByTestId('org-department-name').fill(deptName);
        await page.getByTestId('org-department-add').click();
      })(),
    ]);
    const dept = await deptResp.json();
    deptId = dept?.id;
    await expect(page.getByText(deptName, { exact: true })).toBeVisible();

    await page.getByTestId('org-tab-audit').click();
    await page.getByTestId('org-audit-refresh').click();
    await expect(page.getByText(companyName)).toBeVisible({ timeout: 30_000 });
    await expect(page.getByText(deptName)).toBeVisible({ timeout: 30_000 });
  } finally {
    const api = await request.newContext({ baseURL: BACKEND_BASE_URL });
    try {
      const headers = { Authorization: `Bearer ${pre.tokens.access_token}` };
      if (deptId != null) await api.delete(`/api/org/departments/${deptId}`, { headers });
      if (companyId != null) await api.delete(`/api/org/companies/${companyId}`, { headers });
    } finally {
      await api.dispose();
    }
  }
});
