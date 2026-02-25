// @ts-check
const { expect } = require('@playwright/test');
const { adminTest } = require('../helpers/auth');
const { mockJson } = require('../helpers/mock');

adminTest('routes load with mocked APIs @smoke', async ({ page }) => {
  await mockJson(page, '**/api/datasets', { datasets: [], count: 0 });
  await mockJson(page, '**/api/users**', []);
  await mockJson(page, '**/api/permission-groups', { ok: true, data: [] });
  await mockJson(page, '**/api/org/companies', []);
  await mockJson(page, '**/api/org/departments', []);
  await mockJson(page, '**/api/org/audit**', []);
  await mockJson(page, '**/api/permission-groups/resources/knowledge-bases', { ok: true, data: [] });
  await mockJson(page, '**/api/permission-groups/resources/chats', { ok: true, data: [] });
  await mockJson(page, '**/api/knowledge/documents**', { documents: [], count: 0 });
  await mockJson(page, '**/api/knowledge/deletions**', { deletions: [], count: 0 });
  await mockJson(page, '**/api/ragflow/downloads**', { downloads: [], count: 0 });
  await mockJson(page, '**/api/chats/my', { chats: [] });
  await mockJson(page, '**/api/chats?page_size=1000**', { chats: [], count: 0 });
  await mockJson(page, '**/api/search', { chunks: [], total: 0, page: 1, page_size: 30 });
  await mockJson(page, '**/api/admin/data-security/settings', {
    target_mode: 'local',
    target_local_dir: '',
    target_ip: '',
    target_share_name: '',
    target_subdir: '',
    ragflow_compose_path: '',
    ragflow_stop_services: false,
    full_backup_include_images: false,
    auth_db_path: 'data/auth.db',
    last_run_at_ms: null,
    backup_retention_max: 30,
    backup_target_path: '',
    backup_pack_count: 0,
  });
  await mockJson(page, '**/api/admin/data-security/backup/jobs**', { jobs: [] });

  for (const route of ['/chat', '/agents', '/documents', '/upload', '/users', '/org-directory', '/permission-groups', '/data-security']) {
    await page.goto(route);
    await expect(page.getByTestId('layout-user-name')).toBeVisible();
    await expect(page.getByTestId('layout-header-title')).not.toHaveText('');
  }
});
