import React, { useCallback, useEffect, useMemo, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeRaw from 'rehype-raw';
import rehypeSanitize from 'rehype-sanitize';
import documentClient, { DOCUMENT_SOURCE } from '../shared/documents/documentClient';
import { useAuth } from '../hooks/useAuth';
import { agentsApi } from '../features/agents/api';
import { ensureTablePreviewStyles } from '../shared/preview/tablePreviewStyles';
import { useEscapeClose } from '../shared/hooks/useEscapeClose';
import { DocumentPreviewModal } from '../shared/documents/preview/DocumentPreviewModal';

const Agents = () => {
  const { canDownload } = useAuth();
  const canDownloadFiles = typeof canDownload === 'function' ? !!canDownload() : false;
  const [datasets, setDatasets] = useState([]);
  const [selectedDatasetIds, setSelectedDatasetIds] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Preview states (shared modal)
  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewTarget, setPreviewTarget] = useState(null);

  // Search parameters
  const [page, setPage] = useState(1);
  const [pageSize] = useState(30);
  const [similarityThreshold, setSimilarityThreshold] = useState(0.2);
  const [topK, setTopK] = useState(30);
  const [keyword, setKeyword] = useState(false);
  const [highlight, setHighlight] = useState(false);

  // Inject highlight styles
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

  // Inject shared table styles for Excel/CSV preview
  useEffect(() => {
    ensureTablePreviewStyles();
  }, []);

  const closePreviewModal = useCallback(() => {
    setPreviewOpen(false);
    setPreviewTarget(null);
  }, []);

  useEscapeClose(previewOpen, closePreviewModal);

  // Load available datasets on mount
  useEffect(() => {
    fetchDatasets();
  }, []);

  const fetchDatasets = async () => {
    try {
      setLoading(true);
      const data = await agentsApi.getAvailableDatasets();
      setDatasets(data.datasets || []);

      // Select all datasets by default
      if (data.datasets && data.datasets.length > 0) {
        setSelectedDatasetIds(data.datasets.map(ds => ds.id));
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = async () => {
    if (!searchQuery.trim()) {
      setError('请输入搜索关键词');
      return;
    }

    if (selectedDatasetIds.length === 0) {
      setError('请至少选择一个知识库');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const result = await agentsApi.searchChunks({
        question: searchQuery,
        dataset_ids: selectedDatasetIds,
        page,
        page_size: pageSize,
        similarity_threshold: similarityThreshold,
        top_k: topK,
        keyword: false, // Always use semantic search for better results
        highlight
      });

      // Debug: Check if chunks contain the search query
      if (result.chunks && result.chunks.length > 0) {
        console.log('=== SEARCH RESULT DEBUG ===');
        console.log('[DEBUG] Semantic search returned chunks:', result.chunks.length);
        console.log('[DEBUG] User checked "keyword matching":', keyword);
        console.log('[DEBUG] Search query:', searchQuery);
        console.log('[DEBUG] Checking which chunks contain the search query...');

        let chunksWithKeyword = 0;
        result.chunks.forEach((chunk, index) => {
          const content = chunk.content || '';
          const containsQuery = content.toLowerCase().includes(searchQuery.toLowerCase());
          if (containsQuery) chunksWithKeyword++;
          console.log(`[DEBUG] Chunk ${index}: contains "${searchQuery}" = ${containsQuery}`);

          if (index < 3) { // Show preview for first 3 chunks
            console.log(`[DEBUG] Chunk ${index} preview:`, content.substring(0, 80));
          }
        });

        console.log(`[DEBUG] Total chunks containing keyword: ${chunksWithKeyword}`);

        // If keyword matching checkbox is checked, filter to show only chunks with the keyword
        if (keyword) {
          const filteredChunks = result.chunks.filter(chunk => {
            const content = chunk.content || '';
            return content.toLowerCase().includes(searchQuery.toLowerCase());
          });

          console.log(`[DEBUG] Frontend filter: removed ${result.chunks.length - filteredChunks.length} chunks without keyword`);
          console.log(`[DEBUG] Displaying: ${filteredChunks.length} chunks`);

          // Update the result with filtered chunks
          result.chunks = filteredChunks;
          result.total = filteredChunks.length;
        } else {
          console.log(`[DEBUG] Displaying all ${result.chunks.length} chunks (semantic matching)`);
        }

        console.log('=========================');
      }

      setSearchResults(result);
    } catch (err) {
      console.error('=== SEARCH ERROR ===');
      console.error('[ERROR] Search failed:', err);
      console.error('[ERROR] Error message:', err.message);
      console.error('[ERROR] Error stack:', err.stack);
      console.error('====================');
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter') {
      handleSearch();
    }
  };

  const toggleDataset = (datasetId) => {
    setSelectedDatasetIds(prev =>
      prev.includes(datasetId)
        ? prev.filter(id => id !== datasetId)
        : [...prev, datasetId]
    );
  };

  const selectAllDatasets = () => {
    setSelectedDatasetIds(datasets.map(ds => ds.id));
  };

  const clearDatasetSelection = () => {
    setSelectedDatasetIds([]);
  };

  const handleDownloadDocument = async (docId, docName, datasetId) => {
    try {
      setError(null);

      const dataset = datasets.find(ds => ds.id === datasetId);
      const datasetName = dataset ? (dataset.name || dataset.id) : '展厅';

      await documentClient.downloadToBrowser({
        source: DOCUMENT_SOURCE.RAGFLOW,
        docId,
        datasetName,
        filename: docName,
      });
    } catch (err) {
      setError(`下载文档失败: ${err.message}`);
    }
  };

  const handlePreviewDocument = async (docId, docName, datasetId) => {
    try {
      setError(null);

      const datasetSafe = datasets.find((ds) => ds.id === datasetId);
      const datasetNameSafe = datasetSafe ? datasetSafe.name || datasetSafe.id : '';
      setPreviewTarget({
        source: DOCUMENT_SOURCE.RAGFLOW,
        docId,
        datasetName: datasetNameSafe,
        filename: docName,
      });
      setPreviewOpen(true);
      return;
    } catch (err) {
      setError(`预览文档失败: ${err.message}`);
    } finally {
    }
  };

  const normalizeInlinePipeKvTables = useMemo(() => {
    const makeTable = (pairs) => {
      const rows = pairs
        .filter((p) => p && typeof p.key === 'string' && typeof p.value === 'string')
        .map((p) => `| ${p.key} | ${p.value} |`);
      if (rows.length === 0) return '';
      return ['| 属性 | 值 |', '|---|---|', ...rows].join('\n');
    };

    return (text) => {
      const input = String(text ?? '');
      if (!input.includes('|')) return input;
      const lines = input.split('\n');
      const out = [];

      for (const line of lines) {
        const raw = String(line ?? '');
        const trimmed = raw.trim();

        // Only rewrite a "single line" pseudo-table like:
        // | 注册证名称 | / | | 注册证号 | xxx | | 生效时间 | ... |
        // into a real 2-column markdown table.
        if (
          trimmed.startsWith('|') &&
          trimmed.includes('|') &&
          !trimmed.includes('|---') &&
          !trimmed.includes('<table') &&
          !trimmed.includes('</table>')
        ) {
          const tokens = trimmed
            .split('|')
            .map((t) => t.trim())
            .filter((t) => t.length > 0);

          // Must be key/value pairs.
          // Some sources end with an "empty value" like: "| 备注 | |"
          // which becomes an odd-length token array after filtering empties.
          if (tokens.length >= 3 && tokens.length % 2 === 1) tokens.push('');

          if (tokens.length >= 4 && tokens.length % 2 === 0) {
            const pairs = [];
            for (let i = 0; i < tokens.length; i += 2) {
              const key = tokens[i];
              const value = tokens[i + 1] ?? '';
              pairs.push({ key, value });
            }
            const table = makeTable(pairs);
            if (table) {
              out.push(table);
              continue;
            }
          }
        }

        out.push(raw);
      }

      return out.join('\n');
    };
  }, []);

  const markdownComponents = useMemo(
    () => ({
      p: ({ node, ...props }) => <p style={{ margin: '0 0 10px 0' }} {...props} />,
      ul: ({ node, ...props }) => <ul style={{ margin: '0 0 10px 18px' }} {...props} />,
      ol: ({ node, ...props }) => <ol style={{ margin: '0 0 10px 18px' }} {...props} />,
      table: ({ node, ...props }) => (
        <table
          style={{
            width: '100%',
            borderCollapse: 'collapse',
            margin: '8px 0 12px 0',
            fontSize: '0.9rem',
          }}
          {...props}
        />
      ),
      th: ({ node, ...props }) => (
        <th
          style={{
            border: '1px solid #e5e7eb',
            padding: '8px 10px',
            textAlign: 'left',
            background: '#f9fafb',
            fontWeight: 600,
          }}
          {...props}
        />
      ),
      td: ({ node, ...props }) => (
        <td
          style={{
            border: '1px solid #e5e7eb',
            padding: '8px 10px',
            verticalAlign: 'top',
            whiteSpace: 'pre-wrap',
          }}
          {...props}
        />
      ),
      code: ({ node, inline, className, children, ...props }) => (
        <code
          className={className}
          style={
            inline
              ? {
                  padding: '0 6px',
                  borderRadius: '6px',
                  background: '#e5e7eb',
                }
              : undefined
          }
          {...props}
        >
          {children}
        </code>
      ),
      pre: ({ node, ...props }) => (
        <pre
          style={{
            margin: '0 0 10px 0',
            padding: '10px 12px',
            background: '#111827',
            color: '#f9fafb',
            borderRadius: '8px',
            overflowX: 'auto',
          }}
          {...props}
        />
      ),
      a: ({ node, ...props }) => (
        <a {...props} target="_blank" rel="noreferrer" style={{ color: '#2563eb', textDecoration: 'underline' }}>
          {props.children}
        </a>
      ),
    }),
    []
  );

  // Manual highlight function as fallback
  const highlightText = (text, query) => {
    if (!query || !text) {
      console.log('[HIGHLIGHT] Skipping - query:', query, 'text:', text ? 'exists' : 'empty');
      return text;
    }

    console.log('[HIGHLIGHT] ========== START ==========');
    console.log('[HIGHLIGHT] Query:', query);
    console.log('[HIGHLIGHT] Text preview (first 150 chars):', text.substring(0, 150));
    console.log('[HIGHLIGHT] Query length:', query.length);
    console.log('[HIGHLIGHT] Text length:', text.length);

    // Check if query exists in text at all
    const queryExists = text.toLowerCase().includes(query.toLowerCase());
    console.log('[HIGHLIGHT] Query exists in text (case-insensitive):', queryExists);

    // Try exact match first
    const escapedQuery = query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    console.log('[HIGHLIGHT] Escaped query:', escapedQuery);

    const regex = new RegExp(`(${escapedQuery})`, 'gi');

    // Test the regex
    const match = text.match(regex);
    console.log('[HIGHLIGHT] Regex match result:', match);
    console.log('[HIGHLIGHT] Number of matches:', match ? match.length : 0);

    const result = text.replace(regex, '<em>$1</em>');
    console.log('[HIGHLIGHT] Result has <em> tags:', result.includes('<em>'));
    console.log('[HIGHLIGHT] Result preview (first 200 chars):', result.substring(0, 200));
    console.log('[HIGHLIGHT] ========== END ==========');

    return result;
  };

  return (
    <div style={{ height: 'calc(100vh - 120px)', display: 'flex', gap: '16px' }}>
      {/* Left sidebar: Dataset selection */}
      <div style={{ width: '280px', display: 'flex', flexDirection: 'column' }}>
        <div style={{
          backgroundColor: 'white',
          borderRadius: '8px',
          padding: '16px',
          boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
          height: '100%',
          overflowY: 'auto'
        }}>
          <h3 style={{ margin: '0 0 12px 0', fontSize: '1rem' }}>知识库</h3>

          <div style={{ marginBottom: '12px', display: 'flex', gap: '8px' }}>
            <button
              onClick={selectAllDatasets}
              style={{
                flex: 1,
                padding: '6px',
                fontSize: '0.75rem',
                backgroundColor: '#3b82f6',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer'
              }}
            >
              全选
            </button>
            <button
              onClick={clearDatasetSelection}
              style={{
                flex: 1,
                padding: '6px',
                fontSize: '0.75rem',
                backgroundColor: '#9ca3af',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer'
              }}
            >
              清空
            </button>
          </div>

          {datasets.length === 0 ? (
            <div style={{ color: '#6b7280', textAlign: 'center', padding: '20px' }}>
              暂无可用知识库
            </div>
          ) : (
            datasets.map(dataset => (
              <div
                key={dataset.id}
                onClick={() => toggleDataset(dataset.id)}
                style={{
                  padding: '10px',
                  marginBottom: '8px',
                  borderRadius: '4px',
                  cursor: 'pointer',
                  backgroundColor: selectedDatasetIds.includes(dataset.id) ? '#3b82f6' : '#f3f4f6',
                  color: selectedDatasetIds.includes(dataset.id) ? 'white' : '#1f2937',
                  border: selectedDatasetIds.includes(dataset.id) ? '2px solid #2563eb' : '1px solid #e5e7eb',
                  fontSize: '0.875rem'
                }}
              >
                <div style={{ fontWeight: 'bold', marginBottom: '4px' }}>
                  {dataset.name || dataset.id}
                </div>
                {dataset.description && (
                  <div style={{
                    fontSize: '0.75rem',
                    color: selectedDatasetIds.includes(dataset.id) ? 'rgba(255,255,255,0.8)' : '#6b7280'
                  }}>
                    {dataset.description}
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      </div>

      {/* Main content: Search and results */}
      <div style={{
        flex: 1,
        backgroundColor: 'white',
        borderRadius: '8px',
        boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden'
      }}>
        {/* Search header */}
        <div style={{
          padding: '16px',
          borderBottom: '1px solid #e5e7eb',
          backgroundColor: '#f9fafb'
        }}>
          <div style={{ marginBottom: '12px' }}>
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="输入搜索关键词或问题..."
              disabled={loading}
              style={{
                width: '100%',
                padding: '10px 12px',
                border: '1px solid #d1d5db',
                borderRadius: '4px',
                fontSize: '0.875rem',
                boxSizing: 'border-box'
              }}
            />
          </div>

          {/* Search options */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))',
            gap: '12px',
            marginBottom: '12px'
          }}>
            <div>
              <label style={{ fontSize: '0.75rem', color: '#6b7280', display: 'block', marginBottom: '4px' }}>
                相似度阈值: {similarityThreshold}
              </label>
              <input
                type="range"
                min="0"
                max="1"
                step="0.05"
                value={similarityThreshold}
                onChange={(e) => setSimilarityThreshold(parseFloat(e.target.value))}
                style={{ width: '100%' }}
              />
            </div>

            <div>
              <label style={{ fontSize: '0.75rem', color: '#6b7280', display: 'block', marginBottom: '4px' }}>
                Top-K: {topK}
              </label>
              <input
                type="number"
                min="1"
                max="1024"
                value={topK}
                onChange={(e) => setTopK(parseInt(e.target.value) || 30)}
                style={{
                  width: '100%',
                  padding: '6px',
                  border: '1px solid #d1d5db',
                  borderRadius: '4px',
                  fontSize: '0.875rem'
                }}
              />
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
              <label style={{ display: 'flex', alignItems: 'center', fontSize: '0.875rem', cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={keyword}
                  onChange={(e) => setKeyword(e.target.checked)}
                  style={{ marginRight: '6px' }}
                />
                关键词匹配
              </label>

              <label style={{ display: 'flex', alignItems: 'center', fontSize: '0.875rem', cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={highlight}
                  onChange={(e) => setHighlight(e.target.checked)}
                  style={{ marginRight: '6px' }}
                />
                高亮匹配
              </label>
            </div>
          </div>

          <button
            onClick={handleSearch}
            disabled={!searchQuery.trim() || selectedDatasetIds.length === 0 || loading}
            style={{
              width: '100%',
              padding: '10px',
              backgroundColor: (!searchQuery.trim() || selectedDatasetIds.length === 0 || loading) ? '#9ca3af' : '#3b82f6',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: (!searchQuery.trim() || selectedDatasetIds.length === 0 || loading) ? 'not-allowed' : 'pointer',
              fontSize: '0.875rem',
              fontWeight: 'bold'
            }}
          >
            {loading ? '搜索中...' : '搜索'}
          </button>
        </div>

        {/* Search results */}
        <div style={{
          flex: 1,
          overflowY: 'auto',
          padding: '16px'
        }}>
          {!searchResults ? (
            <div style={{
              textAlign: 'center',
              color: '#9ca3af',
              marginTop: '60px'
            }}>
              <div style={{ fontSize: '3rem', marginBottom: '12px' }}>🔍</div>
              <div>输入关键词开始搜索知识库</div>
            </div>
          ) : searchResults.chunks && searchResults.chunks.length > 0 ? (
            <>
              <div style={{
                marginBottom: '16px',
                padding: '12px',
                backgroundColor: '#f0f9ff',
                borderRadius: '4px',
                color: '#0369a1',
                fontSize: '0.875rem'
              }}>
                找到 {searchResults.total || 0} 个结果 (第 {page} 页)
              </div>

              {searchResults.chunks.map((chunk, index) => {
                // Extract document info - handle multiple possible field names
                const docId = chunk.document_id || chunk.doc_id || chunk.docid;
                const docName = chunk.document_name || chunk.doc_name || chunk.docname || chunk.filename || chunk.document_keyword;
                const datasetId = chunk.dataset_id || chunk.dataset || chunk.kb_id;

                // Choose content based on highlight setting
                const rawContent = String(chunk.content || '');
                let displayContent = rawContent;

                const looksLikeMarkdown = (() => {
                  const name = String(docName || '').toLowerCase().trim();
                  if (name.endsWith('.md') || name.endsWith('.markdown')) return true;
                  const t = rawContent;
                  if (!t) return false;
                  // Headings / tables / lists
                  if (/^#{1,6}\s+/m.test(t)) return true;
                  if (/\n\|.*\|\n\|[-:| ]+\|/m.test(t) || /\|[-:| ]+\|/m.test(t)) return true; // has table divider
                  if (/^\s*[-*+]\s+/m.test(t) || /^\s*\d+\.\s+/m.test(t)) return true;
                  return false;
                })();

                // Debug: Log content info
                if (index === 0) {
                  console.log('=== CHUNK DEBUG ===');
                  console.log('[DEBUG] Chunk index:', index);
                  console.log('[DEBUG] highlight checkbox state:', highlight);
                  console.log('[DEBUG] searchQuery value:', searchQuery);
                  console.log('[DEBUG] searchQuery type:', typeof searchQuery);
                  console.log('[DEBUG] content_with_weight exists:', !!chunk.content_with_weight);
                  console.log('[DEBUG] content exists:', !!chunk.content);
                  console.log('[DEBUG] content length:', displayContent.length);
                  console.log('[DEBUG] Should use manual highlight:', highlight && !chunk.content_with_weight);
                  console.log('==================');
                }

                // If highlight is enabled and backend didn't return highlighted content, do it manually
                if (!looksLikeMarkdown && highlight && !chunk.content_with_weight) {
                  displayContent = highlightText(displayContent, searchQuery);
                } else if (!looksLikeMarkdown && chunk.content_with_weight) {
                  displayContent = chunk.content_with_weight;
                }

                return (
                <div
                  key={index}
                  style={{
                    padding: '16px',
                    marginBottom: '12px',
                    border: '1px solid #e5e7eb',
                    borderRadius: '6px',
                    backgroundColor: '#fafafa'
                  }}
                >
                  <div style={{
                    marginBottom: '8px',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    flexWrap: 'wrap',
                    gap: '8px'
                  }}>
                    <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', alignItems: 'center' }}>
                      {docName && (
                        <span style={{
                          fontSize: '0.875rem',
                          fontWeight: 'bold',
                          color: '#1f2937',
                          backgroundColor: '#f3f4f6',
                          padding: '4px 10px',
                          borderRadius: '4px',
                          marginRight: '8px',
                          border: '1px solid #e5e7eb'
                        }}>
                          📄 {docName}
                        </span>
                      )}
                      {chunk.similarity !== undefined && (
                        <span style={{
                          fontSize: '0.75rem',
                          color: '#059669',
                          backgroundColor: '#d1fae5',
                          padding: '4px 8px',
                          borderRadius: '4px',
                          fontWeight: '500'
                        }}>
                          相似度: {(chunk.similarity * 100).toFixed(1)}%
                        </span>
                      )}
                    </div>

                    <div style={{ display: 'flex', gap: '8px' }}>
                      {docId && (
                        <button
                          onClick={() => handlePreviewDocument(docId, docName, datasetId)}
                          data-testid={`agents-doc-view-${String(datasetId || '')}-${String(docId || '')}`}
                          style={{
                            padding: '6px 14px',
                            fontSize: '0.875rem',
                            backgroundColor: '#3b82f6',
                            color: 'white',
                            border: 'none',
                            borderRadius: '4px',
                            cursor: 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '6px',
                            fontWeight: '500'
                          }}
                          onMouseEnter={(e) => e.target.style.backgroundColor = '#2563eb'}
                          onMouseLeave={(e) => e.target.style.backgroundColor = '#3b82f6'}
                          title="查看文件内容"
                        >
                          👁️ 查看
                        </button>
                      )}
                      {docId && canDownloadFiles && (
                        <button
                          onClick={() => handleDownloadDocument(docId, docName, datasetId)}
                          style={{
                            padding: '6px 14px',
                            fontSize: '0.875rem',
                            backgroundColor: '#059669',
                            color: 'white',
                            border: 'none',
                            borderRadius: '4px',
                            cursor: 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '6px',
                            fontWeight: '500'
                          }}
                          onMouseEnter={(e) => e.target.style.backgroundColor = '#047857'}
                          onMouseLeave={(e) => e.target.style.backgroundColor = '#059669'}
                          title="下载完整源文件"
                        >
                          ⬇️ 下载
                        </button>
                      )}
                    </div>
                  </div>

                  {looksLikeMarkdown ? (
                    <div style={{ fontSize: '0.9rem', lineHeight: 1.65, color: '#111827' }}>
                      <ReactMarkdown components={markdownComponents} remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeRaw, rehypeSanitize]}>
                        {normalizeInlinePipeKvTables(rawContent)}
                      </ReactMarkdown>
                    </div>
                  ) : (
                    <div
                      style={{
                        fontSize: '0.875rem',
                        lineHeight: '1.6',
                        color: '#1f2937',
                        whiteSpace: 'pre-wrap'
                      }}
                      dangerouslySetInnerHTML={{
                        __html: displayContent
                      }}
                    />
                  )}
                </div>
                );
              })}

              {/* Pagination */}
              {searchResults.total && searchResults.total > pageSize && (
                <div style={{
                  display: 'flex',
                  justifyContent: 'center',
                  alignItems: 'center',
                  gap: '12px',
                  marginTop: '16px',
                  paddingTop: '16px',
                  borderTop: '1px solid #e5e7eb'
                }}>
                  <button
                    onClick={() => setPage(p => Math.max(1, p - 1))}
                    disabled={page <= 1 || loading}
                    style={{
                      padding: '6px 12px',
                      backgroundColor: page <= 1 || loading ? '#9ca3af' : '#3b82f6',
                      color: 'white',
                      border: 'none',
                      borderRadius: '4px',
                      cursor: page <= 1 || loading ? 'not-allowed' : 'pointer',
                      fontSize: '0.875rem'
                    }}
                  >
                    上一页
                  </button>

                  <span style={{ fontSize: '0.875rem', color: '#6b7280' }}>
                    第 {page} / {Math.ceil(searchResults.total / pageSize)} 页
                  </span>

                  <button
                    onClick={() => {
                      setPage(p => p + 1);
                      handleSearch();
                    }}
                    disabled={page >= Math.ceil(searchResults.total / pageSize) || loading}
                    style={{
                      padding: '6px 12px',
                      backgroundColor: page >= Math.ceil(searchResults.total / pageSize) || loading ? '#9ca3af' : '#3b82f6',
                      color: 'white',
                      border: 'none',
                      borderRadius: '4px',
                      cursor: page >= Math.ceil(searchResults.total / pageSize) || loading ? 'not-allowed' : 'pointer',
                      fontSize: '0.875rem'
                    }}
                  >
                    下一页
                  </button>
                </div>
              )}
            </>
          ) : (
            <div style={{
              textAlign: 'center',
              color: '#9ca3af',
              marginTop: '60px'
            }}>
              <div style={{ fontSize: '3rem', marginBottom: '12px' }}>📭</div>
              <div>未找到匹配的结果</div>
              <div style={{ fontSize: '0.875rem', marginTop: '8px' }}>
                尝试调整搜索关键词或降低相似度阈值
              </div>
            </div>
          )}
        </div>
      </div>

      {error && (
        <div style={{
          position: 'fixed',
          bottom: '20px',
          right: '20px',
          backgroundColor: '#fee2e2',
          color: '#991b1b',
          padding: '12px 16px',
          borderRadius: '4px',
          boxShadow: '0 2px 8px rgba(0, 0, 0, 0.1)',
          zIndex: 1000,
          maxWidth: '400px'
        }}>
          {error}
          <button
            onClick={() => setError(null)}
            style={{ marginLeft: '12px', background: 'none', border: 'none', color: '#991b1b', cursor: 'pointer' }}
          >
            ×
          </button>
        </div>
      )}

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
