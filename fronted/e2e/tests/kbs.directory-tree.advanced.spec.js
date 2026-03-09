// @ts-check
const { expect } = require('@playwright/test');
const { adminTest } = require('../helpers/auth');

adminTest('kbs directory tree: create, rename, delete directory flow @regression @kbs', async ({ page }) => {
  const treeState = {
    nodes: [{ id: 'n1', name: 'Folder A', path: 'Folder A', parent_id: '', updated_at_ms: 1700000000 }],
    datasets: [],
  };
  let createCalls = 0;
  let renameCalls = 0;
  let deleteCalls = 0;

  await page.route('**/api/datasets', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ datasets: [] }) });
  });

  await page.route('**/api/knowledge/directories', async (route) => {
    const method = route.request().method();
    if (method === 'GET') {
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(treeState) });
    }
    if (method === 'POST') {
      createCalls += 1;
      const body = route.request().postDataJSON();
      treeState.nodes.push({
        id: 'n_new',
        name: String(body?.name || 'New Dir'),
        path: String(body?.name || 'New Dir'),
        parent_id: body?.parent_id || '',
        updated_at_ms: Date.now(),
      });
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ node: { id: 'n_new' } }) });
    }
    return route.fallback();
  });

  await page.route('**/api/knowledge/directories/n_new', async (route) => {
    const method = route.request().method();
    if (method === 'PUT') {
      renameCalls += 1;
      const body = route.request().postDataJSON();
      treeState.nodes = treeState.nodes.map((n) => (n.id === 'n_new' ? { ...n, name: String(body?.name || n.name) } : n));
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ok: true }) });
    }
    if (method === 'DELETE') {
      deleteCalls += 1;
      treeState.nodes = treeState.nodes.filter((n) => n.id !== 'n_new');
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ok: true }) });
    }
    return route.fallback();
  });

  await page.goto('/kbs');
  await expect(page.getByTestId('kbs-subtab-kbs')).toBeVisible();

  page.once('dialog', async (dialog) => dialog.accept('New Dir'));
  await Promise.all([
    page.waitForResponse((resp) => new URL(resp.url()).pathname === '/api/knowledge/directories' && resp.request().method() === 'POST'),
    page.getByTestId('kbs-create-dir').click(),
  ]);
  expect(createCalls).toBe(1);
  await expect(page.getByTestId('kbs-tree-node-n_new')).toBeVisible();

  await page.getByTestId('kbs-tree-node-n_new').click();
  page.once('dialog', async (dialog) => dialog.accept('Renamed Dir'));
  await Promise.all([
    page.waitForResponse((resp) => new URL(resp.url()).pathname === '/api/knowledge/directories/n_new' && resp.request().method() === 'PUT'),
    page.getByTestId('kbs-rename-dir').click(),
  ]);
  expect(renameCalls).toBe(1);

  page.once('dialog', async (dialog) => dialog.accept());
  await Promise.all([
    page.waitForResponse((resp) => new URL(resp.url()).pathname === '/api/knowledge/directories/n_new' && resp.request().method() === 'DELETE'),
    page.getByTestId('kbs-delete-dir').click(),
  ]);
  expect(deleteCalls).toBe(1);
  await expect(page.getByTestId('kbs-tree-node-n_new')).toHaveCount(0);
});

adminTest('kbs directory tree: drag dataset to folder failure shows error @regression @kbs', async ({ page }) => {
  await page.route('**/api/datasets', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        datasets: [{ id: 'ds_move', name: 'KB Move', document_count: 0, chunk_count: 0 }],
      }),
    });
  });

  await page.route('**/api/knowledge/directories', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        nodes: [{ id: 'n_target', name: 'Target Folder', path: 'Target Folder', parent_id: '', updated_at_ms: 1700000000 }],
        datasets: [{ id: 'ds_move', node_id: '' }],
      }),
    });
  });

  await page.route('**/api/knowledge/directories/datasets/ds_move/node', async (route) => {
    if (route.request().method() !== 'PUT') return route.fallback();
    return route.fulfill({
      status: 500,
      contentType: 'application/json',
      body: JSON.stringify({ detail: 'move_failed_test' }),
    });
  });

  await page.goto('/kbs');
  await expect(page.getByTestId('kbs-row-dataset-ds_move')).toBeVisible();
  await expect(page.getByTestId('kbs-tree-node-n_target')).toBeVisible();

  await page.getByTestId('kbs-row-dataset-ds_move').dragTo(page.getByTestId('kbs-tree-node-n_target'));
  await expect(page.getByText('move_failed_test')).toBeVisible();
});
