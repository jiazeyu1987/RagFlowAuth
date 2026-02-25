// @ts-check
const { test, expect, request } = require('@playwright/test');
const { BACKEND_BASE_URL, FRONTEND_BASE_URL, preflightAdmin, uiLogin } = require('../helpers/integration');

test.describe('Password Change Flow', () => {
  test('user changes password successfully and can login with new password @smoke', async ({ page }) => {
    test.setTimeout(90_000);

    const pre = await preflightAdmin();
    if (!pre.ok) test.skip(true, pre.reason);

    const api = await request.newContext({ baseURL: BACKEND_BASE_URL });
    const username = `e2e_pw_${Date.now()}_${Math.random().toString(16).slice(2, 8)}`;
    const oldPassword = 'OldPassw0rd!123';
    const newPassword = 'NewPassw0rd!456';
    let userId = null;

    try {
      // Create a test user
      const headers = { Authorization: `Bearer ${pre.tokens.access_token}` };
      const createResp = await api.post('/api/users', {
        headers,
        data: { username, password: oldPassword, role: 'viewer', status: 'active' },
      });
      expect(createResp.status()).toBe(201);
      const created = await createResp.json();
      userId = created?.user_id || null;
      expect(userId).toBeTruthy();

      // Login with old password
      await uiLogin(page, username, oldPassword);
      await page.waitForURL(/\/chat$/, { timeout: 30_000 });

      // Navigate to change password page
      await page.getByTestId('nav-change-password').click();
      await page.waitForURL(/\/change-password/, { timeout: 10_000 });
      await expect(page.getByTestId('layout-header-title')).toHaveText('修改密码');

      // Fill out the password change form
      await page.getByTestId('change-password-old').fill(oldPassword);
      await page.getByTestId('change-password-new').fill(newPassword);
      await page.getByTestId('change-password-confirm').fill(newPassword);

      // Submit the form
      const [response] = await Promise.all([
        page.waitForResponse((r) => r.url().includes('/api/auth/password') && r.request().method() === 'PUT'),
        page.getByTestId('change-password-submit').click(),
      ]);

      expect(response.ok()).toBeTruthy();

      // Verify success message
      await expect(page.getByTestId('change-password-success')).toHaveText('密码修改成功');

      // Verify form is cleared
      await expect(page.getByTestId('change-password-old')).toHaveValue('');
      await expect(page.getByTestId('change-password-new')).toHaveValue('');
      await expect(page.getByTestId('change-password-confirm')).toHaveValue('');

      // Logout
      await page.getByTestId('layout-logout').click();
      await page.waitForURL(/\/login/, { timeout: 10_000 });

      // Verify old password no longer works
      await page.goto(`${FRONTEND_BASE_URL}/login`);
      await page.getByTestId('login-username').fill(username);
      await page.getByTestId('login-password').fill(oldPassword);
      const [oldLoginResp] = await Promise.all([
        page.waitForResponse((r) => r.url().includes('/api/auth/login') && r.request().method() === 'POST'),
        page.getByTestId('login-submit').click(),
      ]);
      expect([400, 401]).toContain(oldLoginResp.status());

      // Verify new password works
      await page.getByTestId('login-username').fill(username);
      await page.getByTestId('login-password').fill(newPassword);
      const [newLoginResp] = await Promise.all([
        page.waitForResponse((r) => r.url().includes('/api/auth/login') && r.request().method() === 'POST'),
        page.getByTestId('login-submit').click(),
      ]);
      expect(newLoginResp.ok()).toBeTruthy();
      await page.waitForURL(/\/chat$/, { timeout: 30_000 });

      // Verify we're logged in
      await expect(page.getByTestId('layout-user-name')).toHaveText(username);
    } finally {
      // Cleanup: delete the test user
      if (userId != null) {
        const headers = { Authorization: `Bearer ${pre.tokens.access_token}` };
        await api.delete(`/api/users/${userId}`, { headers }).catch(() => {});
      }
      await api.dispose();
    }
  });

  test('password change validation - passwords do not match @smoke', async ({ page }) => {
    test.setTimeout(90_000);

    const pre = await preflightAdmin();
    if (!pre.ok) test.skip(true, pre.reason);

    const api = await request.newContext({ baseURL: BACKEND_BASE_URL });
    const username = `e2e_pw_${Date.now()}_${Math.random().toString(16).slice(2, 8)}`;
    const password = 'Passw0rd!123';
    let userId = null;

    try {
      // Create a test user
      const headers = { Authorization: `Bearer ${pre.tokens.access_token}` };
      const createResp = await api.post('/api/users', {
        headers,
        data: { username, password, role: 'viewer', status: 'active' },
      });
      expect(createResp.status()).toBe(201);
      const created = await createResp.json();
      userId = created?.user_id || null;
      expect(userId).toBeTruthy();

      // Login
      await uiLogin(page, username, password);
      await page.waitForURL(/\/chat$/, { timeout: 30_000 });

      // Navigate to change password page
      await page.getByTestId('nav-change-password').click();
      await page.waitForURL(/\/change-password/, { timeout: 10_000 });

      // Fill out form with mismatched passwords
      await page.getByTestId('change-password-old').fill(password);
      await page.getByTestId('change-password-new').fill('NewPassw0rd!456');
      await page.getByTestId('change-password-confirm').fill('DifferentPassw0rd!789');

      // Submit the form
      await page.getByTestId('change-password-submit').click();

      // Verify validation error
      await expect(page.getByTestId('change-password-error')).toHaveText('两次输入的新密码不一致');
    } finally {
      // Cleanup
      if (userId != null) {
        const headers = { Authorization: `Bearer ${pre.tokens.access_token}` };
        await api.delete(`/api/users/${userId}`, { headers }).catch(() => {});
      }
      await api.dispose();
    }
  });

  test('password change validation - empty fields @smoke', async ({ page }) => {
    test.setTimeout(90_000);

    const pre = await preflightAdmin();
    if (!pre.ok) test.skip(true, pre.reason);

    const api = await request.newContext({ baseURL: BACKEND_BASE_URL });
    const username = `e2e_pw_${Date.now()}_${Math.random().toString(16).slice(2, 8)}`;
    const password = 'Passw0rd!123';
    let userId = null;

    try {
      // Create a test user
      const headers = { Authorization: `Bearer ${pre.tokens.access_token}` };
      const createResp = await api.post('/api/users', {
        headers,
        data: { username, password, role: 'viewer', status: 'active' },
      });
      expect(createResp.status()).toBe(201);
      const created = await createResp.json();
      userId = created?.user_id || null;
      expect(userId).toBeTruthy();

      // Login
      await uiLogin(page, username, password);
      await page.waitForURL(/\/chat$/, { timeout: 30_000 });

      // Navigate to change password page
      await page.getByTestId('nav-change-password').click();
      await page.waitForURL(/\/change-password/, { timeout: 10_000 });

      // Submit without filling any fields
      await page.getByTestId('change-password-submit').click();

      // Verify validation error
      await expect(page.getByTestId('change-password-error')).toHaveText('请输入旧密码和新密码');
    } finally {
      // Cleanup
      if (userId != null) {
        const headers = { Authorization: `Bearer ${pre.tokens.access_token}` };
        await api.delete(`/api/users/${userId}`, { headers }).catch(() => {});
      }
      await api.dispose();
    }
  });

  test('password change validation - incorrect old password @smoke', async ({ page }) => {
    test.setTimeout(90_000);

    const pre = await preflightAdmin();
    if (!pre.ok) test.skip(true, pre.reason);

    const api = await request.newContext({ baseURL: BACKEND_BASE_URL });
    const username = `e2e_pw_${Date.now()}_${Math.random().toString(16).slice(2, 8)}`;
    const password = 'Passw0rd!123';
    let userId = null;

    try {
      // Create a test user
      const headers = { Authorization: `Bearer ${pre.tokens.access_token}` };
      const createResp = await api.post('/api/users', {
        headers,
        data: { username, password, role: 'viewer', status: 'active' },
      });
      expect(createResp.status()).toBe(201);
      const created = await createResp.json();
      userId = created?.user_id || null;
      expect(userId).toBeTruthy();

      // Login
      await uiLogin(page, username, password);
      await page.waitForURL(/\/chat$/, { timeout: 30_000 });

      // Navigate to change password page
      await page.getByTestId('nav-change-password').click();
      await page.waitForURL(/\/change-password/, { timeout: 10_000 });

      // Fill out form with incorrect old password
      await page.getByTestId('change-password-old').fill('WrongPassword!123');
      await page.getByTestId('change-password-new').fill('NewPassw0rd!456');
      await page.getByTestId('change-password-confirm').fill('NewPassw0rd!456');

      // Submit the form
      const [response] = await Promise.all([
        page.waitForResponse((r) => r.url().includes('/api/auth/password') && r.request().method() === 'PUT'),
        page.getByTestId('change-password-submit').click(),
      ]);

      // Verify backend returns error
      expect([400, 401]).toContain(response.status());

      // Verify error message is displayed
      await expect(page.getByTestId('change-password-error')).toBeVisible();
    } finally {
      // Cleanup
      if (userId != null) {
        const headers = { Authorization: `Bearer ${pre.tokens.access_token}` };
        await api.delete(`/api/users/${userId}`, { headers }).catch(() => {});
      }
      await api.dispose();
    }
  });

  test('password change button disabled during submission @smoke', async ({ page }) => {
    test.setTimeout(90_000);

    const pre = await preflightAdmin();
    if (!pre.ok) test.skip(true, pre.reason);

    const api = await request.newContext({ baseURL: BACKEND_BASE_URL });
    const username = `e2e_pw_${Date.now()}_${Math.random().toString(16).slice(2, 8)}`;
    const password = 'Passw0rd!123';
    let userId = null;

    try {
      // Create a test user
      const headers = { Authorization: `Bearer ${pre.tokens.access_token}` };
      const createResp = await api.post('/api/users', {
        headers,
        data: { username, password, role: 'viewer', status: 'active' },
      });
      expect(createResp.status()).toBe(201);
      const created = await createResp.json();
      userId = created?.user_id || null;
      expect(userId).toBeTruthy();

      // Login
      await uiLogin(page, username, password);
      await page.waitForURL(/\/chat$/, { timeout: 30_000 });

      // Navigate to change password page
      await page.getByTestId('nav-change-password').click();
      await page.waitForURL(/\/change-password/, { timeout: 10_000 });

      // Fill out form
      await page.getByTestId('change-password-old').fill(password);
      await page.getByTestId('change-password-new').fill('NewPassw0rd!456');
      await page.getByTestId('change-password-confirm').fill('NewPassw0rd!456');

      await page.route('**/api/auth/password', async (route) => {
        if (route.request().method() !== 'PUT') return route.fallback();
        await new Promise((resolve) => setTimeout(resolve, 600));
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ ok: true }),
        });
      });

      // Submit and verify button is disabled during submission
      await page.getByTestId('change-password-submit').click();
      await expect(page.getByTestId('change-password-submit')).toBeDisabled({ timeout: 5_000 });
      await expect(page.getByTestId('change-password-submit')).toHaveText('提交中...');
      await expect(page.getByTestId('change-password-success')).toHaveText('密码修改成功');

      // Verify button is re-enabled after submission
      await expect(page.getByTestId('change-password-submit')).toBeEnabled();
      await expect(page.getByTestId('change-password-submit')).toHaveText('修改密码');
    } finally {
      // Cleanup
      if (userId != null) {
        const headers = { Authorization: `Bearer ${pre.tokens.access_token}` };
        await api.delete(`/api/users/${userId}`, { headers }).catch(() => {});
      }
      await api.dispose();
    }
  });
});
