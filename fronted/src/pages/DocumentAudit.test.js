import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import DocumentAudit from './DocumentAudit';
import { knowledgeApi } from '../features/knowledge/api';
import { usersApi } from '../features/users/api';
import { useAuth } from '../hooks/useAuth';

jest.mock('../features/knowledge/api', () => ({
  __esModule: true,
  knowledgeApi: {
    listDocuments: jest.fn(),
    listDeletions: jest.fn(),
    listDownloads: jest.fn(),
    listDocumentVersions: jest.fn(),
  },
}));

jest.mock('../features/users/api', () => ({
  __esModule: true,
  usersApi: {
    items: jest.fn(),
  },
}));

jest.mock('../hooks/useAuth', () => ({
  useAuth: jest.fn(),
}));

describe('DocumentAudit', () => {
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
    knowledgeApi.listDocuments.mockResolvedValue([
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
    ]);
    knowledgeApi.listDeletions.mockResolvedValue([]);
    knowledgeApi.listDownloads.mockResolvedValue([]);
    knowledgeApi.listDocumentVersions.mockResolvedValue({
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

  it('loads audit lists and opens document version history via feature APIs', async () => {
    const user = userEvent.setup();

    render(<DocumentAudit />);

    expect(await screen.findByTestId('audit-doc-row-doc-1')).toBeInTheDocument();
    expect(usersApi.items).toHaveBeenCalledWith({ limit: 2000 });
    expect(knowledgeApi.listDocuments).toHaveBeenCalledWith({ limit: 2000 });
    expect(knowledgeApi.listDeletions).toHaveBeenCalledWith({ limit: 2000 });
    expect(knowledgeApi.listDownloads).toHaveBeenCalledWith({ limit: 2000 });

    await user.click(screen.getByTestId('audit-doc-versions-doc-1'));

    await waitFor(() => {
      expect(knowledgeApi.listDocumentVersions).toHaveBeenCalledWith('doc-1');
    });
    expect(await screen.findByTestId('audit-version-row-doc-1-v2')).toBeInTheDocument();
  });
});
