// @ts-check
const { expect } = require('@playwright/test');
const { docOperatorTest } = require('../helpers/docAuth');
const { loadDocFixtures } = require('../helpers/bootstrapSummary');

const fixtures = loadDocFixtures();

docOperatorTest('Doc inbox uses real unread filtering, read-state updates, and detail navigation @doc-e2e', async ({ page }) => {
  const [firstUnreadId, secondUnreadId] = fixtures.notifications.inbox.unread_job_ids.map(String);
  const readJobId = String(fixtures.notifications.inbox.read_job_id);

  await page.goto('/inbox');
  await expect(page.getByTestId('inbox-page')).toBeVisible();

  await expect(page.getByTestId('inbox-unread-count')).toContainText('2');
  await expect(page.getByTestId(`inbox-item-${firstUnreadId}`)).toBeVisible();
  await expect(page.getByTestId(`inbox-item-${secondUnreadId}`)).toBeVisible();
  await expect(page.getByTestId(`inbox-item-${readJobId}`)).toBeVisible();

  const unreadOnlyResponse = page.waitForResponse((response) => (
    response.request().method() === 'GET'
    && response.url().includes('/api/inbox')
    && response.url().includes('unread_only=true')
  ));
  await page.getByTestId('inbox-toggle-unread').click();
  await expect((await unreadOnlyResponse).ok()).toBeTruthy();
  await expect(page.getByTestId(`inbox-item-${readJobId}`)).toHaveCount(0);
  await expect(page.getByTestId(`inbox-item-${firstUnreadId}`)).toBeVisible();
  await expect(page.getByTestId(`inbox-item-${secondUnreadId}`)).toBeVisible();

  const markFirstReadResponse = page.waitForResponse((response) => (
    response.request().method() === 'POST'
    && response.url().includes(`/api/inbox/${firstUnreadId}/read`)
  ));
  await page.getByTestId(`inbox-mark-read-${firstUnreadId}`).click();
  await expect((await markFirstReadResponse).ok()).toBeTruthy();
  await expect(page.getByTestId('inbox-unread-count')).toContainText('1');
  await expect(page.getByTestId(`inbox-item-${firstUnreadId}`)).toHaveCount(0);
  await expect(page.getByTestId(`inbox-item-${secondUnreadId}`)).toBeVisible();

  const showAllResponse = page.waitForResponse((response) => (
    response.request().method() === 'GET'
    && response.url().includes('/api/inbox')
    && !response.url().includes('unread_only=true')
  ));
  await page.getByTestId('inbox-toggle-unread').click();
  await expect((await showAllResponse).ok()).toBeTruthy();
  await expect(page.getByTestId(`inbox-item-${firstUnreadId}`)).toBeVisible();
  await expect(page.getByTestId(`inbox-item-${readJobId}`)).toBeVisible();

  const markAllReadResponse = page.waitForResponse((response) => (
    response.request().method() === 'POST'
    && response.url().includes('/api/inbox/read-all')
  ));
  await page.getByTestId('inbox-mark-all-read').click();
  await expect((await markAllReadResponse).ok()).toBeTruthy();
  await expect(page.getByTestId('inbox-unread-count')).toContainText('0');
  await expect(page.getByTestId('inbox-mark-all-read')).toBeDisabled();
  await expect(page.locator('[data-testid^="inbox-mark-read-"]')).toHaveCount(0);

  await Promise.all([
    page.waitForURL((url) => url.pathname === '/approvals'),
    page.getByTestId(`inbox-item-${readJobId}`).getByRole('button').first().click(),
  ]);
  await expect(page.getByTestId('approval-center-page')).toBeVisible();
});
