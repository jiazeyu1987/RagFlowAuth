// @ts-check
const fs = require('node:fs');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const { request } = require('@playwright/test');
const { getAppVersionFromFrontend } = require('./helpers/appVersion');
const { getEnv } = require('./helpers/env');

/**
 * Write a Playwright storageState file that includes the localStorage keys expected by the React app.
 * IMPORTANT: the app clears auth if STORAGE_KEYS.APP_VERSION != APP_VERSION (see fronted/src/hooks/useAuth.js),
 * so we must set appVersion too.
 */
async function writeStorageState({ storagePath, frontendBaseURL, appVersion, accessToken, refreshToken, user }) {
  const origin = new URL(frontendBaseURL).origin;
  const storageState = {
    cookies: [],
    origins: [
      {
        origin,
        localStorage: [
          { name: 'accessToken', value: String(accessToken || '') },
          { name: 'refreshToken', value: String(refreshToken || '') },
          { name: 'user', value: JSON.stringify(user || {}) },
          { name: 'appVersion', value: String(appVersion || '') },
        ],
      },
    ],
  };

  await fs.promises.mkdir(path.dirname(storagePath), { recursive: true });
  await fs.promises.writeFile(storagePath, JSON.stringify(storageState, null, 2), 'utf8');
}

function resolveAuthDir() {
  const configured = String(process.env.E2E_AUTH_DIR || '').trim();
  if (configured) {
    return path.resolve(configured);
  }
  return path.join(__dirname, '.auth');
}

async function readJsonResponse(resp, fallbackMessage) {
  if (!resp.ok()) {
    const body = await resp.text().catch(() => '');
    throw new Error(`${fallbackMessage}: ${resp.status()} ${body}`);
  }
  return resp.json();
}

async function apiLogin(api, username, password) {
  const loginResp = await api.post('/api/auth/login', {
    data: { username, password },
  });
  const tokens = await readJsonResponse(loginResp, `Login failed for ${username}`);
  const meResp = await api.get('/api/auth/me', {
    headers: { Authorization: `Bearer ${tokens.access_token}` },
  });
  const user = await readJsonResponse(meResp, 'GET /api/auth/me failed');
  return { tokens, user };
}

function resolvePythonCommand() {
  const candidates = [];
  if (process.env.PYTHON && process.env.PYTHON.trim()) {
    const configured = process.env.PYTHON.trim();
    const looksLikePath =
      path.isAbsolute(configured) || configured.includes('\\') || configured.includes('/');
    if (!looksLikePath || fs.existsSync(configured)) {
      candidates.push([configured, []]);
    }
  }
  if (process.platform === 'win32') {
    candidates.push(['python', []]);
    candidates.push(['py', ['-3']]);
  } else {
    candidates.push(['python3', []]);
    candidates.push(['python', []]);
  }
  return candidates;
}

function extractBootstrapJson(stdout) {
  const lines = String(stdout || '')
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);
  for (let index = lines.length - 1; index >= 0; index -= 1) {
    try {
      return JSON.parse(lines[index]);
    } catch (error) {
      // Keep scanning upwards until we find the JSON summary line.
    }
  }
  throw new Error(`Real E2E bootstrap returned invalid JSON: ${String(stdout || '').trim()}`);
}

