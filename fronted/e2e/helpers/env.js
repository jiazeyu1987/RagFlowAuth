// @ts-check
const path = require('node:path');

function getEnv() {
  const repoRoot = path.resolve(__dirname, '..', '..', '..');
  const adminPassword = process.env.E2E_ADMIN_PASS || 'admin123';
  const bootstrapScript = process.env.E2E_BOOTSTRAP_SCRIPT || path.join('scripts', 'bootstrap_real_test_env.py');
  return {
    frontendBaseURL: process.env.E2E_FRONTEND_BASE_URL || 'http://localhost:3001',
    backendBaseURL: process.env.E2E_BACKEND_BASE_URL || 'http://localhost:8001',
    adminUsername: process.env.E2E_ADMIN_USER || 'admin',
    adminPassword,
    subAdminUsername: process.env.E2E_SUB_ADMIN_USER || 'e2e_sub_admin',
    subAdminPassword: process.env.E2E_SUB_ADMIN_PASS || adminPassword,
    operatorUsername: process.env.E2E_OPERATOR_USER || 'e2e_operator',
    operatorPassword: process.env.E2E_OPERATOR_PASS || adminPassword,
    viewerUsername: process.env.E2E_VIEWER_USER || 'e2e_viewer',
    viewerPassword: process.env.E2E_VIEWER_PASS || adminPassword,
    reviewerUsername: process.env.E2E_REVIEWER_USER || 'e2e_reviewer',
    reviewerPassword: process.env.E2E_REVIEWER_PASS || adminPassword,
    uploaderUsername: process.env.E2E_UPLOADER_USER || 'e2e_uploader',
    uploaderPassword: process.env.E2E_UPLOADER_PASS || adminPassword,
    mode: process.env.E2E_MODE || 'real',
    companyName: process.env.E2E_REAL_COMPANY_NAME || '',
    datasetName: process.env.E2E_REAL_DATASET_NAME || '',
    orgExcelPath: process.env.E2E_ORG_EXCEL_PATH || '',
    rootName: process.env.E2E_REAL_ROOT_NAME || 'RagflowAuth E2E Root',
    requireBootstrapRagflow: String(process.env.E2E_BOOTSTRAP_REQUIRE_RAGFLOW || '').trim() === '1',
    testDbPath: process.env.E2E_TEST_DB_PATH || path.join(repoRoot, 'data', 'e2e', 'auth.db'),
    skipBootstrap: String(process.env.E2E_SKIP_BOOTSTRAP || '').trim() === '1',
    bootstrapScript,
    bootstrapSummaryPath: process.env.E2E_BOOTSTRAP_SUMMARY_PATH || path.join(repoRoot, 'fronted', 'e2e', '.auth', 'bootstrap-summary.json'),
  };
}

module.exports = { getEnv };
