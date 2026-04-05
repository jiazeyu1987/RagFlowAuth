// @ts-check
const { getAppVersionFromFrontend } = require('./appVersion');
const { FRONTEND_BASE_URL } = require('./docRealFlow');

function storageStateFromSession(session) {
  const origin = new URL(FRONTEND_BASE_URL).origin;
  return {
    cookies: [],
    origins: [
      {
        origin,
        localStorage: [
          { name: 'accessToken', value: String(session?.tokens?.access_token || '') },
          { name: 'refreshToken', value: String(session?.tokens?.refresh_token || '') },
          { name: 'user', value: JSON.stringify(session?.user || {}) },
          { name: 'appVersion', value: String(getAppVersionFromFrontend()) },
        ],
      },
    ],
  };
}

async function openSessionPage(browser, session) {
  const context = await browser.newContext({
    storageState: storageStateFromSession(session),
  });
  const page = await context.newPage();
  return { context, page };
}

module.exports = {
  openSessionPage,
  storageStateFromSession,
};
