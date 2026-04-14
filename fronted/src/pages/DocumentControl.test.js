import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import DocumentControl from './DocumentControl';
import documentControlApi from '../features/documentControl/api';

jest.mock('../features/documentControl/api', () => ({
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
  product_name: 'Product A',
  registration_ref: 'REG-001',
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
      change_summary: 'initial baseline',
    },
  ],
};

describe('DocumentControl page', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    documentControlApi.listDocuments.mockResolvedValue(listResponse);
    documentControlApi.getDocument.mockResolvedValue(detailResponse);
    documentControlApi.createDocument.mockResolvedValue({
      ...detailResponse,
      controlled_document_id: 'doc-2',
      doc_code: 'DOC-002',
      title: 'Controlled SRS',
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
          change_summary: 'rev 2',
        },
        detailResponse.revisions[0],
      ],
    });
    documentControlApi.transitionRevision.mockResolvedValue({
      ...detailResponse,
      current_revision: {
        controlled_revision_id: 'rev-1',
        revision_no: 1,
        status: 'in_review',
        filename: 'urs.md',
      },
      revisions: [
        {
          ...detailResponse.revisions[0],
          status: 'in_review',
        },
      ],
    });
  });

  it('loads list and detail content for controlled documents', async () => {
    render(<DocumentControl />);

    expect(await screen.findByTestId('document-control-page')).toBeInTheDocument();
    expect(await screen.findByText('Controlled URS')).toBeInTheDocument();
    expect(await screen.findByTestId('document-control-detail-doc-code')).toHaveTextContent(
      'DOC-001'
    );
  });

  it('supports search, document creation, revision creation, and transition actions', async () => {
    const user = userEvent.setup();
    render(<DocumentControl />);

    await screen.findByTestId('document-control-page');

    await user.type(screen.getByTestId('document-control-filter-query'), 'URS');
    await user.click(screen.getByTestId('document-control-search'));
    await waitFor(() =>
      expect(documentControlApi.listDocuments).toHaveBeenLastCalledWith(
        expect.objectContaining({ query: 'URS', limit: 100 })
      )
    );

    await user.type(screen.getByTestId('document-control-create-doc-code'), 'DOC-002');
    await user.type(screen.getByTestId('document-control-create-title'), 'Controlled SRS');
    await user.type(screen.getByTestId('document-control-create-document-type'), 'srs');
    await user.type(screen.getByTestId('document-control-create-target-kb'), 'Quality KB');
    await user.type(screen.getByTestId('document-control-create-product-name'), 'Product B');
    await user.type(screen.getByTestId('document-control-create-registration-ref'), 'REG-002');
    await user.upload(
      screen.getByTestId('document-control-create-file'),
      new File(['hello'], 'srs.md', { type: 'text/markdown' })
    );
    await user.click(screen.getByTestId('document-control-create-submit'));

    await waitFor(() => expect(documentControlApi.createDocument).toHaveBeenCalled());
    expect(await screen.findByTestId('document-control-success')).toHaveTextContent(
      'Controlled document created'
    );

    await user.upload(
      screen.getByTestId('document-control-revision-file'),
      new File(['rev2'], 'urs-v2.md', { type: 'text/markdown' })
    );
    await user.click(screen.getByTestId('document-control-revision-submit'));

    await waitFor(() => expect(documentControlApi.createRevision).toHaveBeenCalled());
    expect(await screen.findByTestId('document-control-success')).toHaveTextContent(
      'Revision created'
    );

    await user.click(screen.getByTestId('document-control-transition-rev-1-in_review'));
    await waitFor(() =>
      expect(documentControlApi.transitionRevision).toHaveBeenCalledWith('rev-1', {
        target_status: 'in_review',
      })
    );
  });

  it('requires product name and registration reference before creating a document', async () => {
    const user = userEvent.setup();
    render(<DocumentControl />);

    await screen.findByTestId('document-control-page');

    await user.type(screen.getByTestId('document-control-create-doc-code'), 'DOC-003');
    await user.type(screen.getByTestId('document-control-create-title'), 'Controlled WI');
    await user.type(screen.getByTestId('document-control-create-document-type'), 'wi');
    await user.type(screen.getByTestId('document-control-create-target-kb'), 'Quality KB');
    await user.upload(
      screen.getByTestId('document-control-create-file'),
      new File(['hello'], 'wi.md', { type: 'text/markdown' })
    );
    await user.click(screen.getByTestId('document-control-create-submit'));

    expect(documentControlApi.createDocument).not.toHaveBeenCalled();
    expect(await screen.findByTestId('document-control-error')).toHaveTextContent(
      'Please provide the product name.'
    );
  });
});