function runBootstrap(env) {
  if (env.skipBootstrap) {
    return null;
  }

  const repoRoot = path.resolve(__dirname, '..', '..');
  const scriptPath = path.isAbsolute(env.bootstrapScript)
    ? env.bootstrapScript
    : path.join(repoRoot, env.bootstrapScript);
  if (!fs.existsSync(scriptPath)) {
    throw new Error(`Real E2E bootstrap script not found: ${scriptPath}`);
  }

  const baseArgs = [
    scriptPath,
    '--json',
    '--db-path',
    env.testDbPath,
    '--admin-username',
    env.adminUsername,
    '--admin-password',
    env.adminPassword,
    '--sub-admin-username',
    env.subAdminUsername,
    '--sub-admin-password',
    env.subAdminPassword,
    '--operator-username',
    env.operatorUsername,
    '--operator-password',
    env.operatorPassword,
    '--viewer-username',
    env.viewerUsername,
    '--viewer-password',
    env.viewerPassword,
    '--reviewer-username',
    env.reviewerUsername,
    '--reviewer-password',
    env.reviewerPassword,
    '--uploader-username',
    env.uploaderUsername,
    '--uploader-password',
    env.uploaderPassword,
    '--root-name',
    env.rootName,
  ];
  if (env.requireBootstrapRagflow) {
    baseArgs.push('--require-ragflow');
  }
  if (env.orgExcelPath) {
    baseArgs.push('--org-excel-path', env.orgExcelPath);
  }
  if (env.companyName) {
    baseArgs.push('--company-name', env.companyName);
  }
  if (env.datasetName) {
    baseArgs.push('--dataset-name', env.datasetName);
  }

  const attemptErrors = [];
  for (const [command, extraArgs] of resolvePythonCommand()) {
    const result = spawnSync(command, [...extraArgs, ...baseArgs], {
      cwd: repoRoot,
      env: {
        ...process.env,
        PYTHONIOENCODING: 'utf-8',
      },
      encoding: 'utf8',
    });
    if (!result.error && result.status === 0) {
      const stdout = String(result.stdout || '').trim();
      if (!stdout) {
        throw new Error('Real E2E bootstrap returned no JSON summary');
      }
      return extractBootstrapJson(stdout);
    }

    const output = [result.stdout, result.stderr, result.error?.message].filter(Boolean).join('\n').trim();
    attemptErrors.push({
      command: [command, ...extraArgs].join(' '),
      details: output || `exit=${result.status}`,
    });
  }

  const errorDetails = attemptErrors
    .map((item) => `[${item.command}] ${item.details}`)
    .join(' | ');
  throw new Error(
    `Real E2E bootstrap failed. Details: ${errorDetails || 'unknown_error'}`
  );
}

module.exports = async () => {
  const env = getEnv();
  if (env.mode !== 'real') {
    throw new Error(`Unsupported E2E_MODE '${env.mode}'. Mock auth mode has been removed; use E2E_MODE=real.`);
  }

  const bootstrapSummary = runBootstrap(env);
  if (bootstrapSummary) {
    await fs.promises.mkdir(path.dirname(env.bootstrapSummaryPath), { recursive: true });
    await fs.promises.writeFile(env.bootstrapSummaryPath, JSON.stringify(bootstrapSummary, null, 2), 'utf8');
  }
  const resolvedUsers = bootstrapSummary?.users || {
    sub_admin: { username: env.subAdminUsername },
    operator: { username: env.operatorUsername },
    viewer: { username: env.viewerUsername },
    reviewer: { username: env.reviewerUsername },
    uploader: { username: env.uploaderUsername },
  };

  const appVersion = getAppVersionFromFrontend();
  const api = await request.newContext({ baseURL: env.backendBaseURL });

  try {
    const realAdmin = await apiLogin(api, env.adminUsername, env.adminPassword);
    const subAdmin = await apiLogin(api, resolvedUsers.sub_admin.username, env.subAdminPassword);
    const operator = await apiLogin(api, resolvedUsers.operator.username, env.operatorPassword);
    const viewer = await apiLogin(api, resolvedUsers.viewer.username, env.viewerPassword);
    const reviewer = await apiLogin(api, resolvedUsers.reviewer.username, env.reviewerPassword);
    const uploader = await apiLogin(api, resolvedUsers.uploader.username, env.uploaderPassword);

    const authDir = resolveAuthDir();
    const states = [
      { filename: 'real-admin.json', session: realAdmin },
      { filename: 'admin.json', session: operator },
      { filename: 'operator.json', session: operator },
      { filename: 'sub-admin.json', session: subAdmin },
      { filename: 'viewer.json', session: viewer },
      { filename: 'reviewer.json', session: reviewer },
      { filename: 'uploader.json', session: uploader },
    ];
    if (bootstrapSummary?.users?.company_admin?.username) {
      const companyAdmin = await apiLogin(api, bootstrapSummary.users.company_admin.username, env.adminPassword);
      states.push({ filename: 'company-admin.json', session: companyAdmin });
    }
    if (bootstrapSummary?.users?.untrained_reviewer?.username) {
      const untrainedReviewer = await apiLogin(
        api,
        bootstrapSummary.users.untrained_reviewer.username,
        env.adminPassword
      );
      states.push({ filename: 'untrained-reviewer.json', session: untrainedReviewer });
    }

    for (const item of states) {
      await writeStorageState({
        storagePath: path.join(authDir, item.filename),
        frontendBaseURL: env.frontendBaseURL,
        appVersion,
        accessToken: item.session.tokens.access_token,
        refreshToken: item.session.tokens.refresh_token,
        user: item.session.user,
      });
    }
  } finally {
    await api.dispose();
  }
};
