import { useCallback, useEffect, useMemo, useState } from 'react';
import { DOCUMENT_SOURCE } from '../../shared/documents/constants';
import { documentsApi } from '../documents/api';
import { useAuth } from '../../hooks/useAuth';
import { agentsApi } from './api';
import { knowledgeApi } from '../knowledge/api';
import { ensureTablePreviewStyles } from '../../shared/preview/tablePreviewStyles';
import { useEscapeClose } from '../../shared/hooks/useEscapeClose';
import useSearchHistory from './hooks/useSearchHistory';

const SEARCH_HISTORY_LIMIT = 10;
const MOBILE_BREAKPOINT = 768;
const PAGE_SIZE = 30;
const TOP_K = 30;

const ensureHighlightStyles = () => {
  if (typeof document === 'undefined' || document.getElementById('highlight-styles')) {
    return;
  }

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
};

const getInitialIsMobile = () => {
  if (typeof window === 'undefined') return false;
  return window.innerWidth <= MOBILE_BREAKPOINT;
};

export default function useAgentsPage() {
  const { user, canDownload } = useAuth();
  const canDownloadFiles = typeof canDownload === 'function' ? !!canDownload() : false;
  const [isMobile, setIsMobile] = useState(getInitialIsMobile);
  const [datasets, setDatasets] = useState([]);
  const [selectedDatasetIds, setSelectedDatasetIds] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewTarget, setPreviewTarget] = useState(null);
  const [page, setPage] = useState(1);
  const [similarityThreshold, setSimilarityThreshold] = useState(0.2);
  const [keyword, setKeyword] = useState(false);
  const [highlight, setHighlight] = useState(true);

  useEffect(() => {
    ensureHighlightStyles();
  }, []);

  useEffect(() => {
    ensureTablePreviewStyles();
  }, []);

  useEffect(() => {
    if (typeof window === 'undefined') return undefined;
    const handleResize = () => setIsMobile(window.innerWidth <= MOBILE_BREAKPOINT);
    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
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
      const rows = await knowledgeApi.listRagflowDatasets();
      setDatasets(Array.isArray(rows) ? rows : []);
      if (Array.isArray(rows) && rows.length) {
        setSelectedDatasetIds(rows.map((item) => item.id));
      }
    } catch (requestError) {
      setError(requestError?.message || '加载知识库失败');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchDatasets();
  }, [fetchDatasets]);

  const handleSearch = useCallback(async (queryOverride = null, pageOverride = null) => {
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
        page_size: PAGE_SIZE,
        similarity_threshold: similarityThreshold,
        top_k: TOP_K,
        keyword: false,
        highlight,
      });

      const chunks = Array.isArray(result?.chunks) ? result.chunks : [];
      const normalized = keyword
        ? (() => {
            const lowerQuery = query.toLowerCase();
            const filtered = chunks.filter((chunk) =>
              String(chunk?.content || '').toLowerCase().includes(lowerQuery)
            );
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

      if (query !== searchQuery) {
        setSearchQuery(query);
      }
      pushSearchHistory(query);
      setSearchResults(normalized);
    } catch (requestError) {
      setError(requestError?.message || '搜索失败');
    } finally {
      setLoading(false);
    }
  }, [highlight, keyword, page, pushSearchHistory, searchQuery, selectedDatasetIds, similarityThreshold]);

  const executeSearch = useCallback(() => {
    const value = String(searchQuery || '').trim();
    if (!value || loading) return;
    setPage(1);
    handleSearch(value, 1);
  }, [handleSearch, loading, searchQuery]);

  const handleHistorySearch = useCallback((query) => {
    const value = String(query || '').trim();
    if (!value || loading) return;
    setSearchQuery(value);
    setPage(1);
    handleSearch(value, 1);
  }, [handleSearch, loading]);

  const handlePageChange = useCallback((nextPage) => {
    if (loading || !searchResults) return;
    const pageNumber = Number(nextPage);
    if (!Number.isInteger(pageNumber) || pageNumber < 1) return;
    const total = Number(searchResults?.total || 0);
    const maxPage = total > 0 ? Math.ceil(total / PAGE_SIZE) : 1;
    if (pageNumber > maxPage) return;
    setPage(pageNumber);
    handleSearch(searchQuery, pageNumber);
  }, [handleSearch, loading, searchQuery, searchResults]);

  const toggleDataset = useCallback((datasetId) => {
    setSelectedDatasetIds((previous) => (
      previous.includes(datasetId)
        ? previous.filter((id) => id !== datasetId)
        : [...previous, datasetId]
    ));
  }, []);

  const selectAllDatasets = useCallback(() => {
    setSelectedDatasetIds(datasets.map((dataset) => dataset.id));
  }, [datasets]);

  const clearDatasetSelection = useCallback(() => {
    setSelectedDatasetIds([]);
  }, []);

  const resolveDatasetName = useCallback((datasetId) => {
    const dataset = datasets.find((item) => item.id === datasetId);
    return dataset ? dataset.name || dataset.id : '知识库';
  }, [datasets]);

  const handleDownloadDocument = useCallback(async (docId, docName, datasetId) => {
    try {
      setError(null);
      await documentsApi.downloadToBrowser({
        source: DOCUMENT_SOURCE.RAGFLOW,
        docId,
        datasetName: resolveDatasetName(datasetId),
        filename: docName,
      });
    } catch (requestError) {
      setError(`下载文档失败: ${requestError?.message || '未知错误'}`);
    }
  }, [resolveDatasetName]);

  const handlePreviewDocument = useCallback(async (docId, docName, datasetId) => {
    try {
      setError(null);
      setPreviewTarget({
        source: DOCUMENT_SOURCE.RAGFLOW,
        docId,
        datasetName: resolveDatasetName(datasetId),
        filename: docName,
      });
      setPreviewOpen(true);
    } catch (requestError) {
      setError(`预览文档失败: ${requestError?.message || '未知错误'}`);
    }
  }, [resolveDatasetName]);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  return {
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
    pageSize: PAGE_SIZE,
    similarityThreshold,
    keyword,
    highlight,
    searchHistory,
    setSearchQuery,
    setSimilarityThreshold,
    setKeyword,
    setHighlight,
    clearHistory: clearSearchHistory,
    removeHistoryItem: removeSearchHistoryItem,
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
  };
}
