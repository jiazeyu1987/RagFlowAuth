// @ts-check
const { expect } = require('@playwright/test');
const { docAdminTest } = require('../helpers/docAuth');
const { createTempTextFixture } = require('../helpers/documentFlow');
const { loadBootstrapSummary, loadDocFixtures } = require('../helpers/bootstrapSummary');
const {
  findUserByUsername,
  deleteUserById,
  listUsers,
  readUserEnvelope,
  uniquePassword,
} = require('../helpers/userLifecycleFlow');
const {
  loginApiAs,
  uploadKnowledgeFileViaApi,
  waitForOperationRequestStatus,
  withdrawOperationRequestViaApi,
} = require('../helpers/docRealFlow');

const summary = loadBootstrapSummary();
const fixtures = loadDocFixtures();
const adminUsername =
  process.env.E2E_ADMIN_USER
  || summary?.users?.company_admin?.username
  || summary?.users?.admin?.username;
const adminPassword = process.env.E2E_ADMIN_PASS || 'admin123';
const uploaderUsername = process.env.E2E_UPLOADER_USER || summary?.users?.uploader?.username;
const uploaderPassword = process.env.E2E_UPLOADER_PASS || process.env.E2E_ADMIN_PASS || 'admin123';

async function readJson(response, fallbackMessage) {
  if (!response.ok()) {
    const body = await response.text().catch(() => '');
    throw new Error(`${fallbackMessage}: ${response.status()} ${body}`.trim());
  }
  return response.json();
}

function cloneJson(value) {
  return JSON.parse(JSON.stringify(value));
}

function normalizeChannelTypes(channelTypes) {
  const normalized = [];
  const seen = new Set();
  for (const item of channelTypes || []) {
    const value = String(item || '').trim().toLowerCase();
    if (!value || seen.has(value)) continue;
    seen.add(value);
    normalized.push(value);
  }
  return normalized;
}

function flattenNotificationRules(payload) {
  const groups = Array.isArray(payload?.groups) ? payload.groups : [];
  const items = [];
  for (const group of groups) {
    for (const item of (Array.isArray(group?.items) ? group.items : [])) {
      items.push(item);
    }
  }
  return items;
}

function toWorkflowBody(workflow) {
  const name = String(workflow?.name || '').trim();
  const steps = Array.isArray(workflow?.steps) ? workflow.steps : [];
  if (!name) {
    throw new Error('workflow name missing');
  }
  if (!steps.length) {
    throw new Error('workflow steps missing');
  }
  return {
    name,
    steps: steps.map((step) => {
      const stepName = String(step?.step_name || '').trim();
      const members = Array.isArray(step?.members) ? step.members : [];
      if (!stepName) {
        throw new Error('workflow step name missing');
      }
      if (!members.length) {
        throw new Error(`workflow step members missing: ${stepName}`);
      }
      return {
        step_name: stepName,
        members: members.map((member) => ({
          member_type: String(member?.member_type || '').trim(),
          member_ref: String(member?.member_ref || '').trim(),
        })),
      };
    }),
  };
}

async function listUsersByFullName(api, headers, fullName) {
  const users = await listUsers(api, headers, { limit: '500' });
  const target = String(fullName || '').trim();
  return (Array.isArray(users) ? users : []).filter(
    (item) => String(item?.full_name || '').trim() === target
  );
}

async function deleteUsersByFullName(api, headers, fullName) {
  const users = await listUsersByFullName(api, headers, fullName);
  for (const user of users) {
    const userId = String(user?.user_id || '').trim();
    if (!userId) continue;
    await deleteUserById(api, headers, userId);
  }
}

async function getInboxUnreadCount(api, headers) {
  const payload = await readJson(
    await api.get('/api/inbox?limit=200', { headers }),
    'list inbox failed'
  );
  return Number(payload?.unread_count || 0);
}

