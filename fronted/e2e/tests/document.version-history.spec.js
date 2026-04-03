// @ts-check
const { expect } = require('@playwright/test');
const { adminTest } = require('../helpers/auth');
const { mockJson } = require('../helpers/mock');

adminTest('audit page opens document version history modal @regression @audit', async ({ page }) => {
  await mockJson(page, '**/api/users**', [
    { user_id: 'u1', username: 'alice' },
    { user_id: 'u2', username: 'bob' },
  ]);

  await mockJson(page, '**/api/knowledge/deletions**', { deletions: [] });
  await mockJson(page, '**/api/ragflow/downloads**', { downloads: [] });
  await mockJson(page, '**/api/knowledge/documents?**', {
    documents: [
      {
        doc_id: 'doc-current',
        kb_id: 'kb-a',
        filename: 'spec.pdf',
        uploaded_by: 'u1',
        uploaded_by_name: 'alice',
        reviewed_by: 'u2',
        reviewed_by_name: 'bob',
        status: 'approved',
        uploaded_at_ms: 1712000000000,
        reviewed_at_ms: 1712000100000,
        version_no: 2,
        is_current: true,
        effective_status: 'approved',
      },
    ],
    count: 1,
  });

  await page.route('**/api/knowledge/documents/doc-current/versions', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        logical_doc_id: 'logical-1',
        current_doc_id: 'doc-current',
        count: 2,
        versions: [
          {
            doc_id: 'doc-current',
            filename: 'spec.pdf',
            uploaded_by: 'u1',
            uploaded_by_name: 'alice',
            status: 'approved',
            uploaded_at_ms: 1712000000000,
            reviewed_by: 'u2',
            reviewed_by_name: 'bob',
            reviewed_at_ms: 1712000100000,
            logical_doc_id: 'logical-1',
            version_no: 2,
            previous_doc_id: 'doc-old',
            superseded_by_doc_id: null,
            is_current: true,
            effective_status: 'approved',
            archived_at_ms: null,
            retention_until_ms: null,
            file_sha256: 'a'.repeat(64),
          },
          {
            doc_id: 'doc-old',
            filename: 'spec.pdf',
            uploaded_by: 'u1',
            uploaded_by_name: 'alice',
            status: 'approved',
            uploaded_at_ms: 1711000000000,
            reviewed_by: 'u2',
            reviewed_by_name: 'bob',
            reviewed_at_ms: 1711000100000,
            logical_doc_id: 'logical-1',
            version_no: 1,
            previous_doc_id: null,
            superseded_by_doc_id: 'doc-current',
            is_current: false,
            effective_status: 'superseded',
            archived_at_ms: 1712000200000,
            retention_until_ms: null,
            file_sha256: 'b'.repeat(64),
          },
        ],
      }),
    });
  });

  await page.goto('/documents?tab=records');
  await page.getByTestId('documents-tab-records').click();

  await expect(page.getByTestId('audit-doc-row-doc-current')).toContainText('v2');
  await page.getByTestId('audit-doc-versions-doc-current').click();

  await expect(page.getByTestId('audit-versions-modal')).toBeVisible();
  await expect(page.getByText('逻辑文档 ID: logical-1')).toBeVisible();
  await expect(page.getByTestId('audit-version-row-doc-current')).toContainText('当前生效');
  await expect(page.getByTestId('audit-version-row-doc-old')).toContainText('历史版本');
  await expect(page.getByTestId('audit-version-row-doc-old')).toContainText('b'.repeat(64));
});
