// @ts-check
const { expect } = require('@playwright/test');
const { adminTest } = require('../helpers/auth');

adminTest('knowledge config p0: list/detail/save/create-copy/delete-empty-only @regression @kbs', async ({ page }) => {
  let datasets = [
    {
      id: 'kb_nonempty',
      name: 'kb-nonempty',
      description: 'non empty',
      document_count: 1,
      chunk_count: 10,
      chunk_method: 'naive',
      embedding_model: 'bge',
      pagerank: 0,
    },
    {
      id: 'kb_empty',
      name: 'kb-empty',
      description: 'empty',
      document_count: 0,
      chunk_count: 0,
      chunk_method: 'naive',
      embedding_model: 'bge',
      pagerank: 0,
    },
  ];

  const byId = (id) => datasets.find((x) => x.id === id);
  let createBody = null;
  let updateBody = null;
  const deleteCalls = [];

  await page.route('**/api/datasets', async (route) => {
    const method = route.request().method();
    if (method === 'GET') {
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ datasets }) });
    }
    if (method === 'POST') {
      createBody = route.request().postDataJSON();
      const created = {
        id: `kb_new_${Date.now()}`,
        name: createBody?.name || 'kb-new',
        description: createBody?.description || '',
        document_count: 0,
        chunk_count: 0,
        chunk_method: createBody?.chunk_method || 'naive',
        embedding_model: createBody?.embedding_model || 'bge',
        pagerank: createBody?.pagerank || 0,
      };
      datasets = [created, ...datasets];
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ dataset: created }) });
    }
    return route.fallback();
  });

  await page.route('**/api/datasets/*', async (route) => {
    const id = decodeURIComponent(new URL(route.request().url()).pathname.split('/').pop() || '');
    const method = route.request().method();
    if (method === 'GET') {
      const ds = byId(id);
      if (!ds) return route.fulfill({ status: 404, contentType: 'application/json', body: JSON.stringify({ detail: 'dataset_not_found' }) });
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ dataset: ds }) });
    }
    if (method === 'PUT') {
      updateBody = route.request().postDataJSON();
      const ds = byId(id);
      if (!ds) return route.fulfill({ status: 404, contentType: 'application/json', body: JSON.stringify({ detail: 'dataset_not_found' }) });
      Object.assign(ds, updateBody || {});
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ dataset: ds }) });
    }
    if (method === 'DELETE') {
      deleteCalls.push(id);
      datasets = datasets.filter((x) => x.id !== id);
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ok: true }) });
    }
    return route.fallback();
  });

  await page.goto('/kbs');
  await expect(page.getByRole('button', { name: /知识库配置/ })).toBeVisible();
  await expect(page.getByText('ID: kb_nonempty')).toBeVisible();
  await expect(page.getByText('ID: kb_empty')).toBeVisible();

  await page.getByText('ID: kb_nonempty').click();
  const nameInput = page.locator('input').nth(1);
  await nameInput.fill('kb-nonempty-renamed');
  await page.getByRole('button', { name: /保存/ }).first().click();
  expect(updateBody).toBeTruthy();
  expect(updateBody.name).toBe('kb-nonempty-renamed');

  await expect(page.getByTitle('非空知识库，禁止删除')).toBeDisabled();

  page.once('dialog', async (dialog) => dialog.accept());
  await page.getByTitle('删除空知识库').click();
  expect(deleteCalls).toContain('kb_empty');
  await expect(page.getByText('ID: kb_empty')).toHaveCount(0);

  await page.getByRole('button', { name: /新建/ }).first().click();
  await page.getByPlaceholder(/输入新知识库名称/).fill('kb-copy-new');
  await page.getByRole('button', { name: /创建/ }).click();
  expect(createBody).toBeTruthy();
  expect(createBody.name).toBe('kb-copy-new');
  expect(createBody.chunk_method).toBeTruthy();
  expect(createBody.embedding_model).toBeTruthy();
  await expect(page.getByText('ID: kb_new_')).toHaveCount(1);
});
