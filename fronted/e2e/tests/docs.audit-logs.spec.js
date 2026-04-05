// @ts-check
const { expect } = require('@playwright/test');
const { realAdminTest } = require('../helpers/auth');
const {
  applyAuditLogFilters,
  getFirstAuditTableRowText,
  openAuditLogs,
  paginateAuditLogs,
} = require('../helpers/orgAuditFlow');

realAdminTest('Audit logs covers real auth-login query and real next/prev pagination @doc-e2e', async ({ page }, testInfo) => {
  testInfo.setTimeout(180_000);

  await openAuditLogs(page);

  const firstPage = await applyAuditLogFilters(page, {
    action: 'auth_login',
    limit: 1,
    offset: 0,
  });
  if (firstPage.total < 2) {
    throw new Error(`audit_events_insufficient_for_pagination:${firstPage.total}`);
  }
  expect(firstPage.items.length).toBe(1);
  expect(String(firstPage.items[0].action || '')).toBe('auth_login');

  await expect(page.getByTestId(`audit-row-${firstPage.items[0].id}`)).toBeVisible();
  const firstRowText = await getFirstAuditTableRowText(page);
  expect(firstRowText).toBeTruthy();

  const secondPage = await paginateAuditLogs(page, 'next', {
    action: 'auth_login',
    limit: 1,
    offset: 1,
  });
  expect(secondPage.total).toBe(firstPage.total);
  expect(secondPage.items.length).toBe(1);
  expect(secondPage.items[0].id).not.toBe(firstPage.items[0].id);
  await expect(page.getByTestId(`audit-row-${secondPage.items[0].id}`)).toBeVisible();

  const secondRowText = await getFirstAuditTableRowText(page);
  expect(secondRowText).not.toBe(firstRowText);

  const previousPage = await paginateAuditLogs(page, 'prev', {
    action: 'auth_login',
    limit: 1,
    offset: 0,
  });
  expect(previousPage.total).toBe(firstPage.total);
  expect(previousPage.items.length).toBe(1);
  expect(previousPage.items[0].id).toBe(firstPage.items[0].id);
  await expect(page.getByTestId(`audit-row-${firstPage.items[0].id}`)).toBeVisible();

  const restoredRowText = await getFirstAuditTableRowText(page);
  expect(restoredRowText).toBe(firstRowText);
});