async function getNotificationRuleItem(api, headers, eventType) {
  const payload = await readJson(
    await api.get('/api/admin/notifications/rules', { headers }),
    'list notification rules failed'
  );
  const items = flattenNotificationRules(payload);
  const matched = items.find((item) => String(item?.event_type || '').trim() === String(eventType || '').trim());
  if (!matched) {
    throw new Error(`notification rule not found: ${eventType}`);
  }
  return matched;
}

async function upsertNotificationRule(api, headers, eventType, enabledChannelTypes) {
  await readJson(
    await api.put('/api/admin/notifications/rules', {
      headers,
      data: {
        items: [
          {
            event_type: String(eventType || '').trim(),
            enabled_channel_types: normalizeChannelTypes(enabledChannelTypes),
          },
        ],
      },
    }),
    `upsert notification rule failed for ${eventType}`
  );
}

async function getNotificationChannel(api, headers, channelId) {
  const payload = await readJson(
    await api.get('/api/admin/notifications/channels?enabled_only=false', { headers }),
    'list notification channels failed'
  );
  const items = Array.isArray(payload?.items) ? payload.items : [];
  const matched = items.find((item) => String(item?.channel_id || '').trim() === String(channelId || '').trim());
  if (!matched) {
    throw new Error(`notification channel not found: ${channelId}`);
  }
  return matched;
}

function toChannelUpsertPayload(channel) {
  const channelType = String(channel?.channel_type || '').trim();
  const name = String(channel?.name || '').trim();
  if (!channelType) {
    throw new Error('notification channel_type missing');
  }
  if (!name) {
    throw new Error('notification channel name missing');
  }
  const rawConfig = channel?.config;
  const config = rawConfig && typeof rawConfig === 'object' && !Array.isArray(rawConfig) ? rawConfig : {};
  return {
    channel_type: channelType,
    name,
    enabled: Boolean(channel?.enabled),
    config,
  };
}

async function upsertNotificationChannel(api, headers, channelId, payload) {
  await readJson(
    await api.put(`/api/admin/notifications/channels/${encodeURIComponent(channelId)}`, {
      headers,
      data: payload,
    }),
    `upsert notification channel failed for ${channelId}`
  );
}

async function getWorkflowItem(api, headers, operationType) {
  const payload = await readJson(
    await api.get('/api/operation-approvals/workflows', { headers }),
    'list operation workflows failed'
  );
  const items = Array.isArray(payload?.items) ? payload.items : [];
  const matched = items.find(
    (item) => String(item?.operation_type || '').trim() === String(operationType || '').trim()
  );
  if (!matched) {
    throw new Error(`operation workflow not found: ${operationType}`);
  }
  return matched;
}

async function upsertWorkflow(api, headers, operationType, payload) {
  await readJson(
    await api.put(`/api/operation-approvals/workflows/${encodeURIComponent(operationType)}`, {
      headers,
      data: payload,
    }),
    `upsert operation workflow failed for ${operationType}`
  );
}

async function listNotificationJobs(api, headers, { eventType = '', limit = 300 } = {}) {
  const params = new URLSearchParams({ limit: String(limit) });
  if (eventType) params.set('event_type', String(eventType));
  const payload = await readJson(
    await api.get(`/api/admin/notifications/jobs?${params.toString()}`, { headers }),
    'list notification jobs failed'
  );
  return Array.isArray(payload?.items) ? payload.items : [];
}

function hasNotificationJobForRequest(jobs, { requestId, recipientUserId, channelType }) {
  const request = String(requestId || '').trim();
  const recipient = String(recipientUserId || '').trim();
  const channel = String(channelType || '').trim().toLowerCase();
  return (Array.isArray(jobs) ? jobs : []).some((item) => {
    const payload = item?.payload && typeof item.payload === 'object' ? item.payload : {};
    return (
      String(payload?.request_id || '').trim() === request
      && String(item?.recipient_user_id || '').trim() === recipient
      && String(item?.channel_type || '').trim().toLowerCase() === channel
    );
  });
}

