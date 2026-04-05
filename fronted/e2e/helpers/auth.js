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
};
