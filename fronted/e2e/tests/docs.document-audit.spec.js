// @ts-check
const { expect } = require('@playwright/test');
const { docAdminTest } = require('../helpers/docAuth');
const { loadDocFixtures } = require('../helpers/bootstrapSummary');

const fixtures = loadDocFixtures();

docAdminTest('Doc document audit page uses real document, deletion, download, and version history data @doc-e2e', async ({ page }) => {
  await page.goto('/document-history');
  await expect(page.getByTestId('audit-page')).toBeVisible();

  const currentRow = page.getByTestId(`audit-doc-row-${fixtures.documents.current_doc_id}`);
  const secondaryRow = page.getByTestId(`audit-doc-row-${fixtures.documents.secondary_doc_id}`);
  await expect(currentRow).toBeVisible();
  await expect(secondaryRow).toBeVisible();

  const currentKb = (await currentRow.locator('td').first().textContent())?.trim();
  const secondaryKb = (await secondaryRow.locator('td').first().textContent())?.trim();
  expect(currentKb).toBeTruthy();
  expect(secondaryKb).toBeTruthy();
  expect(currentKb).not.toBe(secondaryKb);

  const kbOptions = await page.getByTestId('audit-filter-kb').locator('option').evaluateAll((options) => (
    options.map((option) => ({
      value: option.value,
      text: option.textContent || '',
    }))
  ));
  const secondaryKbOption = kbOptions.find((option) => (
    option.value === secondaryKb || option.text.trim() === secondaryKb
  ));
  expect(secondaryKbOption).toBeTruthy();

  await page.getByTestId('audit-filter-kb').selectOption(secondaryKbOption.value);
  await expect(currentRow).toHaveCount(0);
  await expect(secondaryRow).toBeVisible();

  await page.getByTestId('audit-filter-reset').click();
  await page.getByTestId('audit-filter-status').selectOption('pending');
  await expect(currentRow).toBeVisible();
  await expect(secondaryRow).toHaveCount(0);

  await page.getByTestId('audit-filter-reset').click();

  const versionResponse = page.waitForResponse((response) => (
    response.request().method() === 'GET'
    && response.url().includes(`/api/knowledge/documents/${fixtures.documents.current_doc_id}/versions`)
  ));
  await page.getByTestId(`audit-doc-versions-${fixtures.documents.current_doc_id}`).click();
  await expect((await versionResponse).ok()).toBeTruthy();

  await expect(page.getByTestId('audit-versions-modal')).toBeVisible();
  await expect(page.getByTestId(`audit-version-row-${fixtures.documents.previous_doc_id}`)).toBeVisible();
  await expect(page.getByTestId(`audit-version-row-${fixtures.documents.current_doc_id}`)).toBeVisible();
  await page.getByTestId('audit-versions-modal').getByRole('button').last().click();
  await expect(page.getByTestId('audit-versions-modal')).toHaveCount(0);

  await page.getByTestId('audit-tab-deletions').click();
  await expect(page.getByTestId(`audit-deletion-row-${fixtures.documents.deletion_log_id}`)).toBeVisible();

  await page.getByTestId('audit-tab-downloads').click();
  await expect(page.getByTestId(`audit-download-row-${fixtures.documents.download_log_ids.single}`)).toBeVisible();
  await expect(page.getByTestId(`audit-download-row-${fixtures.documents.download_log_ids.batch}`)).toBeVisible();
});
