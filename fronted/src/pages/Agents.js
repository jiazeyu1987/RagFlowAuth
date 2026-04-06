import React from 'react';
import { documentsApi } from '../features/documents/api';
import { DocumentPreviewModal } from '../shared/documents/preview/DocumentPreviewModal';
import AgentsDatasetSidebar from '../features/agents/components/AgentsDatasetSidebar';
import AgentsSearchControls from '../features/agents/components/AgentsSearchControls';
import AgentsSearchResults from '../features/agents/components/AgentsSearchResults';
import useAgentsPage from '../features/agents/useAgentsPage';

const Agents = () => {
  const {
    canDownloadFiles,
    isMobile,
    datasets,
    selectedDatasetIds,
    searchQuery,
    searchResults,
    loading,
    error,
    previewOpen,
    previewTarget,
    page,
    pageSize,
    similarityThreshold,
    keyword,
    highlight,
    searchHistory,
    setSearchQuery,
    setSimilarityThreshold,
    setKeyword,
    setHighlight,
    clearHistory,
    removeHistoryItem,
    closePreviewModal,
    executeSearch,
    handleHistorySearch,
    handlePageChange,
    toggleDataset,
    selectAllDatasets,
    clearDatasetSelection,
    handleDownloadDocument,
    handlePreviewDocument,
    clearError,
  } = useAgentsPage();

  return (
    <div
      style={{
        height: isMobile ? 'auto' : 'calc(100vh - 120px)',
        minHeight: isMobile ? 'calc(100vh - 160px)' : undefined,
        display: 'flex',
        flexDirection: isMobile ? 'column' : 'row',
        gap: '16px',
      }}
    >
      <AgentsDatasetSidebar
        datasets={datasets}
        selectedDatasetIds={selectedDatasetIds}
        onToggleDataset={toggleDataset}
        onSelectAll={selectAllDatasets}
        onClearSelection={clearDatasetSelection}
      />

      <div
        style={{
          flex: 1,
          backgroundColor: 'white',
          borderRadius: '8px',
          boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
          minWidth: 0,
          minHeight: isMobile ? '58vh' : 0,
        }}
      >
        <AgentsSearchControls
          searchQuery={searchQuery}
          onSearchQueryChange={setSearchQuery}
          onSearch={executeSearch}
          loading={loading}
          searchHistory={searchHistory}
          onHistorySearch={handleHistorySearch}
          onClearHistory={clearHistory}
          onRemoveHistoryItem={removeHistoryItem}
          similarityThreshold={similarityThreshold}
          onSimilarityThresholdChange={setSimilarityThreshold}
          keyword={keyword}
          onKeywordChange={setKeyword}
          highlight={highlight}
          onHighlightChange={setHighlight}
          disableSearch={!searchQuery.trim() || !selectedDatasetIds.length || loading}
        />

        <AgentsSearchResults
          searchResults={searchResults}
          page={page}
          pageSize={pageSize}
          loading={loading}
          searchQuery={searchQuery}
          highlight={highlight}
          canDownloadFiles={canDownloadFiles}
          onPreviewDocument={handlePreviewDocument}
          onDownloadDocument={handleDownloadDocument}
          onPageChange={handlePageChange}
        />
      </div>

      {error ? (
        <div
          data-testid="agents-error"
          style={{
            position: 'fixed',
            bottom: isMobile ? '12px' : '20px',
            right: isMobile ? '12px' : '20px',
            left: isMobile ? '12px' : 'auto',
            backgroundColor: '#fee2e2',
            color: '#991b1b',
            padding: '12px 16px',
            borderRadius: '4px',
            boxShadow: '0 2px 8px rgba(0, 0, 0, 0.1)',
            zIndex: 1000,
            maxWidth: isMobile ? 'none' : '400px',
          }}
        >
          {error}
          <button
            type="button"
            onClick={clearError}
            style={{
              marginLeft: '12px',
              background: 'none',
              border: 'none',
              color: '#991b1b',
              cursor: 'pointer',
            }}
          >
            关闭
          </button>
        </div>
      ) : null}

      <DocumentPreviewModal
        open={previewOpen}
        target={previewTarget}
        onClose={closePreviewModal}
        canDownloadFiles={canDownloadFiles}
        documentApi={documentsApi}
      />
    </div>
  );
};

export default Agents;
