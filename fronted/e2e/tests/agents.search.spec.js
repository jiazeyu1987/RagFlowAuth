// @ts-check
const { test, expect } = require('@playwright/test');
const { adminTest } = require('../helpers/auth');

adminTest('agents search sends expected request and renders results (mock) @regression @agents', async ({ page }) => {
  await page.route('**/api/datasets', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        datasets: [{ id: 'ds1', name: '展厅' }],
        count: 1,
      }),
    });
  });

  let captured = null;
  await page.route('**/api/search', async (route) => {
    if (route.request().method() !== 'POST') return route.fallback();
    captured = route.request().postDataJSON();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        chunks: [
          {
            id: 'c1',
            content: 'hello chunk content',
            dataset_id: 'ds1',
            doc_id: 'doc1',
            doc_name: 'readme.txt',
          },
        ],
        total: 1,
        page: 1,
        page_size: 30,
      }),
    });
  });

  await page.goto('/agents');

  await page.getByPlaceholder('输入搜索关键词或问题...').fill('hello');
  await page.getByRole('button', { name: '搜索' }).click();

  expect(captured).toBeTruthy();
  expect(captured.question).toBe('hello');
  expect(captured.dataset_ids).toEqual(['ds1']);
  expect(captured.page).toBe(1);
  expect(captured.page_size).toBe(30);

  await expect(page.getByText('hello chunk content')).toBeVisible();
});
