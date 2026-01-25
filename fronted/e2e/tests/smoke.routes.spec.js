// @ts-check
const { expect } = require('@playwright/test');
const { adminTest } = require('../helpers/auth');
const { mockJson } = require('../helpers/mock');

adminTest('routes load with mocked APIs @smoke', async ({ page }) => {
  // Common: datasets (used by /upload, /documents, /agents, etc.)
  await mockJson(page, '**/api/datasets', {
    datasets: [],
    count: 0,
  });

  // Users page
  await mockJson(page, '**/api/users**', []);
  await mockJson(page, '**/api/permission-groups', { ok: true, data: [] });
  await mockJson(page, '**/api/org/companies', []);
  await mockJson(page, '**/api/org/departments', []);

  // Permission groups page
  await mockJson(page, '**/api/permission-groups/resources/knowledge-bases', { ok: true, data: [] });
  await mockJson(page, '**/api/permission-groups/resources/chats', { ok: true, data: [] });

  // Org directory page
  await mockJson(page, '**/api/org/audit**', []);

  // Documents page
  await mockJson(page, '**/api/knowledge/documents**', { documents: [], count: 0 });
  await mockJson(page, '**/api/knowledge/deletions**', { deletions: [], count: 0 });
  await mockJson(page, '**/api/ragflow/downloads**', { downloads: [], count: 0 });

  // Chat page
  await mockJson(page, '**/api/chats/my', { chats: [] });

  // Agents page
  await mockJson(page, '**/api/search', { chunks: [], total: 0, page: 1, page_size: 30 });

  // Data security page
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
  });
  await mockJson(page, '**/api/admin/data-security/backup/jobs**', { jobs: [] });

  // Navigate a representative set of routes and assert the shell title matches.
  await page.goto('/chat');
  await expect(page.getByTestId('layout-user-name')).toBeVisible();
  await expect(page.getByTestId('layout-header-title')).toHaveText('AI对话');

  await page.goto('/agents');
  await expect(page.getByTestId('layout-header-title')).toHaveText('搜索');

  await page.goto('/documents');
  await expect(page.getByTestId('layout-header-title')).toHaveText('文档审核');

  await page.goto('/upload');
  await expect(page.getByTestId('layout-header-title')).toHaveText('上传文档');

  await page.goto('/users');
  await expect(page.getByTestId('layout-header-title')).toHaveText('用户管理');

  await page.goto('/org-directory');
  await expect(page.getByTestId('layout-header-title')).toHaveText('公司/部门');

  await page.goto('/permission-groups');
  await expect(page.getByTestId('layout-header-title')).toHaveText('权限组管理');

  await page.goto('/data-security');
  await expect(page.getByTestId('layout-header-title')).toHaveText('数据安全');
});
