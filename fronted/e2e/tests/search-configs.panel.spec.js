// @ts-check
const { expect } = require('@playwright/test');
const { adminTest } = require('../helpers/auth');

adminTest('search configs panel: create update delete flow @regression @search-configs', async ({ page }) => {
  /** @type {Array<{id:string,name:string,config:Record<string, unknown>}>} */
  let configs = [
    { id: 'sc_default', name: 'Default Config', config: { top_k: 6, rerank: true } },
    { id: 'sc_precision', name: 'Precision Config', config: { top_k: 3, rerank: true } },
  ];

  let updateBody = null;
  let createBody = null;
  const deleteCalls = [];

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
      createBody = route.request().postDataJSON();
      const created = {
        id: 'sc_new_1',
        name: String(createBody?.name || 'New Config'),
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

    if (method === 'PUT') {
      updateBody = route.request().postDataJSON();
      if (!current) {
        return route.fulfill({ status: 404, contentType: 'application/json', body: JSON.stringify({ detail: 'not_found' }) });
      }
      current.name = String(updateBody?.name || current.name);
      current.config = updateBody?.config && typeof updateBody.config === 'object' ? updateBody.config : current.config;
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ config: current }),
      });
    }

    if (method === 'DELETE') {
      deleteCalls.push(id);
      configs = configs.filter((item) => item.id !== id);
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ ok: true }),
      });
    }

    return route.fallback();
  });

  await page.goto('/search-configs');

  await expect(page.getByText('Search Configs')).toBeVisible();
  await expect(page.getByText('ID: sc_default')).toBeVisible();

  const nameInput = page.getByPlaceholder('Config name');
  await expect(nameInput).toHaveValue('Default Config');
  await nameInput.fill('Default Config Updated');

  const detailJson = page.locator('textarea').first();
  await detailJson.fill('{\n  "top_k": 8,\n  "rerank": false\n}');

  await page.getByRole('button', { name: 'Save' }).click();

  expect(updateBody).toEqual({ name: 'Default Config Updated', config: { top_k: 8, rerank: false } });
  await expect(page.getByText('Saved')).toBeVisible();

  await page.getByRole('button', { name: 'New' }).click();
  await expect(page.getByText('Create Search Config')).toBeVisible();

  await page.getByPlaceholder('Input name').fill('Guidewire Search Config');
  const createJson = page.locator('textarea').nth(1);
  await createJson.fill('{\n  "top_k": 12,\n  "use_vector": true\n}');
  await page.getByRole('button', { name: 'Create' }).click();

  expect(createBody).toEqual({ name: 'Guidewire Search Config', config: { top_k: 12, use_vector: true } });
  await expect(page.getByText('ID: sc_new_1')).toBeVisible();

  page.once('dialog', async (dialog) => dialog.accept());
  await page.getByRole('button', { name: 'Del' }).first().click();

  expect(deleteCalls).toContain('sc_new_1');
  await expect(page.getByText('ID: sc_new_1')).toHaveCount(0);
});
