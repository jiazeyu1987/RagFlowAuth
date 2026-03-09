import React, { useCallback, useEffect, useMemo, useState } from 'react';
import documentClient, { DOCUMENT_SOURCE } from '../shared/documents/documentClient';
import { useAuth } from '../hooks/useAuth';
import { agentsApi } from '../features/agents/api';
import { ensureTablePreviewStyles } from '../shared/preview/tablePreviewStyles';
import { useEscapeClose } from '../shared/hooks/useEscapeClose';
import { DocumentPreviewModal } from '../shared/documents/preview/DocumentPreviewModal';
import AgentsDatasetSidebar from '../features/agents/components/AgentsDatasetSidebar';
import AgentsSearchControls from '../features/agents/components/AgentsSearchControls';
import AgentsSearchResults from '../features/agents/components/AgentsSearchResults';
import useSearchHistory from '../features/agents/hooks/useSearchHistory';

const SEARCH_HISTORY_LIMIT = 10;

const Agents = () => {
  const { user, canDownload } = useAuth();
  const canDownloadFiles = typeof canDownload === 'function' ? !!canDownload() : false;

  const [datasets, setDatasets] = useState([]);
  const [selectedDatasetIds, setSelectedDatasetIds] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewTarget, setPreviewTarget] = useState(null);

  const [page, setPage] = useState(1);
  const [pageSize] = useState(30);
  const [similarityThreshold, setSimilarityThreshold] = useState(0.2);
  const [topK, setTopK] = useState(30);
  const [keyword, setKeyword] = useState(false);
  const [highlight, setHighlight] = useState(false);

  useEffect(() => {
    if (typeof document !== 'undefined' && !document.getElementById('highlight-styles')) {
      const style = document.createElement('style');
      style.id = 'highlight-styles';
      style.textContent = `
        .ragflow-highlight {
          background-color: #fef08a;
          font-weight: bold;
          padding: 2px 4px;
          border-radius: 2px;
        }
        em {
          background-color: #fef08a;
          font-weight: bold;
          font-style: normal;
          padding: 2px 4px;
          border-radius: 2px;
        }
      `;
      document.head.appendChild(style);
    }
  }, []);

  useEffect(() => {
    ensureTablePreviewStyles();
  }, []);

  const closePreviewModal = useCallback(() => {
    setPreviewOpen(false);
    setPreviewTarget(null);
  }, []);

  useEscapeClose(previewOpen, closePreviewModal);

  const searchHistoryStorageKey = useMemo(
    () => `ragflowauth_agents_search_history_v1:${user?.user_id || user?.username || 'anon'}`,
    [user?.user_id, user?.username]
  );

  const {
    history: searchHistory,
    pushHistory: pushSearchHistory,
    clearHistory: clearSearchHistory,
    removeHistoryItem: removeSearchHistoryItem,
  } = useSearchHistory(searchHistoryStorageKey, SEARCH_HISTORY_LIMIT);

  const fetchDatasets = useCallback(async () => {
    try {
      setLoading(true);
      const data = await agentsApi.getAvailableDatasets();
      const rows = Array.isArray(data?.datasets) ? data.datasets : [];
      setDatasets(rows);
      if (rows.length) {
        setSelectedDatasetIds(rows.map((item) => item.id));
      }
    } catch (err) {
      setError(err?.message || '加载知识库失败');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchDatasets();
  }, [fetchDatasets]);

  const handleSearch = useCallback(
    async (queryOverride = null, pageOverride = null) => {
      const query = String(queryOverride ?? searchQuery ?? '').trim();
      const nextPage = Number.isInteger(pageOverride) && pageOverride > 0 ? pageOverride : page;

      if (!query) {
        setError('请输入搜索关键词');
        return;
      }
      if (!selectedDatasetIds.length) {
        setError('请至少选择一个知识库');
        return;
      }

      setLoading(true);
      setError(null);

      try {
        const result = await agentsApi.searchChunks({
          question: query,
          dataset_ids: selectedDatasetIds,
          page: nextPage,
          page_size: pageSize,
          similarity_threshold: similarityThreshold,
          top_k: topK,
          keyword: false,
          highlight,
        });

        const chunks = Array.isArray(result?.chunks) ? result.chunks : [];
        const normalized = keyword
          ? (() => {
              const lowerQuery = query.toLowerCase();
              const filtered = chunks.filter((chunk) => String(chunk?.content || '').toLowerCase().includes(lowerQuery));
              return {
                ...result,
                chunks: filtered,
                total: filtered.length,
              };
            })()
          : {
              ...result,
              chunks,
            };

        if (query !== searchQuery) setSearchQuery(query);
        pushSearchHistory(query);
        setSearchResults(normalized);
      } catch (err) {
        setError(err?.message || '搜索失败');
      } finally {
        setLoading(false);
      }
    },
    [highlight, keyword, page, pageSize, pushSearchHistory, searchQuery, selectedDatasetIds, similarityThreshold, topK]
  );

  const executeSearch = useCallback(() => {
    const value = String(searchQuery || '').trim();
    if (!value || loading) return;
    setPage(1);
    handleSearch(value, 1);
  }, [handleSearch, loading, searchQuery]);

  const handleHistorySearch = useCallback(
    (query) => {
      const value = String(query || '').trim();
      if (!value || loading) return;
      setSearchQuery(value);
      setPage(1);
      handleSearch(value, 1);
    },
    [handleSearch, loading]
  );

  const handlePageChange = useCallback(
    (nextPage) => {
      if (loading || !searchResults) return;
      const pageNumber = Number(nextPage);
      if (!Number.isInteger(pageNumber) || pageNumber < 1) return;
      const total = Number(searchResults?.total || 0);
      const maxPage = total > 0 ? Math.ceil(total / pageSize) : 1;
      if (pageNumber > maxPage) return;
      setPage(pageNumber);
      handleSearch(searchQuery, pageNumber);
    },
    [handleSearch, loading, pageSize, searchQuery, searchResults]
  );

  const toggleDataset = useCallback((datasetId) => {
    setSelectedDatasetIds((prev) => (prev.includes(datasetId) ? prev.filter((id) => id !== datasetId) : [...prev, datasetId]));
  }, []);

  const selectAllDatasets = useCallback(() => {
    setSelectedDatasetIds(datasets.map((dataset) => dataset.id));
  }, [datasets]);

  const clearDatasetSelection = useCallback(() => {
    setSelectedDatasetIds([]);
  }, []);

  const handleDownloadDocument = useCallback(
    async (docId, docName, datasetId) => {
      try {
        setError(null);
        const dataset = datasets.find((item) => item.id === datasetId);
        const datasetName = dataset ? dataset.name || dataset.id : '展厅';
        await documentClient.downloadToBrowser({
          source: DOCUMENT_SOURCE.RAGFLOW,
          docId,
          datasetName,
          filename: docName,
        });
      } catch (err) {
        setError(`下载文档失败: ${err?.message || '未知错误'}`);
      }
    },
    [datasets]
  );

  const handlePreviewDocument = useCallback(
    async (docId, docName, datasetId) => {
      try {
        setError(null);
        const dataset = datasets.find((item) => item.id === datasetId);
        const datasetName = dataset ? dataset.name || dataset.id : '';
        setPreviewTarget({
          source: DOCUMENT_SOURCE.RAGFLOW,
          docId,
          datasetName,
          filename: docName,
        });
        setPreviewOpen(true);
      } catch (err) {
        setError(`预览文档失败: ${err?.message || '未知错误'}`);
      }
    },
    [datasets]
  );

  return (
    <div style={{ height: 'calc(100vh - 120px)', display: 'flex', gap: '16px' }}>
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
        }}
      >
        <AgentsSearchControls
          searchQuery={searchQuery}
          onSearchQueryChange={setSearchQuery}
          onSearch={executeSearch}
          loading={loading}
          searchHistory={searchHistory}
          onHistorySearch={handleHistorySearch}
          onClearHistory={clearSearchHistory}
          onRemoveHistoryItem={removeSearchHistoryItem}
          similarityThreshold={similarityThreshold}
          onSimilarityThresholdChange={setSimilarityThreshold}
          topK={topK}
          onTopKChange={setTopK}
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
            bottom: '20px',
            right: '20px',
            backgroundColor: '#fee2e2',
            color: '#991b1b',
            padding: '12px 16px',
            borderRadius: '4px',
            boxShadow: '0 2px 8px rgba(0, 0, 0, 0.1)',
            zIndex: 1000,
            maxWidth: '400px',
          }}
        >
          {error}
          <button
            type="button"
            onClick={() => setError(null)}
            style={{ marginLeft: '12px', background: 'none', border: 'none', color: '#991b1b', cursor: 'pointer' }}
          >
            ×
          </button>
        </div>
      ) : null}

      <DocumentPreviewModal
        open={previewOpen}
        target={previewTarget}
        onClose={closePreviewModal}
        canDownloadFiles={canDownloadFiles}
      />
    </div>
  );
};

export default Agents;
