// @ts-check
const path = require('node:path');
const { test: base } = require('@playwright/test');

const authDir = path.resolve(__dirname, '..', '.auth');

// Legacy compatibility:
// - admin.json is now backed by a real "operator" account with broad business permissions.
// - real-admin.json is the restricted system admin account from the backend.
const adminStorageStatePath = path.join(authDir, 'admin.json');
const operatorStorageStatePath = path.join(authDir, 'operator.json');
const realAdminStorageStatePath = path.join(authDir, 'real-admin.json');
const viewerStorageStatePath = path.join(authDir, 'viewer.json');
const reviewerStorageStatePath = path.join(authDir, 'reviewer.json');
const uploaderStorageStatePath = path.join(authDir, 'uploader.json');

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
const viewerTest = buildTest(viewerStorageStatePath);
const reviewerTest = buildTest(reviewerStorageStatePath);
const uploaderTest = buildTest(uploaderStorageStatePath);

module.exports = {
  adminStorageStatePath,
  operatorStorageStatePath,
  realAdminStorageStatePath,
  viewerStorageStatePath,
  reviewerStorageStatePath,
  uploaderStorageStatePath,
  adminTest,
  operatorTest,
  realAdminTest,
  viewerTest,
  reviewerTest,
  uploaderTest,
};
