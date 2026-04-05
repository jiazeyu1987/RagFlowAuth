import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import Agents from './Agents';
import { useAuth } from '../hooks/useAuth';
import { agentsApi } from '../features/agents/api';
import { knowledgeApi } from '../features/knowledge/api';

jest.mock('../hooks/useAuth', () => ({
  useAuth: jest.fn(),
}));

jest.mock('../features/agents/api', () => ({
  agentsApi: {
    searchChunks: jest.fn(),
  },
}));

jest.mock('../features/knowledge/api', () => ({
  knowledgeApi: {
    listRagflowDatasets: jest.fn(),
  },
}));

jest.mock('../features/documents/api', () => ({
  __esModule: true,
  DOCUMENT_SOURCE: {
    RAGFLOW: 'ragflow',
  },
  documentsApi: {
    downloadToBrowser: jest.fn(),
  },
}));

jest.mock('../shared/preview/tablePreviewStyles', () => ({
  ensureTablePreviewStyles: jest.fn(),
}));

jest.mock('../shared/hooks/useEscapeClose', () => ({
  useEscapeClose: jest.fn(),
}));

jest.mock('../shared/documents/preview/DocumentPreviewModal', () => ({
  DocumentPreviewModal: function MockDocumentPreviewModal() {
    return null;
  },
}));

jest.mock('../features/agents/hooks/useSearchHistory', () => ({
  __esModule: true,
  default: () => ({
    history: [],
    pushHistory: jest.fn(),
    clearHistory: jest.fn(),
    removeHistoryItem: jest.fn(),
  }),
}));

jest.mock('../features/agents/components/AgentsDatasetSidebar', () => function MockAgentsDatasetSidebar(props) {
  return (
    <div data-testid="agents-sidebar-state">
      {JSON.stringify({
        datasetIds: (props.datasets || []).map((item) => item.id),
        selectedDatasetIds: props.selectedDatasetIds || [],
      })}
    </div>
  );
});

jest.mock('../features/agents/components/AgentsSearchControls', () => function MockAgentsSearchControls(props) {
  return (
    <div>
      <input
        data-testid="agents-search-input"
        value={props.searchQuery}
        onChange={(event) => props.onSearchQueryChange(event.target.value)}
      />
      <button
        type="button"
        data-testid="agents-search-button"
        disabled={props.disableSearch}
        onClick={props.onSearch}
      >
        Search
      </button>
    </div>
  );
});

jest.mock('../features/agents/components/AgentsSearchResults', () => function MockAgentsSearchResults(props) {
  return <div data-testid="agents-results-state">{JSON.stringify(props.searchResults || null)}</div>;
});

describe('Agents', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    useAuth.mockReturnValue({
      user: { user_id: 'u-1', username: 'alice' },
      canDownload: () => true,
    });
    knowledgeApi.listRagflowDatasets.mockResolvedValue([
      { id: 'ds-1', name: 'KB 1' },
      { id: 'ds-2', name: 'KB 2' },
    ]);
    agentsApi.searchChunks.mockResolvedValue({
      chunks: [{ content: 'matched chunk' }],
      total: 1,
    });
  });

  it('loads datasets through knowledgeApi and searches with the selected dataset ids', async () => {
    render(<Agents />);

    await waitFor(() => {
      expect(knowledgeApi.listRagflowDatasets).toHaveBeenCalledTimes(1);
      expect(screen.getByTestId('agents-sidebar-state')).toHaveTextContent('"datasetIds":["ds-1","ds-2"]');
      expect(screen.getByTestId('agents-sidebar-state')).toHaveTextContent('"selectedDatasetIds":["ds-1","ds-2"]');
    });

    fireEvent.change(screen.getByTestId('agents-search-input'), {
      target: { value: 'capsule' },
    });

    await waitFor(() => expect(screen.getByTestId('agents-search-button')).not.toBeDisabled());

    fireEvent.click(screen.getByTestId('agents-search-button'));

    await waitFor(() => {
      expect(agentsApi.searchChunks).toHaveBeenCalledWith(
        expect.objectContaining({
          question: 'capsule',
          dataset_ids: ['ds-1', 'ds-2'],
          page: 1,
          page_size: 30,
        })
      );
    });
  });
});
