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
  let directoryState = {
    nodes: [],
    datasets: [
      { id: 'kb_nonempty', node_id: '' },
      { id: 'kb_empty', node_id: '' },
    ],
  };

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
      directoryState = {
        ...directoryState,
        datasets: [{ id: created.id, node_id: '' }, ...(directoryState.datasets || [])],
      };
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
      directoryState = {
        ...directoryState,
        datasets: (directoryState.datasets || []).filter((item) => item.id !== id),
      };
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ok: true }) });
    }
    return route.fallback();
  });

  await page.route('**/api/knowledge/directories', async (route) => {
    const method = route.request().method();
    if (method !== 'GET') return route.fallback();
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(directoryState),
    });
  });

  await page.route('**/api/knowledge/directories/datasets/*/node', async (route) => {
    if (route.request().method() !== 'PUT') return route.fallback();
    const datasetId = decodeURIComponent(new URL(route.request().url()).pathname.split('/').slice(-2, -1)[0] || '');
    const payload = route.request().postDataJSON() || {};
    const nodeId = payload.node_id || '';
    const next = (directoryState.datasets || []).filter((item) => item.id !== datasetId);
    next.push({ id: datasetId, node_id: nodeId });
    directoryState = { ...directoryState, datasets: next };
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ ok: true }),
    });
  });

  await page.goto('/kbs');
  await expect(page.getByTestId('kbs-subtab-kbs')).toBeVisible();
  await expect(page.getByTestId('kbs-row-dataset-kb_nonempty')).toBeVisible();
  await expect(page.getByTestId('kbs-row-dataset-kb_empty')).toBeVisible();

  await page.getByTestId('kbs-row-dataset-kb_nonempty').click();
  const nameInput = page.getByTestId('kbs-detail-name');
  await nameInput.fill('kb-nonempty-renamed');
  await page.getByTestId('kbs-detail-save').click();
  expect(updateBody).toBeTruthy();
  expect(updateBody.name).toBe('kb-nonempty-renamed');

  await expect(page.getByTestId('kbs-detail-delete')).toBeDisabled();

  await page.getByTestId('kbs-row-dataset-kb_empty').click();
  page.once('dialog', async (dialog) => dialog.accept());
  await page.getByTestId('kbs-detail-delete').click();
  expect(deleteCalls).toContain('kb_empty');
  await expect(page.getByTestId('kbs-row-dataset-kb_empty')).toHaveCount(0);

  await page.getByTestId('kbs-create-kb').click();
  await expect(page.getByTestId('kbs-create-dialog')).toBeVisible();
  await page.getByTestId('kbs-create-name').fill('kb-copy-new');
  await page.getByTestId('kbs-create-submit').click();
  expect(createBody).toBeTruthy();
  expect(createBody.name).toBe('kb-copy-new');
  await expect(page.locator('[data-testid^="kbs-row-dataset-kb_new_"]')).toHaveCount(1);
});

