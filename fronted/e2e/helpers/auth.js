// @ts-check
const path = require('node:path');
const { test: base } = require('@playwright/test');

const authDir = path.resolve(process.env.E2E_AUTH_DIR || path.join(__dirname, '..', '.auth'));

// Legacy compatibility:
// - admin.json is now backed by a real "operator" account with broad business permissions.
// - real-admin.json is the restricted system admin account from the backend.
const adminStorageStatePath = path.join(authDir, 'admin.json');
const operatorStorageStatePath = path.join(authDir, 'operator.json');
const realAdminStorageStatePath = path.join(authDir, 'real-admin.json');
const companyAdminStorageStatePath = path.join(authDir, 'company-admin.json');
const subAdminStorageStatePath = path.join(authDir, 'sub-admin.json');
const viewerStorageStatePath = path.join(authDir, 'viewer.json');
const reviewerStorageStatePath = path.join(authDir, 'reviewer.json');
const uploaderStorageStatePath = path.join(authDir, 'uploader.json');
const untrainedReviewerStorageStatePath = path.join(authDir, 'untrained-reviewer.json');

const baseMockAuthenticatedUser = Object.freeze({
  user_id: 'u_admin',
  username: 'admin',
  full_name: 'E2E Admin',
  email: 'admin@example.test',
  role: 'admin',
  status: 'active',
  accessible_kb_ids: [],
  permissions: {
    can_upload: true,
    can_review: true,
    can_download: true,
    can_copy: true,
    can_delete: true,
    can_manage_kb_directory: true,
    can_view_kb_config: true,
    can_view_tools: true,
    accessible_tools: [],
  },
  capabilities: {
    users: {
      manage: { scope: 'all', targets: [] },
    },
    kb_documents: {
      view: { scope: 'all', targets: [] },
      upload: { scope: 'all', targets: [] },
      review: { scope: 'all', targets: [] },
      approve: { scope: 'all', targets: [] },
      reject: { scope: 'all', targets: [] },
      delete: { scope: 'all', targets: [] },
      download: { scope: 'all', targets: [] },
      copy: { scope: 'all', targets: [] },
    },
    ragflow_documents: {
      view: { scope: 'all', targets: [] },
      preview: { scope: 'all', targets: [] },
      delete: { scope: 'all', targets: [] },
      download: { scope: 'all', targets: [] },
      copy: { scope: 'all', targets: [] },
    },
    kb_directory: {
      manage: { scope: 'all', targets: [] },
    },
    kbs_config: {
      view: { scope: 'all', targets: [] },
    },
    tools: {
      view: { scope: 'all', targets: [] },
    },
    chats: {
      view: { scope: 'all', targets: [] },
    },
  },
  idle_timeout_minutes: 120,
});

function buildMockAuthenticatedUser(overrides = {}) {
  return {
    ...baseMockAuthenticatedUser,
    ...overrides,
    accessible_kb_ids: Array.isArray(overrides.accessible_kb_ids)
      ? overrides.accessible_kb_ids
      : baseMockAuthenticatedUser.accessible_kb_ids,
    permissions: {
      ...baseMockAuthenticatedUser.permissions,
      ...(overrides.permissions || {}),
    },
    capabilities: overrides.capabilities || baseMockAuthenticatedUser.capabilities,
  };
}

async function mockAuthMe(page, overrides = {}) {
  await page.route('**/api/auth/me', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(buildMockAuthenticatedUser(overrides)),
    });
  });
}

function buildTest(storageState) {
  return base.extend({
    context: async ({ browser }, use) => {
      const context = await browser.newContext({ storageState });
      await use(context);
      await context.close();
    },
    page: async ({ context }, use) => {
      const page = await context.newPage();
      await use(page);
      await page.close();
    },
  });
}

const operatorTest = buildTest(operatorStorageStatePath);
const adminTest = buildTest(adminStorageStatePath);
const realAdminTest = buildTest(realAdminStorageStatePath);
const companyAdminTest = buildTest(companyAdminStorageStatePath);
const subAdminTest = buildTest(subAdminStorageStatePath);
const viewerTest = buildTest(viewerStorageStatePath);
const reviewerTest = buildTest(reviewerStorageStatePath);
const uploaderTest = buildTest(uploaderStorageStatePath);
const untrainedReviewerTest = buildTest(untrainedReviewerStorageStatePath);

module.exports = {
  adminStorageStatePath,
  operatorStorageStatePath,
  realAdminStorageStatePath,
  companyAdminStorageStatePath,
  subAdminStorageStatePath,
  viewerStorageStatePath,
  reviewerStorageStatePath,
  uploaderStorageStatePath,
  untrainedReviewerStorageStatePath,
  adminTest,
  operatorTest,
  realAdminTest,
  companyAdminTest,
  subAdminTest,
  viewerTest,
  reviewerTest,
  uploaderTest,
  untrainedReviewerTest,
  buildMockAuthenticatedUser,
  mockAuthMe,
};