docAdminTest('Doc notification settings exercise real rules, channels, history, retry, and dispatch @doc-e2e', async ({ page }) => {
  const queuedJobId = String(fixtures.notifications.history.queued_job_id || '');
  const failedJobId = String(fixtures.notifications.history.failed_job_id || '');
  expect(queuedJobId).toBeTruthy();
  expect(failedJobId).toBeTruthy();

  await page.goto('/notification-settings');
  await expect(page.getByTestId('notification-settings-page')).toBeVisible();

  const todoEmailRule = page.getByTestId('notification-rule-operation_approval_todo-email');
  const todoDingtalkRule = page.getByTestId('notification-rule-operation_approval_todo-dingtalk');
  const todoInAppRule = page.getByTestId('notification-rule-operation_approval_todo-in_app');

  await expect(todoEmailRule).not.toBeChecked();
  await expect(todoInAppRule).toBeChecked();
  await expect(todoDingtalkRule).not.toBeChecked();

  const saveRulesResponse = page.waitForResponse((response) => (
    response.request().method() === 'PUT'
    && response.url().includes('/api/admin/notifications/rules')
  ));
  await todoDingtalkRule.check();
  await page.getByTestId('notification-save-rules').click();
  await expect((await saveRulesResponse).ok()).toBeTruthy();

  await page.reload();
  await expect(page.getByTestId('notification-rule-operation_approval_todo-dingtalk')).toBeChecked();

  await page.getByTestId('notification-tab-channels').click();
  await page.getByTestId('notification-email-host').fill('smtp.doc-e2e.test');
  await page.getByTestId('notification-email-port').fill('465');
  await page.getByTestId('notification-email-from-email').fill('doc-e2e@example.test');
  await page.getByTestId('notification-dingtalk-app-key').fill('doc-e2e-app-key');
  await page.getByTestId('notification-dingtalk-recipient-map').fill(JSON.stringify({
    doc_company_admin: 'doc-company-admin',
    e2e_reviewer: 'real-reviewer',
  }, null, 2));

  const saveChannelResponses = Promise.all([
    page.waitForResponse((response) => (
      response.request().method() === 'PUT'
      && response.url().includes('/api/admin/notifications/channels/email-main')
    )),
    page.waitForResponse((response) => (
      response.request().method() === 'PUT'
      && response.url().includes('/api/admin/notifications/channels/dingtalk-main')
    )),
    page.waitForResponse((response) => (
      response.request().method() === 'PUT'
      && response.url().includes('/api/admin/notifications/channels/inapp-main')
    )),
  ]);
  await page.getByTestId('notification-save-channels').click();
  for (const response of await saveChannelResponses) {
    await expect(response.ok()).toBeTruthy();
  }
  await expect(page.getByTestId('notification-email-host')).toHaveValue('smtp.doc-e2e.test');

  await page.reload();
  await page.getByTestId('notification-tab-channels').click();
  await expect(page.getByTestId('notification-email-host')).toHaveValue('smtp.doc-e2e.test');
  await expect(page.getByTestId('notification-email-from-email')).toHaveValue('doc-e2e@example.test');
  await expect(page.getByTestId('notification-dingtalk-app-key')).toHaveValue('doc-e2e-app-key');

  await page.getByTestId('notification-tab-history').click();

  const failedHistoryResponse = page.waitForResponse((response) => (
    response.request().method() === 'GET'
    && response.url().includes('/api/admin/notifications/jobs')
    && response.url().includes('status=failed')
  ));
  await page.getByTestId('notification-history-status').selectOption('failed');
  await page.getByTestId('notification-history-apply').click();
  await expect((await failedHistoryResponse).ok()).toBeTruthy();
  expect(failedJobId).toBeTruthy();
  const failedRetryButton = page.getByTestId(`notification-retry-${failedJobId}`);
  await expect(failedRetryButton).toBeVisible();

  const retryResponse = page.waitForResponse((response) => (
    response.request().method() === 'POST'
    && response.url().includes(`/api/admin/notifications/jobs/${failedJobId}/retry`)
  ));
  await failedRetryButton.click();
  await expect((await retryResponse).ok()).toBeTruthy();

  const sentHistoryAfterRetry = page.waitForResponse((response) => (
    response.request().method() === 'GET'
    && response.url().includes('/api/admin/notifications/jobs')
    && response.url().includes('status=sent')
  ));
  await page.getByTestId('notification-history-status').selectOption('sent');
  await page.getByTestId('notification-history-apply').click();
  await expect((await sentHistoryAfterRetry).ok()).toBeTruthy();
  await expect(page.locator('tbody')).toContainText(String(failedJobId));

  const queuedHistoryResponse = page.waitForResponse((response) => (
    response.request().method() === 'GET'
    && response.url().includes('/api/admin/notifications/jobs')
    && response.url().includes('status=queued')
  ));
  await page.getByTestId('notification-history-status').selectOption('queued');
  await page.getByTestId('notification-history-apply').click();
  await expect((await queuedHistoryResponse).ok()).toBeTruthy();
  await expect(page.locator('tbody')).toContainText(String(queuedJobId));

  const dispatchResponse = page.waitForResponse((response) => (
    response.request().method() === 'POST'
    && response.url().includes('/api/admin/notifications/dispatch')
  ));
  await page.getByTestId('notification-dispatch-pending').click();
  await expect((await dispatchResponse).ok()).toBeTruthy();

  const sentHistoryAfterDispatch = page.waitForResponse((response) => (
    response.request().method() === 'GET'
    && response.url().includes('/api/admin/notifications/jobs')
    && response.url().includes('status=sent')
  ));
  await page.getByTestId('notification-history-status').selectOption('sent');
  await page.getByTestId('notification-history-apply').click();
  await expect((await sentHistoryAfterDispatch).ok()).toBeTruthy();
  await expect(page.locator('tbody')).toContainText(String(queuedJobId));
});

