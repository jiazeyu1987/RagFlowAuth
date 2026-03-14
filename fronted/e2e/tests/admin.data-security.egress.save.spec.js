// @ts-check
const { expect } = require('@playwright/test');
const { adminTest } = require('../helpers/auth');

adminTest('data security egress config can be edited and saved @regression @admin', async ({ page }) => {
  const settings = {
    target_mode: 'local',
    target_local_dir: '/mnt/backup/ragflowauth',
    target_ip: '',
    target_share_name: '',
    target_subdir: '',
    ragflow_compose_path: '/app/ragflow_compose/docker-compose.yml',
    ragflow_stop_services: false,
    full_backup_include_images: true,
    auth_db_path: 'data/auth.db',
    last_run_at_ms: null,
    backup_retention_max: 30,
    backup_target_path: '/mnt/backup/ragflowauth',
    backup_pack_count: 1,
  };

  let egressConfig = {
    mode: 'extranet',
    minimal_egress_enabled: true,
    sensitive_classification_enabled: true,
    auto_desensitize_enabled: true,
    high_sensitive_block_enabled: true,
    domestic_model_whitelist_enabled: false,
    domestic_model_allowlist: ['qwen-plus'],
    allowed_target_hosts: [],
    sensitivity_rules: {
      low: ['公开资料'],
      medium: ['内部资料'],
      high: ['身份证号', '银行卡号'],
    },
    updated_by_user_id: 'admin',
    updated_at_ms: Date.now(),
  };
  let capturedPut = null;

  await page.route('**/api/admin/data-security/settings', async (route) => {
    const method = route.request().method();
    if (method === 'GET') {
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(settings) });
    }
    if (method === 'PUT') {
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(settings) });
    }
    return route.fallback();
  });

  await page.route('**/api/admin/data-security/backup/jobs**', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ jobs: [] }) });
  });

  await page.route('**/api/admin/security/egress/config', async (route) => {
    const method = route.request().method();
    if (method === 'GET') {
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(egressConfig) });
    }
    if (method === 'PUT') {
      capturedPut = route.request().postDataJSON();
      egressConfig = {
        ...egressConfig,
        ...(capturedPut || {}),
        updated_by_user_id: 'e2e_admin',
        updated_at_ms: Date.now(),
      };
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(egressConfig) });
    }
    return route.fallback();
  });

  await page.goto('/data-security');
  await expect(page.getByTestId('ds-egress-rules-high')).toContainText('身份证号');

  await page.getByTestId('ds-egress-auto-desensitize').uncheck();
  await page.getByTestId('ds-egress-rules-high').fill('身份证号\n银行卡号\n手机号');
  await page.getByTestId('ds-egress-save').click();

  expect(capturedPut).toBeTruthy();
  expect(capturedPut.auto_desensitize_enabled).toBe(false);
  expect(capturedPut.sensitivity_rules.high).toEqual(['身份证号', '银行卡号', '手机号']);

  await expect(page.getByTestId('ds-egress-message')).toContainText('已保存');
});

