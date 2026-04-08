import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { DocumentPreviewModal } from './DocumentPreviewModal';
import { DOCUMENT_SOURCE } from '../constants';

jest.mock('../../hooks/useEscapeClose', () => ({
  useEscapeClose: jest.fn(),
}));

jest.mock('../../preview/tablePreviewStyles', () => ({
  ensureTablePreviewStyles: jest.fn(),
}));

jest.mock('../../preview/markdownPreview', () => ({
  isMarkdownFilename: jest.fn(() => false),
  MarkdownPreview: ({ content }) => <div data-testid="markdown-preview">{content}</div>,
}));

jest.mock('../../preview/ragflowPreviewManager', () => ({
  loadDocumentPreview: jest.fn(),
}));

jest.mock('./OnlyOfficeViewer', () => (props) => (
  <div data-testid="onlyoffice-viewer">{props.serverUrl}</div>
));

jest.mock('./watermarkOverlay', () => ({
  ControlledPreviewBadge: ({ watermark }) => (
    <div data-testid="preview-watermark-badge">{watermark?.label || ''}</div>
  ),
  WatermarkedPreviewFrame: ({ children }) => (
    <div data-testid="watermarked-preview-frame">{children}</div>
  ),
}));

const { loadDocumentPreview } = jest.requireMock('../../preview/ragflowPreviewManager');

const encodeBase64 = (value) => Buffer.from(value, 'utf8').toString('base64');

const createDocumentApi = () => ({
  onlyofficeEditorConfig: jest.fn(),
  preview: jest.fn(),
  downloadBlob: jest.fn(),
});

describe('DocumentPreviewModal', () => {
  const originalCreateObjectURL = window.URL.createObjectURL;
  const originalRevokeObjectURL = window.URL.revokeObjectURL;

  beforeEach(() => {
    jest.clearAllMocks();
    window.URL.createObjectURL = jest.fn(() => 'blob:preview-1');
    window.URL.revokeObjectURL = jest.fn();
  });

  afterAll(() => {
    window.URL.createObjectURL = originalCreateObjectURL;
    window.URL.revokeObjectURL = originalRevokeObjectURL;
  });

  it('loads html previews through the preview session and revokes object urls on close', async () => {
    const documentApi = createDocumentApi();
    loadDocumentPreview.mockResolvedValue({
      type: 'html',
      filename: 'notes.html',
      content: encodeBase64('<html><body>preview</body></html>'),
      watermark: { label: '受控预览' },
    });

    const onClose = jest.fn();
    const { rerender } = render(
      <DocumentPreviewModal
        open
        target={{
          source: DOCUMENT_SOURCE.RAGFLOW,
          docId: 'doc-1',
          datasetName: 'KB-1',
          filename: 'notes.html',
        }}
        onClose={onClose}
        canDownloadFiles
        documentApi={documentApi}
      />
    );

    await waitFor(() => {
      expect(screen.getByTitle('html-preview')).toHaveAttribute('src', 'blob:preview-1');
    });
    expect(loadDocumentPreview).toHaveBeenCalled();

    rerender(
      <DocumentPreviewModal
        open={false}
        target={null}
        onClose={onClose}
        canDownloadFiles
        documentApi={documentApi}
      />
    );

    await waitFor(() => {
      expect(window.URL.revokeObjectURL).toHaveBeenCalledWith('blob:preview-1');
    });
  });

  it('routes office documents to onlyoffice config loading', async () => {
    const documentApi = createDocumentApi();
    documentApi.onlyofficeEditorConfig.mockResolvedValue({
      filename: 'report.docx',
      server_url: 'http://onlyoffice.local',
      config: { document: { title: 'report.docx' } },
      watermark: { label: '受控预览' },
    });

    render(
      <DocumentPreviewModal
        open
        target={{
          source: DOCUMENT_SOURCE.RAGFLOW,
          docId: 'doc-2',
          datasetName: 'KB-1',
          filename: 'report.docx',
        }}
        onClose={jest.fn()}
        canDownloadFiles
        documentApi={documentApi}
      />
    );

    await waitFor(() => {
      expect(screen.getByTestId('onlyoffice-viewer')).toHaveTextContent(
        'http://onlyoffice.local'
      );
    });
    expect(documentApi.onlyofficeEditorConfig).toHaveBeenCalledWith(
      expect.objectContaining({
        source: DOCUMENT_SOURCE.RAGFLOW,
        docId: 'doc-2',
        datasetName: 'KB-1',
        filename: 'report.docx',
      })
    );
    expect(loadDocumentPreview).not.toHaveBeenCalled();
  });

  it('can switch excel previews to original html rendering', async () => {
    const user = userEvent.setup();
    const documentApi = createDocumentApi();
    window.URL.createObjectURL = jest.fn(() => 'blob:excel-html');
    loadDocumentPreview.mockResolvedValue({
      type: 'excel',
      filename: 'table.xlsx',
      sheets: {
        Sheet1: '<table><tbody><tr><td>1</td></tr></tbody></table>',
      },
      watermark: { label: '受控预览' },
    });
    documentApi.preview.mockResolvedValue({
      type: 'html',
      filename: 'table.html',
      content: encodeBase64('<html><body>table</body></html>'),
      watermark: { label: '受控预览' },
    });

    render(
      <DocumentPreviewModal
        open
        target={{
          source: DOCUMENT_SOURCE.PATENT,
          docId: 'doc-3',
          sessionId: 'session-1',
          filename: 'table.xlsx',
        }}
        onClose={jest.fn()}
        canDownloadFiles
        documentApi={documentApi}
      />
    );

    await waitFor(() => {
      expect(screen.getByRole('button', { name: '原样预览 (HTML)' })).toBeInTheDocument();
    });

    await user.click(screen.getByRole('button', { name: '原样预览 (HTML)' }));

    await waitFor(() => {
        expect(documentApi.preview).toHaveBeenCalledWith(
          expect.objectContaining({
            source: DOCUMENT_SOURCE.PATENT,
            docId: 'doc-3',
            sessionId: 'session-1',
            render: 'html',
          })
        );
    });

    await waitFor(() => {
      expect(screen.getByTitle('html-preview')).toHaveAttribute('src', 'blob:excel-html');
    });
  });
});
