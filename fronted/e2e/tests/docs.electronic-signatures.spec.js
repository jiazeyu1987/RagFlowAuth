// @ts-check
const { expect } = require('@playwright/test');
const { docAdminTest } = require('../helpers/docAuth');

docAdminTest('Doc electronic signature management loads real signature detail and verifies it @doc-e2e', async ({ page }) => {
  await page.goto('/electronic-signatures');
  await expect(page.getByTestId('electronic-signature-management-page')).toBeVisible();

  const recordTypeSelect = page.locator('select').nth(0);
  const actionSelect = page.locator('select').nth(1);
  await recordTypeSelect.selectOption('operation_approval_request');
  await actionSelect.selectOption('operation_approval_approve');

  const listResponsePromise = page.waitForResponse((response) => (
    response.request().method() === 'GET'
    && response.url().includes('/api/electronic-signatures')
    && response.url().includes('record_type=operation_approval_request')
    && response.url().includes('action=operation_approval_approve')
  ));
  await page.getByRole('button', { name: '查询' }).click();
  const listResponse = await listResponsePromise;
  await expect(listResponse.ok()).toBeTruthy();
  const listPayload = await listResponse.json();
  expect(Array.isArray(listPayload.items)).toBeTruthy();
  expect(listPayload.items.length).toBeGreaterThan(0);

  const targetIndex = listPayload.items.length > 1 ? 1 : 0;
  const targetSignature = listPayload.items[targetIndex];
  const selectedSignatureId = String(targetSignature.signature_id);
  const signatureRow = page.locator('tbody tr').nth(targetIndex);
  await expect(signatureRow).toBeVisible();

  const detailResponsePromise = page.waitForResponse((response) => (
    response.request().method() === 'GET'
    && response.url().includes(`/api/electronic-signatures/${selectedSignatureId}`)
  ));
  await signatureRow.getByRole('button', { name: '查看' }).click();
  const detailResponse = await detailResponsePromise;
  await expect(detailResponse.ok()).toBeTruthy();
  const detailPayload = await detailResponse.json();

  await expect(page.getByRole('heading', { name: '签名详情' })).toBeVisible();
  await expect(page.getByText(detailPayload.meaning, { exact: false })).toBeVisible();

  const verifyResponsePromise = page.waitForResponse((response) => (
    response.request().method() === 'POST'
    && response.url().includes(`/api/electronic-signatures/${selectedSignatureId}/verify`)
  ));
  await page.getByRole('button', { name: '验签' }).click();
  const verifyPayload = await (await verifyResponsePromise).json();
  expect(verifyPayload).toMatchObject({
    signature_id: selectedSignatureId,
  });
  expect(typeof verifyPayload.verified).toBe('boolean');
  await expect(page.getByText(/验签通过|验签未通过/)).toBeVisible();
});

docAdminTest('Doc electronic signature management toggles real authorization state and restores it @doc-e2e', async ({ page }) => {
  await page.goto('/electronic-signatures');
  await expect(page.getByTestId('electronic-signature-management-page')).toBeVisible();

  await page.getByRole('button', { name: '签名授权管理' }).click();

  const authorizationRow = page.locator('tbody tr').filter({
    hasText: /Doc Company Admin|doc_company_admin/,
  }).first();
  await expect(authorizationRow).toBeVisible();
  const authorizationButton = authorizationRow.getByRole('button');
  await expect(authorizationButton).toBeVisible();

  const disableResponsePromise = page.waitForResponse((response) => (
    response.request().method() === 'PUT'
    && response.url().includes('/api/electronic-signature-authorizations/')
  ));
  await authorizationButton.click();
  const disableResponse = await disableResponsePromise;
  await expect(disableResponse.ok()).toBeTruthy();
  expect(await disableResponse.json()).toMatchObject({
    electronic_signature_enabled: false,
  });
  await expect(authorizationRow).toContainText(/未授权|启用/);

  const enableResponsePromise = page.waitForResponse((response) => (
    response.request().method() === 'PUT'
    && response.url().includes('/api/electronic-signature-authorizations/')
  ));
  await authorizationRow.getByRole('button').click();
  const enableResponse = await enableResponsePromise;
  await expect(enableResponse.ok()).toBeTruthy();
  expect(await enableResponse.json()).toMatchObject({
    electronic_signature_enabled: true,
  });
  await expect(authorizationRow).toContainText(/已授权|停用/);
});
