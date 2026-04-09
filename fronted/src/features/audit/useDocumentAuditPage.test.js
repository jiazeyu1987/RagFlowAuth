import { act, renderHook, waitFor } from '@testing-library/react';
import useDocumentAuditPage from './useDocumentAuditPage';
import { auditApi } from './api';
import { usersApi } from '../users/api';
import { useAuth } from '../../hooks/useAuth';

jest.mock('./api', () => ({
  __esModule: true,
  auditApi: {
    listDocuments: jest.fn(),
    listDeletions: jest.fn(),
    listDownloads: jest.fn(),
    listDocumentVersions: jest.fn(),
  },
}));

jest.mock('../users/api', () => ({
  __esModule: true,
  usersApi: {
    items: jest.fn(),
  },
}));

jest.mock('../../hooks/useAuth', () => ({
  useAuth: jest.fn(),
}));

describe('useDocumentAuditPage', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    useAuth.mockReturnValue({
      user: {
        user_id: 'admin-1',
        username: 'admin',
        full_name: 'Admin User',
      },
    });
    usersApi.items.mockResolvedValue([
      { user_id: 'u-1', username: 'alice', full_name: 'Alice' },
      { user_id: 'u-2', username: 'bob', full_name: 'Bob' },
    ]);
    auditApi.listDocuments.mockResolvedValue([
      {
        doc_id: 'doc-1',
        kb_id: 'KB-1',
        filename: 'spec.pdf',
        uploaded_by: 'u-1',
        reviewed_by: 'u-2',
        status: 'approved',
        uploaded_at_ms: 1712203200000,
        reviewed_at_ms: 1712206800000,
      },
      {
        doc_id: 'doc-2',
        kb_id: 'KB-2',
        filename: 'guide.pdf',
        uploaded_by: 'admin-1',
        reviewed_by: '',
        status: 'pending',
        uploaded_at_ms: 1712303200000,
        reviewed_at_ms: null,
      },
    ]);
    auditApi.listDeletions.mockResolvedValue([
      {
        id: 'del-1',
        kb_id: 'KB-1',
        filename: 'old.pdf',
      },
    ]);
    auditApi.listDownloads.mockResolvedValue([
      {
        id: 'down-1',
        kb_id: 'KB-2',
        filename: 'guide.pdf',
      },
    ]);
    auditApi.listDocumentVersions.mockResolvedValue({
      versions: [
        {
          doc_id: 'doc-1-v2',
          version_no: 2,
          filename: 'spec.pdf',
          is_current: true,
          effective_status: 'approved',
          uploaded_by: 'u-1',
          uploaded_at_ms: 1712203200000,
          archived_at_ms: null,
          file_sha256: 'abc123',
        },
      ],
      currentDocId: 'doc-1-v2',
      logicalDocId: 'logical-1',
    });
  });

  it('loads audit data into stable hook state and derives filters from the feature api', async () => {
    const { result } = renderHook(() => useDocumentAuditPage());

    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(usersApi.items).toHaveBeenCalledWith({ limit: 2000 });
    expect(auditApi.listDocuments).toHaveBeenCalledWith({ limit: 2000 });
    expect(auditApi.listDeletions).toHaveBeenCalledWith({ limit: 2000 });
    expect(auditApi.listDownloads).toHaveBeenCalledWith({ limit: 2000 });
    expect(result.current.documents.map((item) => item.doc_id)).toEqual(['doc-2', 'doc-1']);
    expect(result.current.knowledgeBases).toEqual(['KB-2', 'KB-1']);
    expect(result.current.resolveDisplayName('admin-1')).toBe('Admin User');

    act(() => {
      result.current.setFilterKb('KB-1');
      result.current.setFilterStatus('approved');
    });

    expect(result.current.filteredDocuments.map((item) => item.doc_id)).toEqual(['doc-1']);
    expect(result.current.filteredDeletions.map((item) => item.id)).toEqual(['del-1']);
    expect(result.current.filteredDownloads).toHaveLength(0);
  });

  it('loads version history for the selected document through the feature api', async () => {
    const { result } = renderHook(() => useDocumentAuditPage());

    await waitFor(() => expect(result.current.loading).toBe(false));

    const targetDocument = result.current.documents.find((item) => item.doc_id === 'doc-1');

    await act(async () => {
      await result.current.openVersionsDialog(targetDocument);
    });

    expect(auditApi.listDocumentVersions).toHaveBeenCalledWith('doc-1');
    expect(result.current.versionsDialog.open).toBe(true);
    expect(result.current.versionsDialog.logicalDocId).toBe('logical-1');
    expect(result.current.versionsDialog.items).toEqual([
      expect.objectContaining({
        doc_id: 'doc-1-v2',
      }),
    ]);
  });

  it('maps backend ascii permission codes to Chinese error messages', async () => {
    usersApi.items.mockRejectedValueOnce(new Error('no_knowledge_management_permission'));

    const { result } = renderHook(() => useDocumentAuditPage());

    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(result.current.error).toBe('当前账号没有知识库管理权限');
  });
});
