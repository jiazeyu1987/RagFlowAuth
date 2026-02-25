// @ts-check

function getEnv() {
  return {
    frontendBaseURL: process.env.E2E_FRONTEND_BASE_URL || 'http://localhost:3000',
    backendBaseURL: process.env.E2E_BACKEND_BASE_URL || 'http://localhost:8001',
    adminUsername: process.env.E2E_ADMIN_USER || 'admin',
    adminPassword: process.env.E2E_ADMIN_PASS || 'admin123',
    viewerPassword: process.env.E2E_VIEWER_PASS || 'viewer123',
    mode: process.env.E2E_MODE || 'mock',
  };
}

module.exports = { getEnv };
