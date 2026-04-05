import React from 'react';
import { MemoryRouter } from 'react-router-dom';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import KnowledgeUpload from './KnowledgeUpload';
import { knowledgeUploadApi } from '../features/knowledge/upload/api';
import { knowledgeApi } from '../features/knowledge/api';
import { useAuth } from '../hooks/useAuth';

jest.mock('react-router-dom', () => {
  const actual = jest.requireActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => jest.fn(),
  };
});

jest.mock('../hooks/useAuth', () => ({
  useAuth: jest.fn(),
}));

jest.mock('../features/knowledge/api', () => ({
  knowledgeApi: {
    listRagflowDatasets: jest.fn(),
    listKnowledgeDirectories: jest.fn(),
  },
}));

jest.mock('../features/knowledge/upload/api', () => ({
  knowledgeUploadApi: {
    getAllowedExtensions: jest.fn(),
    uploadDocument: jest.fn(),
  },
}));

jest.mock('../features/knowledge/upload/components/UploadDropzone', () => function MockUploadDropzone(props) {
  return (
    <div>
      <input data-testid="mock-upload-input" type="file" multiple onChange={props.onFileSelect} />
    </div>
  );
});

jest.mock('../features/knowledge/upload/components/SelectedFilesList', () => function MockSelectedFilesList() {
  return <div data-testid="mock-selected-files-list" />;
});

jest.mock('../features/knowledge/upload/components/UploadExtensionsPanel', () => function MockUploadExtensionsPanel() {
  return <div data-testid="mock-upload-extensions-panel" />;
});

describe('KnowledgeUpload', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    useAuth.mockReturnValue({
      accessibleKbs: ['KB-1', 'ds-kb-1'],
      loading: false,
      canViewKbConfig: () => false,
    });
    knowledgeApi.listRagflowDatasets.mockResolvedValue([
      { id: 'ds-kb-1', name: 'KB-1' },
    ]);
    knowledgeApi.listKnowledgeDirectories.mockResolvedValue({
      nodes: [],
      datasets: [{ id: 'ds-kb-1', name: 'KB-1', node_id: null }],
    });
    knowledgeUploadApi.getAllowedExtensions.mockResolvedValue({
      allowed_extensions: ['.txt'],
    });
    knowledgeUploadApi.uploadDocument.mockResolvedValue({
      request_id: 'req-upload-1',
    });
  });

  it('shows approval request submitted after upload', async () => {
    const user = userEvent.setup();

    render(
      <MemoryRouter>
        <KnowledgeUpload />
      </MemoryRouter>
    );

    await screen.findByTestId('upload-submit');

    const file = new File(['hello'], 'demo.txt', { type: 'text/plain' });
    await user.upload(screen.getByTestId('mock-upload-input'), file);
    await user.click(screen.getByTestId('upload-submit'));

    await waitFor(() => {
      expect(knowledgeUploadApi.uploadDocument).toHaveBeenCalledWith(file, 'KB-1');
    });
    expect(await screen.findByTestId('upload-success')).toHaveTextContent('申请已提交');
  });
});
