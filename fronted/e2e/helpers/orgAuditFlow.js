// @ts-check
const fs = require('node:fs');
const path = require('node:path');
const { expect } = require('@playwright/test');
const { loadBootstrapSummary } = require('./bootstrapSummary');

function normalizeText(value) {
  return String(value || '').replace(/\s+/g, ' ').trim();
}

function getOrgBootstrapContext(summaryPath) {
  const summary = loadBootstrapSummary(summaryPath);
  const companyId = Number(summary?.org?.company?.id);
  const companyName = String(summary?.org?.company?.name || '').trim();
  const companyAdminUsername = String(summary?.users?.company_admin?.username || '').trim();
  const excelPathRaw = String(summary?.paths?.org_excel_path || summary?.org?.summary?.source || '').trim();

  if (!Number.isFinite(companyId) || companyId <= 0) {
    throw new Error('bootstrap_org_company_id_missing');
  }
  if (!companyName) {
    throw new Error('bootstrap_org_company_name_missing');
  }
  if (!companyAdminUsername) {
    throw new Error('bootstrap_company_admin_username_missing');
  }
  if (!excelPathRaw) {
    throw new Error('bootstrap_org_excel_path_missing');
  }

  const excelPath = path.resolve(excelPathRaw);
  if (!fs.existsSync(excelPath)) {
    throw new Error(`bootstrap_org_excel_not_found:${excelPath}`);
  }

  return {
    summary,
    companyId,
    companyName,
    companyAdminUsername,
    excelPath,
    excelFilename: path.basename(excelPath),
  };
}

function resolveDepartmentFixture(departments, companyId) {
  if (!Array.isArray(departments) || departments.length === 0) {
    throw new Error('org_departments_empty');
  }

  const preferredDepartment = companyId == null
    ? null
    : departments.find((item) => (
      Number(item?.company_id) === Number(companyId)
      && Number(item?.id) > 0
      && String(item?.name || '').trim()
    ));
  const department = preferredDepartment || departments.find((item) => (
    Number(item?.id) > 0
    && String(item?.name || '').trim()
  ));

  if (!department) {
    throw new Error(
      companyId == null
        ? 'org_department_fixture_missing'
        : `org_department_fixture_missing_for_company:${companyId}`
    );
  }

  return {
    id: Number(department.id),
    name: String(department.name || '').trim(),
    pathName: String(department.path_name || '').trim(),
  };
}

async function openOrgDirectory(page) {
  const treeResponsePromise = page.waitForResponse((response) => (
    response.request().method() === 'GET'
    && new URL(response.url()).pathname.endsWith('/api/org/tree')
  ));
  const departmentsResponsePromise = page.waitForResponse((response) => (
    response.request().method() === 'GET'
    && new URL(response.url()).pathname.endsWith('/api/org/departments')
  ));

  await page.goto('/org-directory');
  await expect(page.getByTestId('org-page')).toBeVisible();

  const [treeResponse, departmentsResponse] = await Promise.all([
    treeResponsePromise,
    departmentsResponsePromise,
  ]);
  await expect(treeResponse.ok()).toBeTruthy();
  await expect(departmentsResponse.ok()).toBeTruthy();

  const tree = await treeResponse.json();
  const departments = await departmentsResponse.json();
  if (!Array.isArray(tree) || tree.length === 0) {
    throw new Error('org_tree_empty');
  }
  if (!Array.isArray(departments) || departments.length === 0) {
    throw new Error('org_departments_empty');
  }

  return {
    tree,
    departments,
  };
}

async function searchDepartmentFromOrgTree(page, department) {
  const searchInput = page.getByTestId('org-search-input');
  await searchInput.fill(department.name);

  const searchResult = page.getByTestId(`org-search-result-department-${department.id}`);
  await expect(searchResult).toBeVisible();
  await searchResult.click();

  const treeNode = page.getByTestId(`org-tree-node-department-${department.id}`);
  await expect(treeNode).toBeVisible();

  return treeNode;
}

async function clearOrgSearch(page, departmentId) {
  await page.getByTestId('org-search-clear').click();
  await expect(page.getByTestId(`org-search-result-department-${departmentId}`)).toHaveCount(0);
}

async function chooseOrgExcelFile(page, excelPath) {
  const resolvedExcelPath = path.resolve(excelPath);
  if (!fs.existsSync(resolvedExcelPath)) {
    throw new Error(`org_excel_file_missing:${resolvedExcelPath}`);
  }

  await page.getByTestId('org-excel-file-input').setInputFiles(resolvedExcelPath);
  await expect(page.getByTestId('org-excel-file-name')).toContainText(path.basename(resolvedExcelPath));
}

async function clearOrgExcelFile(page) {
  await page.getByTestId('org-excel-file-clear').click();
  await expect(page.getByTestId('org-excel-file-clear')).toHaveCount(0);
}

async function loadOrgRebuildAuditRows(page, limit = 50) {
  await page.getByTestId('org-tab-audit').click();
  await page.getByTestId('org-audit-entity-type').selectOption('org_structure');
  await page.getByTestId('org-audit-action').selectOption('rebuild');
  await page.getByTestId('org-audit-limit').selectOption(String(limit));

  const responsePromise = page.waitForResponse((response) => {
    if (response.request().method() !== 'GET') return false;
    const url = new URL(response.url());
    return (
      url.pathname.endsWith('/api/org/audit')
      && url.searchParams.get('entity_type') === 'org_structure'
      && url.searchParams.get('action') === 'rebuild'
      && url.searchParams.get('limit') === String(limit)
    );
  });

  await page.getByTestId('org-audit-refresh').click();
  const response = await responsePromise;
  await expect(response.ok()).toBeTruthy();

  const rows = await response.json();
  if (!Array.isArray(rows)) {
    throw new Error('org_audit_rows_invalid');
  }
  return rows;
}