docAdminTest('Doc notification sends in-app and dingtalk to ¼ÖÔóÓî and unread count increases @doc-e2e', async ({ page }, testInfo) => {
  void page;
  testInfo.setTimeout(300_000);

  const fullName = '\u8d3e\u6cfd\u5b87';
  const username = 'jiazeyu';
  const password = uniquePassword('JiaZeYu');
  const dingtalkAddress = 'jiazeyu-ding-user';
  const uploadFx = createTempTextFixture('doc-notification-jiazeyu');

  /** @type {Error | null} */
  let mainError = null;
  /** @type {Awaited<ReturnType<typeof loginApiAs>> | null} */
  let adminSession = null;
  /** @type {Awaited<ReturnType<typeof loginApiAs>> | null} */
  let uploaderSession = null;
  /** @type {Awaited<ReturnType<typeof loginApiAs>> | null} */
  let targetUserSession = null;

  let createdUserId = '';
  let requestId = '';
  /** @type {string[] | null} */
  let originalRuleChannels = null;
  let ruleChanged = false;
  /** @type {{ channel_type: string, name: string, enabled: boolean, config: Record<string, unknown> } | null} */
  let originalDingtalkChannelPayload = null;
  let dingtalkChannelChanged = false;
  /** @type {{ name: string, steps: Array<{ step_name: string, members: Array<{ member_type: string, member_ref: string }> }> } | null} */
  let originalWorkflowBody = null;
  let workflowChanged = false;

  try {
    expect(adminUsername).toBeTruthy();
    expect(uploaderUsername).toBeTruthy();
    expect(summary?.users?.viewer?.username).toBeTruthy();
    expect(summary?.users?.sub_admin?.username).toBeTruthy();
    expect(summary?.knowledge?.dataset?.id || summary?.knowledge?.dataset?.name).toBeTruthy();

    adminSession = await loginApiAs(adminUsername, adminPassword);
    uploaderSession = await loginApiAs(uploaderUsername, uploaderPassword);

    await deleteUsersByFullName(adminSession.api, adminSession.headers, fullName);
    const staleUser = await findUserByUsername(adminSession.api, adminSession.headers, username);
    if (staleUser?.user_id) {
      await deleteUserById(adminSession.api, adminSession.headers, String(staleUser.user_id));
    }

    const viewerUser = await findUserByUsername(
      adminSession.api,
      adminSession.headers,
      String(summary.users.viewer.username)
    );
    const subAdminUser = await findUserByUsername(
      adminSession.api,
      adminSession.headers,
      String(summary.users.sub_admin.username)
    );
    expect(viewerUser).toBeTruthy();
    expect(subAdminUser).toBeTruthy();

    const createResponse = await adminSession.api.post('/api/users', {
      headers: adminSession.headers,
      data: {
        username,
        employee_user_id: username,
        password,
        full_name: fullName,
        role: 'viewer',
        manager_user_id: subAdminUser?.user_id,
        company_id: viewerUser?.company_id,
        department_id: viewerUser?.department_id,
        status: 'active',
        max_login_sessions: 3,
        idle_timeout_minutes: 120,
      },
    });
    await expect(createResponse.ok()).toBeTruthy();
    const createBody = await createResponse.json();
    createdUserId = String(
      readUserEnvelope(createBody, `create user returned invalid payload for ${username}`).user_id || ''
    ).trim();
    expect(createdUserId).toBeTruthy();

    const usersByName = await listUsersByFullName(adminSession.api, adminSession.headers, fullName);
    const createdUser = usersByName.find((item) => String(item?.user_id || '').trim() === createdUserId);
    expect(createdUser).toBeTruthy();
    expect(String(createdUser?.full_name || '').trim()).toBe(fullName);
    expect(String(createdUser?.username || '').trim()).toBe(username);

    targetUserSession = await loginApiAs(username, password);
    const unreadBefore = await getInboxUnreadCount(targetUserSession.api, targetUserSession.headers);

    const todoRule = await getNotificationRuleItem(adminSession.api, adminSession.headers, 'operation_approval_todo');
    originalRuleChannels = normalizeChannelTypes(todoRule.enabled_channel_types);
    const wantedRuleChannels = normalizeChannelTypes([...originalRuleChannels, 'in_app', 'dingtalk']);
    if (wantedRuleChannels.join('|') !== originalRuleChannels.join('|')) {
      await upsertNotificationRule(adminSession.api, adminSession.headers, 'operation_approval_todo', wantedRuleChannels);
      ruleChanged = true;
    }

    /** @type {{ channel_type: string, name: string, enabled: boolean, config: Record<string, unknown> }} */
    let dingtalkPayload;
    try {
      const dingtalkChannel = await getNotificationChannel(adminSession.api, adminSession.headers, 'dingtalk-main');
      dingtalkPayload = toChannelUpsertPayload(dingtalkChannel);
      originalDingtalkChannelPayload = cloneJson(dingtalkPayload);
    } catch (error) {
      dingtalkPayload = {
        channel_type: 'dingtalk',
        name: 'doc-dingtalk-main',
        enabled: true,
        config: {
          app_key: 'doc-app-key',
          app_secret: 'doc-app-secret',
          agent_id: '10001',
          recipient_map: {},
          api_base: 'https://api.dingtalk.com',
          oapi_base: 'https://oapi.dingtalk.com',
          timeout_seconds: 30,
        },
      };
      originalDingtalkChannelPayload = null;
    }
    const rawRecipientMap = dingtalkPayload.config?.recipient_map;
    const recipientMap = rawRecipientMap && typeof rawRecipientMap === 'object' && !Array.isArray(rawRecipientMap)
      ? rawRecipientMap
      : {};
    if (
      !dingtalkPayload.enabled
      || String(recipientMap?.[createdUserId] || '').trim() !== dingtalkAddress
      || String(recipientMap?.[username] || '').trim() !== dingtalkAddress
    ) {
      await upsertNotificationChannel(
        adminSession.api,
        adminSession.headers,
        'dingtalk-main',
        {
          ...dingtalkPayload,
          enabled: true,
          config: {
            ...dingtalkPayload.config,
            recipient_map: {
              ...recipientMap,
              [createdUserId]: dingtalkAddress,
              [username]: dingtalkAddress,
            },
          },
        }
      );
      dingtalkChannelChanged = true;
    }

    const originalWorkflow = await getWorkflowItem(adminSession.api, adminSession.headers, 'knowledge_file_upload');
    originalWorkflowBody = toWorkflowBody(originalWorkflow);
    await upsertWorkflow(adminSession.api, adminSession.headers, 'knowledge_file_upload', {
      name: originalWorkflowBody.name,
      steps: [
        {
          step_name: 'JiaZeYu Approval',
          members: [
            {
              member_type: 'user',
              member_ref: createdUserId,
            },
          ],
        },
      ],
    });
    workflowChanged = true;

    const request = await uploadKnowledgeFileViaApi(uploaderSession.api, uploaderSession.headers, {
      kbRef: summary?.knowledge?.dataset?.id || summary?.knowledge?.dataset?.name,
      filePath: uploadFx.filePath,
      mimeType: 'text/plain',
    });
    requestId = String(request?.request_id || '').trim();
    expect(requestId).toBeTruthy();

    await waitForOperationRequestStatus(
      uploaderSession.api,
      uploaderSession.headers,
      requestId,
      'in_approval',
      { timeoutMs: 60_000, intervalMs: 1_000 }
    );

    await expect.poll(async () => {
      const jobs = await listNotificationJobs(adminSession.api, adminSession.headers, {
        eventType: 'operation_approval_todo',
        limit: 300,
      });
      const hasDingtalk = hasNotificationJobForRequest(jobs, {
        requestId,
        recipientUserId: createdUserId,
        channelType: 'dingtalk',
      });
      return hasDingtalk;
    }, { timeout: 60_000, intervals: [1_000, 2_000, 3_000] }).toBeTruthy();

    await expect.poll(
      () => getInboxUnreadCount(targetUserSession.api, targetUserSession.headers),
      { timeout: 60_000, intervals: [1_000, 2_000, 3_000] }
    ).toBe(unreadBefore + 1);
  } catch (error) {
    mainError = /** @type {Error} */ (error);
    throw error;
  } finally {
    const cleanupErrors = [];

    if (uploaderSession && requestId) {
      try {
        await withdrawOperationRequestViaApi(uploaderSession.api, uploaderSession.headers, {
          requestId,
          reason: 'Doc notification test cleanup',
        });
      } catch (error) {
        cleanupErrors.push(`withdraw request failed: ${String(error)}`);
      }
    }

    if (adminSession && workflowChanged && originalWorkflowBody) {
      try {
        await upsertWorkflow(adminSession.api, adminSession.headers, 'knowledge_file_upload', originalWorkflowBody);
      } catch (error) {
        cleanupErrors.push(`restore workflow failed: ${String(error)}`);
      }
    }

    if (adminSession && dingtalkChannelChanged && originalDingtalkChannelPayload) {
      try {
        await upsertNotificationChannel(
          adminSession.api,
          adminSession.headers,
          'dingtalk-main',
          originalDingtalkChannelPayload
        );
      } catch (error) {
        cleanupErrors.push(`restore dingtalk channel failed: ${String(error)}`);
      }
    }

    if (adminSession && ruleChanged && originalRuleChannels) {
      try {
        await upsertNotificationRule(
          adminSession.api,
          adminSession.headers,
          'operation_approval_todo',
          originalRuleChannels
        );
      } catch (error) {
        cleanupErrors.push(`restore notification rule failed: ${String(error)}`);
      }
    }

    if (adminSession) {
      try {
        await deleteUsersByFullName(adminSession.api, adminSession.headers, fullName);
      } catch (error) {
        cleanupErrors.push(`delete users by full_name failed: ${String(error)}`);
      }
    }

    if (targetUserSession) await targetUserSession.api.dispose();
    if (uploaderSession) await uploaderSession.api.dispose();
    if (adminSession) await adminSession.api.dispose();
    uploadFx.cleanup();

    if (cleanupErrors.length) {
      if (mainError) {
        // eslint-disable-next-line no-console
        console.error(`[cleanup] ${cleanupErrors.join(' | ')}`);
      } else {
        throw new Error(cleanupErrors.join(' | '));
      }
    }
  }
});
