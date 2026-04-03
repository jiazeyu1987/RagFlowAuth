// @ts-check
const { expect } = require('@playwright/test');
const { reviewerTest } = require('../helpers/auth');

reviewerTest('review page defaults to assigned approvals and can toggle to all pending @documents @review', async ({ page }) => {
  const mine = {
    doc_id: 'mine1',
    filename: 'mine.txt',
    file_size: 12,
    mime_type: 'text/plain',
    uploaded_by: 'u1',
    uploaded_by_name: 'alice',
    status: 'pending',
    uploaded_at_ms: Date.now(),
    reviewed_by: null,
    reviewed_at_ms: null,
    review_notes: null,
    ragflow_doc_id: null,
    kb_id: 'kb1',
    current_step_name: 'Step 1',
    can_review_current_step: true,
  };
  const other = {
    doc_id: 'other1',
    filename: 'other.txt',
    file_size: 12,
    mime_type: 'text/plain',
    uploaded_by: 'u2',
    uploaded_by_name: 'bob',
    status: 'pending',
    uploaded_at_ms: Date.now(),
    reviewed_by: null,
    reviewed_at_ms: null,
    review_notes: null,
    ragflow_doc_id: null,
    kb_id: 'kb1',
    current_step_name: 'Step 1',
    can_review_current_step: false,
  };

  await page.route('**/api/datasets', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ datasets: [{ id: 'kb1', name: 'kb1' }], count: 1 }),
    });
  });

  await page.route('**/api/knowledge/documents**', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    const url = new URL(route.request().url());
    const assignedOnly = url.searchParams.get('assigned_to_me') === 'true';
    const documents = assignedOnly ? [mine] : [mine, other];
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ documents, count: documents.length }),
    });
  });

  await page.goto('/documents');

  await expect(page.getByTestId('docs-assigned-filter')).toBeVisible();
  await expect(page.getByText('mine.txt')).toBeVisible();
  await expect(page.getByText('other.txt')).toHaveCount(0);
  await expect(page.getByTestId('docs-approve-mine1')).toBeVisible();

  await page.getByTestId('docs-assigned-filter').click();

  await expect(page.getByText('other.txt')).toBeVisible();
  await expect(page.getByTestId('docs-approve-other1')).toHaveCount(0);
});