async function rebuildOrgFromExcel(page, excelPath) {
  await chooseOrgExcelFile(page, excelPath);

  const [response] = await Promise.all([
    page.waitForResponse((response) => (
      response.request().method() === 'POST'
      && new URL(response.url()).pathname.endsWith('/api/org/rebuild-from-excel')
    )),
    page.waitForEvent('dialog').then((dialog) => dialog.accept()),
    page.getByTestId('org-rebuild-trigger').click(),
  ]);
  await expect(response.ok()).toBeTruthy();
  const payload = await response.json();

  if (Number(payload?.company_count) <= 0) {
    throw new Error('org_rebuild_company_count_invalid');
  }
  if (Number(payload?.department_count) <= 0) {
    throw new Error('org_rebuild_department_count_invalid');
  }
  if (Number(payload?.employee_count) <= 0) {
    throw new Error('org_rebuild_employee_count_invalid');
  }

  await expect(page.getByTestId('org-rebuild-trigger')).toBeEnabled();
  return payload;
}

async function openAuditLogs(page) {
  await page.goto('/logs');
  await expect(page.getByTestId('audit-logs-page')).toBeVisible();
  await expect(page.getByTestId('audit-table')).toBeVisible();
}

async function applyAuditLogFilters(page, filters = {}) {
  if (Object.prototype.hasOwnProperty.call(filters, 'action')) {
    await page.getByTestId('audit-filter-action').selectOption(String(filters.action || ''));
  }
  if (Object.prototype.hasOwnProperty.call(filters, 'companyId')) {
    await page.getByTestId('audit-filter-company').selectOption(String(filters.companyId || ''));
  }
  if (Object.prototype.hasOwnProperty.call(filters, 'departmentId')) {
    await page.getByTestId('audit-filter-department').selectOption(String(filters.departmentId || ''));
  }
  if (Object.prototype.hasOwnProperty.call(filters, 'username')) {
    await page.getByTestId('audit-filter-username').fill(String(filters.username || ''));
  }
  if (Object.prototype.hasOwnProperty.call(filters, 'limit')) {
    await page.getByTestId('audit-filter-limit').selectOption(String(filters.limit || 200));
  }

  const expectedOffset = String(filters.offset || 0);
  const expectedAction = Object.prototype.hasOwnProperty.call(filters, 'action')
    ? String(filters.action || '')
    : null;
  const expectedLimit = Object.prototype.hasOwnProperty.call(filters, 'limit')
    ? String(filters.limit || 200)
    : null;

  const responsePromise = page.waitForResponse((response) => {
    if (response.request().method() !== 'GET') return false;
    const url = new URL(response.url());
    if (!url.pathname.endsWith('/api/audit/events')) return false;
    if (url.searchParams.get('offset') !== expectedOffset) return false;
    if (expectedAction !== null && url.searchParams.get('action') !== expectedAction) return false;
    if (expectedLimit !== null && url.searchParams.get('limit') !== expectedLimit) return false;
    return true;
  });

  await page.getByTestId('audit-apply').click();
  const response = await responsePromise;
  await expect(response.ok()).toBeTruthy();

  const payload = await response.json();
  if (!Array.isArray(payload?.items) || typeof payload?.total !== 'number') {
    throw new Error('audit_events_payload_invalid');
  }

  await expect(page.getByTestId('audit-total')).toHaveText(String(payload.total));
  return payload;
}

async function paginateAuditLogs(page, direction, filters = {}) {
  const normalizedDirection = String(direction || '').trim();
  if (normalizedDirection !== 'next' && normalizedDirection !== 'prev') {
    throw new Error(`unsupported_audit_pagination_direction:${normalizedDirection}`);
  }

  const responsePromise = page.waitForResponse((response) => {
    if (response.request().method() !== 'GET') return false;
    const url = new URL(response.url());
    if (!url.pathname.endsWith('/api/audit/events')) return false;
    if (url.searchParams.get('offset') !== String(filters.offset || 0)) return false;
    if (Object.prototype.hasOwnProperty.call(filters, 'action')
      && url.searchParams.get('action') !== String(filters.action || '')) {
      return false;
    }
    if (Object.prototype.hasOwnProperty.call(filters, 'limit')
      && url.searchParams.get('limit') !== String(filters.limit || 200)) {
      return false;
    }
    return true;
  });

  await page.getByTestId(normalizedDirection === 'next' ? 'audit-next' : 'audit-prev').click();
  const response = await responsePromise;
  await expect(response.ok()).toBeTruthy();

  const payload = await response.json();
  if (!Array.isArray(payload?.items) || typeof payload?.total !== 'number') {
    throw new Error('audit_events_payload_invalid');
  }
  return payload;
}

async function getFirstAuditTableRowText(page) {
  const row = page.getByTestId('audit-table').locator('tbody tr').first();
  await expect(row).toBeVisible();
  return normalizeText(await row.textContent());
}

module.exports = {
  applyAuditLogFilters,
  chooseOrgExcelFile,
  clearOrgExcelFile,
  clearOrgSearch,
  getFirstAuditTableRowText,
  getOrgBootstrapContext,
  loadOrgRebuildAuditRows,
  normalizeText,
  openAuditLogs,
  openOrgDirectory,
  paginateAuditLogs,
  rebuildOrgFromExcel,
  resolveDepartmentFixture,
  searchDepartmentFromOrgTree,
};
