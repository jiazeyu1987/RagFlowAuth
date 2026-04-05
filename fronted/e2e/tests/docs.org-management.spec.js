// @ts-check
const { expect } = require('@playwright/test');
const { realAdminTest } = require('../helpers/auth');
const {
  clearOrgExcelFile,
  clearOrgSearch,
  getOrgBootstrapContext,
  loadOrgRebuildAuditRows,
  openOrgDirectory,
  rebuildOrgFromExcel,
  resolveDepartmentFixture,
  searchDepartmentFromOrgTree,
} = require('../helpers/orgAuditFlow');

const orgContext = getOrgBootstrapContext();

realAdminTest('Org management covers real tree search, real Excel rebuild, and real org audit trail @doc-e2e', async ({ page }, testInfo) => {
  testInfo.setTimeout(240_000);

  const { departments } = await openOrgDirectory(page);
  const department = resolveDepartmentFixture(departments);

  await searchDepartmentFromOrgTree(page, department);
  await clearOrgSearch(page, department.id);

  await page.getByTestId('org-tab-overview').click();
  await expect(page.getByTestId('org-rebuild-trigger')).toBeDisabled();

  await page.getByTestId('org-excel-file-input').setInputFiles(orgContext.excelPath);
  await expect(page.getByTestId('org-excel-file-name')).toContainText(orgContext.excelFilename);
  await expect(page.getByTestId('org-rebuild-trigger')).toBeEnabled();

  await clearOrgExcelFile(page);
  await expect(page.getByTestId('org-rebuild-trigger')).toBeDisabled();

  const beforeRows = await loadOrgRebuildAuditRows(page, 50);
  const beforeTopId = beforeRows[0] ? String(beforeRows[0].id) : '';

  await page.getByTestId('org-tab-overview').click();
  const rebuildPayload = await rebuildOrgFromExcel(page, orgContext.excelPath);
  expect(Number(rebuildPayload.company_count)).toBeGreaterThan(0);
  expect(Number(rebuildPayload.department_count)).toBeGreaterThan(0);
  expect(Number(rebuildPayload.employee_count)).toBeGreaterThan(0);

  const afterRows = await loadOrgRebuildAuditRows(page, 50);
  expect(afterRows.length).toBeGreaterThan(0);
  expect(String(afterRows[0].before_name || '')).toContain(orgContext.excelFilename);
  expect(String(afterRows[0].after_name || '')).toContain('companies=');
  if (beforeTopId) {
    expect(String(afterRows[0].id)).not.toBe(beforeTopId);
  }

  const firstAuditRow = page.getByTestId(`org-audit-row-${afterRows[0].id}`);
  await expect(firstAuditRow).toBeVisible();
  await expect(firstAuditRow).toContainText(orgContext.excelFilename);
});
