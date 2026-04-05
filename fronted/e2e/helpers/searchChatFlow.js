// @ts-check
const { expect } = require('@playwright/test');
const { poll } = require('./documentFlow');
const { FRONTEND_BASE_URL } = require('./docRealFlow');

async function readJson(response, message) {
  if (!response.ok()) {
    const body = await response.text().catch(() => '');
    throw new Error(`${message}: ${response.status()} ${body}`.trim());
  }
  return response.json();
}

async function createDirectory(api, headers, { name, parentId }) {
  const response = await api.post('/api/knowledge/directories', {
    headers,
    data: { name, parent_id: parentId || null },
  });
  const payload = await readJson(response, `create directory failed for ${name}`);
  const nodeId = String(payload?.node?.id || '').trim();
  if (!nodeId) {
    throw new Error(`create directory did not return node id for ${name}`);
  }
  return payload.node;
}

async function createDataset(api, headers, { name, nodeId }) {
  const response = await api.post('/api/datasets', {
    headers,
    data: { name, node_id: nodeId || null },
  });
  const payload = await readJson(response, `create dataset failed for ${name}`);
  const datasetId = String(payload?.dataset?.id || '').trim();
  if (!datasetId) {
    throw new Error(`create dataset did not return dataset id for ${name}`);
  }
  return payload.dataset;
}

async function createPermissionGroup(api, headers, payload) {
  const response = await api.post('/api/permission-groups', { headers, data: payload });
  const body = await readJson(response, `create permission group failed for ${payload.group_name}`);
  const groupId = Number(body?.data?.group_id || 0);
  if (!Number.isInteger(groupId) || groupId <= 0) {
    throw new Error(`create permission group did not return group_id for ${payload.group_name}`);
  }
  return groupId;
}

async function deletePermissionGroup(api, headers, groupId) {
  const response = await api.delete(`/api/permission-groups/${groupId}`, { headers });
  await readJson(response, `delete permission group failed for ${groupId}`);
}

async function getUser(api, headers, userId) {
  const response = await api.get(`/api/users/${encodeURIComponent(userId)}`, { headers });
  return readJson(response, `get user failed for ${userId}`);
}

async function updateUserGroups(api, headers, userId, groupIds) {
  const response = await api.put(`/api/users/${encodeURIComponent(userId)}`, {
    headers,
    data: { group_ids: groupIds },
  });
  return readJson(response, `update user groups failed for ${userId}`);
}

async function listMyChats(api, headers) {
  const response = await api.get('/api/chats/my', { headers });
  const body = await readJson(response, 'list my chats failed');
  return Array.isArray(body?.chats) ? body.chats : [];
}

async function findChatByRef(api, headers, chatRef) {
  const cleanRef = String(chatRef || '').trim();
  if (!cleanRef) {
    throw new Error('chatRef is required');
  }
  const chats = await listMyChats(api, headers);
  const match = chats.find((chat) => (
    String(chat?.id || '').trim() === cleanRef
    || String(chat?.name || '').trim() === cleanRef
  ));
  if (!match) {
    throw new Error(`chat not found for ref ${cleanRef}`);
  }
  return match;
}

async function createChatSessionViaApi(api, headers, chatId, name = 'doc chat e2e') {
  const response = await api.post(`/api/chats/${encodeURIComponent(chatId)}/sessions`, {
    headers,
    params: { name },
  });
  const body = await readJson(response, `create chat session failed for ${chatId}`);
  const sessionId = String(body?.id || '').trim();
  if (!sessionId) {
    throw new Error(`create chat session did not return id for ${chatId}`);
  }
  return body;
}

async function deleteChatSessionViaApi(api, headers, chatId, sessionId) {
  const response = await api.delete(`/api/chats/${encodeURIComponent(chatId)}/sessions`, {
    headers,
    data: { ids: [sessionId] },
  });
  await readJson(response, `delete chat session failed for ${chatId}/${sessionId}`);
}

async function openChatAndSelect(page, chatId) {
  await page.goto(`${FRONTEND_BASE_URL}/chat`);
  await expect(page.getByTestId('chat-page')).toBeVisible();
  const chatItem = page.getByTestId(`chat-item-${chatId}`);
  await expect(chatItem).toBeVisible();
  await chatItem.click();
}

async function createChatSessionViaUi(page, chatId) {
  const createSessionResponse = page.waitForResponse((response) => (
    response.request().method() === 'POST'
    && response.url().includes(`/api/chats/${chatId}/sessions`)
  ));
  await page.getByTestId('chat-session-create').click();
  const response = await createSessionResponse;
  const body = await readJson(response, `create chat session via UI failed for ${chatId}`);
  const sessionId = String(body?.id || '').trim();
  if (!sessionId) {
    throw new Error('create chat session via UI returned empty id');
  }
  await expect(page.getByTestId(`chat-session-item-${sessionId}`)).toBeVisible();
  return sessionId;
}

async function sendChatQuestionViaUi(page, chatId, question) {
  const assistantMessages = page.getByTestId('chat-messages').locator("[data-testid$='-assistant']");
  const beforeCount = await assistantMessages.count();
  await page.getByTestId('chat-input').fill(question);
  const completionResponsePromise = page.waitForResponse((response) => (
    response.request().method() === 'POST'
    && response.url().includes(`/api/chats/${chatId}/completions`)
  ));
  await page.getByTestId('chat-send').click();
  const completionResponse = await completionResponsePromise;
  if (!completionResponse.ok()) {
    const body = await completionResponse.text().catch(() => '');
    throw new Error(`chat completion failed: ${completionResponse.status()} ${body}`.trim());
  }
  await expect(assistantMessages).toHaveCount(beforeCount + 1, { timeout: 90_000 });
  const assistantMessage = assistantMessages.nth(beforeCount);
  await expect.poll(
    async () => String((await assistantMessage.textContent()) || '').trim().length,
    { timeout: 120_000 }
  ).toBeGreaterThan(0);
  return assistantMessage;
}

async function expectChatUnavailable(page, chatId) {
  await page.goto(`${FRONTEND_BASE_URL}/chat`);
  await expect(page.getByTestId('chat-page')).toBeVisible();
  await expect(page.getByTestId(`chat-item-${chatId}`)).toHaveCount(0);
}

async function expectUnauthorizedRoute(page, path) {
  await page.goto(`${FRONTEND_BASE_URL}${path}`);
  await expect.poll(
    async () => /\/unauthorized$/.test(page.url()),
    { timeout: 30_000, intervals: [500, 1_000, 2_000] }
  ).toBeTruthy();
  await expect(page.getByTestId('unauthorized-title')).toBeVisible();
}

async function waitForChatById(api, headers, chatId, {
  timeoutMs = 30_000,
  intervalMs = 1_000,
} = {}) {
  const clean = String(chatId || '').trim();
  if (!clean) {
    throw new Error('chatId is required');
  }
  const result = await poll(async () => {
    const chats = await listMyChats(api, headers);
    return chats.find((chat) => String(chat?.id || '').trim() === clean) || null;
  }, { timeoutMs, intervalMs });
  if (!result) {
    throw new Error(`chat not visible in user scope: ${clean}`);
  }
  return result;
}

module.exports = {
  createDirectory,
  createDataset,
  createPermissionGroup,
  createChatSessionViaApi,
  createChatSessionViaUi,
  deleteChatSessionViaApi,
  deletePermissionGroup,
  expectChatUnavailable,
  expectUnauthorizedRoute,
  findChatByRef,
  getUser,
  listMyChats,
  openChatAndSelect,
  readJson,
  sendChatQuestionViaUi,
  updateUserGroups,
  waitForChatById,
};
