// @ts-check
const { expect } = require('@playwright/test');
const { adminTest, viewerTest } = require('../helpers/auth');

adminTest('root route redirects to chat and shell renders @regression @dashboard', async ({ page }) => {
  await page.goto('/');
  await expect(page).toHaveURL(/\/chat$/);
  await expect(page.getByTestId('layout-user-name')).toBeVisible();
  await expect(page.getByTestId('chat-page')).toBeVisible();
});

adminTest('admin can navigate to key routes from sidebar @regression @dashboard', async ({ page }) => {
  await page.goto('/chat');
  await page.getByTestId('nav-browser').click();
  await expect(page).toHaveURL(/\/browser$/);

  await page.getByTestId('nav-agents').click();
  await expect(page).toHaveURL(/\/agents$/);
});

viewerTest('viewer has no admin menu entries @regression @dashboard', async ({ page }) => {
  await page.goto('/chat');
  await expect(page.getByTestId('layout-user-name')).toBeVisible();

  await expect(page.getByTestId('nav-users')).toHaveCount(0);
  await expect(page.getByTestId('nav-permission-groups')).toHaveCount(0);
  await expect(page.getByTestId('nav-org-directory')).toHaveCount(0);
  await expect(page.getByTestId('nav-data-security')).toHaveCount(0);
  await expect(page.getByTestId('nav-logs')).toHaveCount(0);
});

viewerTest('dashboard shows empty state when user has no dashboard cards @regression @dashboard', async ({ page }) => {
  await page.goto('/dashboard');
  await expect(page.getByTestId('dashboard-page')).toBeVisible();
  await expect(page.getByTestId('dashboard-empty')).toBeVisible();
});

adminTest('dashboard route renders stats cards from backend stats API @regression @dashboard', async ({ page }) => {
  await page.route('**/api/knowledge/stats', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        pending_documents: 3,
        approved_documents: 9,
        rejected_documents: 2,
        total_documents: 14,
      }),
    });
  });

  await page.goto('/dashboard');
  await expect(page.getByTestId('dashboard-page')).toBeVisible();
  await expect(page.getByTestId('dashboard-card-pending')).toContainText('3');
  await expect(page.getByTestId('dashboard-card-approved')).toContainText('9');
  await expect(page.getByTestId('dashboard-card-rejected')).toContainText('2');
  await expect(page.getByTestId('dashboard-card-total')).toContainText('14');
});

adminTest('dashboard quick actions navigate to target routes @regression @dashboard', async ({ page }) => {
  await page.route('**/api/knowledge/stats', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        pending_documents: 1,
        approved_documents: 2,
        rejected_documents: 0,
        total_documents: 3,
      }),
    });
  });

  await page.goto('/dashboard');
  await expect(page.getByTestId('dashboard-quick-browser')).toBeVisible();
  await expect(page.getByTestId('dashboard-quick-upload')).toBeVisible();
  await expect(page.getByTestId('dashboard-quick-documents')).toBeVisible();

  await page.getByTestId('dashboard-quick-browser').click();
  await expect(page).toHaveURL(/\/browser$/);

  await page.goto('/dashboard');
  await page.getByTestId('dashboard-quick-upload').click();
  await expect(page).toHaveURL(/\/upload$/);

  await page.goto('/dashboard');
  await page.getByTestId('dashboard-quick-documents').click();
  await expect(page).toHaveURL(/\/documents$/);
});

adminTest('dashboard shows stats error when stats API fails @regression @dashboard', async ({ page }) => {
  await page.route('**/api/knowledge/stats', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    return route.fulfill({
      status: 500,
      contentType: 'application/json',
      body: JSON.stringify({ detail: 'stats_failed_test' }),
    });
  });

  await page.goto('/dashboard');
  await expect(page.getByTestId('dashboard-page')).toBeVisible();
  await expect(page.getByTestId('dashboard-stats-error')).toContainText('Failed to get stats');
});
