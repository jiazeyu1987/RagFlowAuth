// @ts-check
const { expect } = require('@playwright/test');
const { adminTest } = require('../helpers/auth');

adminTest('document preview renders backend watermark badge and overlay for onlyoffice documents (mock) @regression @preview', async ({ page }) => {
  await page.route('**/api/datasets', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ datasets: [{ id: 'ds1', name: '展厅' }], count: 1 }),
    });
  });

  await page.route('**/api/ragflow/documents?*', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ documents: [{ id: 'doc1', name: 'report.docx', status: 'ok' }], count: 1 }),
    });
  });

  await page.route('**/api/onlyoffice/editor-config', async (route) => {
    if (route.request().method() !== 'POST') return route.fallback();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        server_url: 'http://onlyoffice.local',
        filename: 'report.docx',
        watermark_policy_id: 'wm-default',
        watermark_text: '用户:测试用户 | 公司:测试公司 | 时间:2026-04-02 10:00:00 CST | 用途:预览 | 文档ID:doc1',
        watermark: {
          policy_id: 'wm-default',
          label: '受控预览',
          text: '用户:测试用户 | 公司:测试公司 | 时间:2026-04-02 10:00:00 CST | 用途:预览 | 文档ID:doc1',
          overlay: {
            text_color: '#6b7280',
            opacity: 0.18,
            rotation_deg: -24,
            gap_x: 260,
            gap_y: 180,
            font_size: 18,
          },
        },
        config: {
          documentType: 'word',
          type: 'desktop',
          document: {
            title: 'report.docx',
            url: 'http://onlyoffice.local/api/file?token=fake-token',
            fileType: 'docx',
            key: 'doc1',
            permissions: {
              edit: false,
              download: false,
              print: false,
              copy: false,
            },
          },
          editorConfig: {
            mode: 'view',
            lang: 'zh-CN',
          },
        },
      }),
    });
  });

  await page.route('**/web-apps/apps/api/documents/api.js', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    await route.fulfill({
      status: 200,
      contentType: 'application/javascript',
      body: `
        window.DocsAPI = {
          DocEditor: function(id, config) {
            window.__onlyofficeLastConfig = config;
            const el = document.getElementById(id);
            if (el) {
              el.setAttribute('data-doc-editor-ready', '1');
              el.textContent = 'ONLYOFFICE READY';
            }
            this.destroyEditor = function() {};
          }
        };
      `,
    });
  });

  await page.goto('/browser');
  await page.getByTestId('browser-dataset-toggle-ds1').click();
  await expect(page.getByTestId('browser-doc-row-ds1-doc1')).toBeVisible();

  await page.getByTestId('browser-doc-view-ds1-doc1').click();
  await expect(page.getByTestId('document-preview-modal')).toBeVisible();
  await expect(page.getByTestId('preview-controlled-badge')).toContainText('受控预览');
  await expect(page.getByTestId('preview-controlled-badge')).toContainText('禁止截图/外传');
  await expect(page.getByTestId('preview-watermark-overlay')).toHaveAttribute('data-watermark-text', /文档ID:doc1/);
  await expect(page.locator('[data-doc-editor-ready="1"]')).toBeVisible();
});
