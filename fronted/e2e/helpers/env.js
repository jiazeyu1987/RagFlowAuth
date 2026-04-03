// @ts-check

function getEnv() {
  const adminPassword = process.env.E2E_ADMIN_PASS || 'admin123';
  return {
    frontendBaseURL: process.env.E2E_FRONTEND_BASE_URL || 'http://localhost:3000',
    backendBaseURL: process.env.E2E_BACKEND_BASE_URL || 'http://localhost:8001',
    adminUsername: process.env.E2E_ADMIN_USER || 'admin',
    adminPassword,
    operatorPassword: process.env.E2E_OPERATOR_PASS || adminPassword,
    viewerPassword: process.env.E2E_VIEWER_PASS || adminPassword,
    reviewerPassword: process.env.E2E_REVIEWER_PASS || adminPassword,
    uploaderPassword: process.env.E2E_UPLOADER_PASS || adminPassword,
    mode: process.env.E2E_MODE || 'real',
  };
}

module.exports = { getEnv };
