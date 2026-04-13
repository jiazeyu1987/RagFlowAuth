import { act, renderHook, waitFor } from '@testing-library/react';
import useDocumentControlPage from './useDocumentControlPage';
import documentControlApi from './api';

jest.mock('./api', () => ({
  __esModule: true,
  default: {
    listDocuments: jest.fn(),
    getDocument: jest.fn(),
    createDocument: jest.fn(),
    createRevision: jest.fn(),
    transitionRevision: jest.fn(),
  },
}));

const listResponse = [
  {
    controlled_document_id: 'doc-1',
    doc_code: 'DOC-001',
    title: 'Controlled URS',
    current_revision: {
      controlled_revision_id: 'rev-1',
      revision_no: 1,
      status: 'draft',
      filename: 'urs.md',
    },
  },
];

const detailResponse = {
  controlled_document_id: 'doc-1',
  doc_code: 'DOC-001',
  title: 'Controlled URS',
  document_type: 'urs',
  target_kb_id: 'kb-quality',
  target_kb_name: 'Quality KB',
  current_revision: {
    controlled_revision_id: 'rev-1',
    revision_no: 1,
    status: 'draft',
    filename: 'urs.md',
  },
  effective_revision: null,
  revisions: [
    {
      controlled_revision_id: 'rev-1',
      revision_no: 1,
      status: 'draft',
      filename: 'urs.md',
      file_path: '/tmp/urs.md',
    },
  ],
};

describe('useDocumentControlPage', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    documentControlApi.listDocuments.mockResolvedValue(listResponse);
    documentControlApi.getDocument.mockResolvedValue(detailResponse);
    documentControlApi.createDocument.mockResolvedValue({
      ...detailResponse,
      controlled_document_id: 'doc-2',
      doc_code: 'DOC-002',
    });
    documentControlApi.createRevision.mockResolvedValue({
      ...detailResponse,
      current_revision: {
        controlled_revision_id: 'rev-2',
        revision_no: 2,
        status: 'draft',
        filename: 'urs-v2.md',
      },
      revisions: [
        {
          controlled_revision_id: 'rev-2',
          revision_no: 2,
          status: 'draft',
          filename: 'urs-v2.md',
          file_path: '/tmp/urs-v2.md',
        },
        {
          controlled_revision_id: 'rev-1',
          revision_no: 1,
          status: 'effective',
          filename: 'urs.md',
          file_path: '/tmp/urs.md',
        },
      ],
    });
    documentControlApi.transitionRevision.mockResolvedValue({
      ...detailResponse,
      current_revision: {
        controlled_revision_id: 'rev-1',
        revision_no: 1,
        status: 'effective',
        filename: 'urs.md',
      },
      effective_revision: {
        controlled_revision_id: 'rev-1',
        revision_no: 1,
        status: 'effective',
        filename: 'urs.md',
      },
      revisions: [
        {
          controlled_revision_id: 'rev-1',
          revision_no: 1,
          status: 'effective',
          filename: 'urs.md',
          file_path: '/tmp/urs.md',
        },
      ],
    });
  });

  it('loads list and detail state, then reloads with search filters', async () => {
    const { result } = renderHook(() => useDocumentControlPage());

    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.documents).toHaveLength(1);
    expect(result.current.selectedDocument?.controlled_document_id).toBe('doc-1');
    expect(documentControlApi.listDocuments).toHaveBeenCalledWith({
      limit: 100,
      query: '',
      docCode: '',
      title: '',
      documentType: '',
      productName: '',
      registrationRef: '',
      status: '',
    });
    expect(documentControlApi.getDocument).toHaveBeenCalledWith('doc-1');

    act(() => {
      result.current.handleFilterChange('query', 'URS');
    });

    await act(async () => {
      await result.current.handleSearch();
    });

    expect(documentControlApi.listDocuments).toHaveBeenLastCalledWith({
      limit: 100,
      query: 'URS',
      docCode: '',
      title: '',
      documentType: '',
      productName: '',
      registrationRef: '',
      status: '',
    });
  });

  it('fails fast on missing files and updates state after create and transition actions', async () => {
    const { result } = renderHook(() => useDocumentControlPage());

    await waitFor(() => expect(result.current.loading).toBe(false));

    await act(async () => {
      await result.current.handleCreateDocument();
    });
    expect(result.current.error).toBe('file_required');

    act(() => {
      result.current.setDocumentForm((previous) => ({
        ...previous,
        doc_code: 'DOC-002',
        title: 'Controlled SRS',
        document_type: 'srs',
        target_kb_id: 'Quality KB',
        file: new File(['hello'], 'srs.md', { type: 'text/markdown' }),
      }));
    });

    await act(async () => {
      await result.current.handleCreateDocument();
    });
    expect(documentControlApi.createDocument).toHaveBeenCalled();
    expect(result.current.success).toBe('Controlled document created');

    act(() => {
      result.current.setRevisionForm((previous) => ({
        ...previous,
        change_summary: 'rev 2',
        file: new File(['hello'], 'srs-v2.md', { type: 'text/markdown' }),
      }));
    });

    await act(async () => {
      await result.current.handleCreateRevision();
    });
    expect(documentControlApi.createRevision).toHaveBeenCalled();
    expect(result.current.success).toBe('Revision created');

    await act(async () => {
      await result.current.handleTransitionRevision('rev-1', 'effective');
    });
    expect(documentControlApi.transitionRevision).toHaveBeenCalledWith('rev-1', {
      target_status: 'effective',
    });
    expect(result.current.selectedDocument?.effective_revision?.status).toBe('effective');
  });
});
