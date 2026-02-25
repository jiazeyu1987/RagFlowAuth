// @ts-check
const { expect } = require('@playwright/test');
const { adminTest } = require('../helpers/auth');

adminTest('chat config keeps multi-kb selection on save/copy @regression @kbs', async ({ page }) => {
  const kbList = [
    { id: 'ds_hall', name: 'kb-hall' },
    { id: 'ds_research', name: 'kb-research' },
    { id: 'ds_other', name: 'kb-other' },
  ];
  let chats = [{ id: 'chat_123', name: 'chat-123', dataset_ids: ['ds_hall', 'ds_research'] }];

  const chatById = (id) => chats.find((x) => x.id === id);
  let createBody = null;
  let updateBody = null;

  await page.route('**/api/datasets', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ datasets: kbList }) });
  });

  await page.route('**/api/chats?page_size=1000', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ chats }) });
  });

  await page.route('**/api/chats', async (route) => {
    if (route.request().method() !== 'POST') return route.fallback();
    createBody = route.request().postDataJSON();
    const created = { id: `chat_new_${Date.now()}`, ...createBody };
    chats = [created, ...chats];
    return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ chat: created }) });
  });

  await page.route('**/api/chats/*', async (route) => {
    const method = route.request().method();
    const id = decodeURIComponent(new URL(route.request().url()).pathname.split('/').pop() || '');
    if (method === 'GET') {
      const c = chatById(id);
      if (!c) return route.fulfill({ status: 404, contentType: 'application/json', body: JSON.stringify({ detail: 'chat_not_found' }) });
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ chat: c }) });
    }
    if (method === 'PUT') {
      updateBody = route.request().postDataJSON();
      const c = chatById(id);
      if (c) Object.assign(c, updateBody || {});
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ chat: c || { id, ...(updateBody || {}) } }) });
    }
    return route.fallback();
  });

  await page.goto('/kbs');
  await page.getByRole('button', { name: /对话配置/ }).click();

  await page.getByText('ID: chat_123').click();
  const hallCheckbox = page.locator('label', { hasText: 'kb-hall' }).locator('input[type="checkbox"]');
  const researchCheckbox = page.locator('label', { hasText: 'kb-research' }).locator('input[type="checkbox"]');
  const otherCheckbox = page.locator('label', { hasText: 'kb-other' }).locator('input[type="checkbox"]');
  await expect(hallCheckbox).toBeChecked();
  await expect(researchCheckbox).toBeChecked();
  await expect(otherCheckbox).not.toBeChecked();

  await otherCheckbox.check();
  await page.getByRole('button', { name: /保存/ }).first().click();
  expect(updateBody).toBeTruthy();
  expect((updateBody.dataset_ids || []).sort()).toEqual(['ds_hall', 'ds_other', 'ds_research'].sort());

  await page.getByRole('button', { name: /新建/ }).first().click();
  await page.getByPlaceholder(/输入新对话名称/).fill('chat-234');
  await page.getByRole('button', { name: /创建/ }).click();
  expect(createBody).toBeTruthy();
  expect(createBody.name).toBe('chat-234');
  expect((createBody.dataset_ids || []).sort()).toEqual(['ds_hall', 'ds_other', 'ds_research'].sort());
});
