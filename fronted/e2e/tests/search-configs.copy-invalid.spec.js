// @ts-check
const { expect } = require('@playwright/test');
const { adminTest } = require('../helpers/auth');

adminTest('search configs: copy mode create and invalid json validation @regression @search-configs', async ({ page }) => {
  /** @type {Array<{id:string,name:string,config:Record<string, unknown>}>} */
  let configs = [
    { id: 'sc_default', name: 'Default Config', config: { top_k: 6, rerank: true } },
    { id: 'sc_precision', name: 'Precision Config', config: { top_k: 3, rerank: true, threshold: 0.2 } },
  ];

  let createBody = null;
  let createCalls = 0;

  await page.route('**/api/search/configs', async (route) => {
    const method = route.request().method();
    if (method === 'GET') {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ configs }),
      });
    }

    if (method === 'POST') {
      createCalls += 1;
      createBody = route.request().postDataJSON();
      const created = {
        id: `sc_new_${createCalls}`,
        name: String(createBody?.name || 'new config'),
        config: createBody?.config && typeof createBody.config === 'object' ? createBody.config : {},
      };
      configs = [created, ...configs];
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ config: created }),
      });
    }

    return route.fallback();
  });

  await page.route('**/api/search/configs/*', async (route) => {
    const method = route.request().method();
    const id = decodeURIComponent(new URL(route.request().url()).pathname.split('/').pop() || '');
    const current = configs.find((item) => item.id === id);

    if (method === 'GET') {
      if (!current) {
        return route.fulfill({ status: 404, contentType: 'application/json', body: JSON.stringify({ detail: 'not_found' }) });
      }
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ config: current }),
      });
    }

    return route.fallback();
  });

  await page.goto('/search-configs');

  await expect(page.getByText('Search Configs')).toBeVisible();

  await page.getByRole('button', { name: 'New' }).click();
  await expect(page.getByText('Create Search Config')).toBeVisible();

  await page.getByRole('button', { name: 'Copy' }).click();
  await page.locator('select').last().selectOption('sc_precision');

  const createJson = page.locator('textarea').nth(1);
  await expect(createJson).toContainText('"top_k": 3');
  await expect(createJson).toContainText('"threshold": 0.2');

  await page.getByPlaceholder('Input name').fill('Copied Search Config');
  await page.getByRole('button', { name: 'Create' }).click();

  expect(createCalls).toBe(1);
  expect(createBody).toEqual({ name: 'Copied Search Config', config: { top_k: 3, rerank: true, threshold: 0.2 } });
  await expect(page.getByText('ID: sc_new_1')).toBeVisible();

  await page.getByRole('button', { name: 'New' }).click();
  await page.getByPlaceholder('Input name').fill('Invalid Json Config');
  await page.locator('textarea').nth(1).fill('{"top_k": }');
  await page.getByRole('button', { name: 'Create' }).click();

  expect(createCalls).toBe(1);
  await expect(page.getByText('JSON parse failed')).toBeVisible();
});
