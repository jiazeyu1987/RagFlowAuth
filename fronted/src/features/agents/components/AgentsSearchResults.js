import React, { useMemo } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeRaw from 'rehype-raw';
import rehypeSanitize from 'rehype-sanitize';
import {
  getChunkDocumentInfo,
  highlightTextFallback,
  looksLikeMarkdownContent,
  normalizeInlinePipeKvTables,
} from '../utils/searchResultUtils';

export default function AgentsSearchResults({
  searchResults,
  page,
  pageSize,
  loading,
  searchQuery,
  highlight,
  canDownloadFiles,
  onPreviewDocument,
  onDownloadDocument,
  onPageChange,
}) {
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

  const chunks = Array.isArray(searchResults?.chunks) ? searchResults.chunks : [];
  const total = Number(searchResults?.total || 0);
  const totalPages = total > 0 ? Math.ceil(total / pageSize) : 1;

  if (!searchResults) {
    return (
      <div data-testid="agents-results-empty-initial" style={{ flex: 1, overflowY: 'auto', padding: '16px' }}>
        <div style={{ textAlign: 'center', color: '#9ca3af', marginTop: '60px' }}>
          <div style={{ fontSize: '3rem', marginBottom: '12px' }}>🔍</div>
          <div>输入关键词开始搜索知识库</div>
        </div>
      </div>
    );
  }

  if (!chunks.length) {
    return (
      <div data-testid="agents-results-empty-search" style={{ flex: 1, overflowY: 'auto', padding: '16px' }}>
        <div style={{ textAlign: 'center', color: '#9ca3af', marginTop: '60px' }}>
          <div style={{ fontSize: '3rem', marginBottom: '12px' }}>📭</div>
          <div>未找到匹配的结果</div>
          <div style={{ fontSize: '0.875rem', marginTop: '8px' }}>尝试调整搜索关键词或降低相似度阈值</div>
        </div>
      </div>
    );
  }

  return (
    <div style={{ flex: 1, overflowY: 'auto', padding: '16px' }}>
      <div
        data-testid="agents-results-summary"
        style={{
          marginBottom: '16px',
          padding: '12px',
          backgroundColor: '#f0f9ff',
          borderRadius: '4px',
          color: '#0369a1',
          fontSize: '0.875rem',
        }}
      >
        找到 {total} 个结果 (第 {page} 页)
      </div>

      {chunks.map((chunk, index) => {
        const { docId, docName, datasetId } = getChunkDocumentInfo(chunk);
        const rawContent = String(chunk?.content || '');
        const useMarkdown = looksLikeMarkdownContent(rawContent, docName);
        let displayContent = rawContent;

        if (!useMarkdown && highlight && !chunk?.content_with_weight) {
          displayContent = highlightTextFallback(rawContent, searchQuery);
        } else if (!useMarkdown && chunk?.content_with_weight) {
          displayContent = chunk.content_with_weight;
        }

        return (
          <div
            key={index}
            data-testid={`agents-result-item-${index}`}
            style={{
              padding: '16px',
              marginBottom: '12px',
              border: '1px solid #e5e7eb',
              borderRadius: '6px',
              backgroundColor: '#fafafa',
            }}
          >
            <div
              style={{
                marginBottom: '8px',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                flexWrap: 'wrap',
                gap: '8px',
              }}
            >
              <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', alignItems: 'center' }}>
                {docName ? (
                  <span
                    style={{
                      fontSize: '0.875rem',
                      fontWeight: 'bold',
                      color: '#1f2937',
                      backgroundColor: '#f3f4f6',
                      padding: '4px 10px',
                      borderRadius: '4px',
                      marginRight: '8px',
                      border: '1px solid #e5e7eb',
                    }}
                  >
                    文档: {docName}
                  </span>
                ) : null}

                {chunk?.similarity !== undefined ? (
                  <span
                    style={{
                      fontSize: '0.75rem',
                      color: '#059669',
                      backgroundColor: '#d1fae5',
                      padding: '4px 8px',
                      borderRadius: '4px',
                      fontWeight: '500',
                    }}
                  >
                    相似度: {(chunk.similarity * 100).toFixed(1)}%
                  </span>
                ) : null}
              </div>

              <div style={{ display: 'flex', gap: '8px' }}>
                {docId ? (
                  <button
                    type="button"
                    onClick={() => onPreviewDocument && onPreviewDocument(docId, docName, datasetId)}
                    data-testid={`agents-doc-view-${String(datasetId || '')}-${String(docId || '')}`}
                    style={{
                      padding: '6px 14px',
                      fontSize: '0.875rem',
                      backgroundColor: '#3b82f6',
                      color: 'white',
                      border: 'none',
                      borderRadius: '4px',
                      cursor: 'pointer',
                      fontWeight: '500',
                    }}
                    title="查看文件内容"
                  >
                    查看
                  </button>
                ) : null}

                {docId && canDownloadFiles ? (
                  <button
                    type="button"
                    onClick={() => onDownloadDocument && onDownloadDocument(docId, docName, datasetId)}
                    style={{
                      padding: '6px 14px',
                      fontSize: '0.875rem',
                      backgroundColor: '#059669',
                      color: 'white',
                      border: 'none',
                      borderRadius: '4px',
                      cursor: 'pointer',
                      fontWeight: '500',
                    }}
                    title="下载完整源文件"
                  >
                    下载
                  </button>
                ) : null}
              </div>
            </div>

            {useMarkdown ? (
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
                  whiteSpace: 'pre-wrap',
                }}
                dangerouslySetInnerHTML={{
                  __html: displayContent,
                }}
              />
            )}
          </div>
        );
      })}

      {total > pageSize ? (
        <div
          style={{
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center',
            gap: '12px',
            marginTop: '16px',
            paddingTop: '16px',
            borderTop: '1px solid #e5e7eb',
          }}
        >
          <button
            type="button"
            onClick={() => onPageChange && onPageChange(Math.max(1, page - 1))}
            disabled={page <= 1 || loading}
            style={{
              padding: '6px 12px',
              backgroundColor: page <= 1 || loading ? '#9ca3af' : '#3b82f6',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: page <= 1 || loading ? 'not-allowed' : 'pointer',
              fontSize: '0.875rem',
            }}
          >
            上一页
          </button>

          <span style={{ fontSize: '0.875rem', color: '#6b7280' }}>
            第 {page} / {totalPages} 页
          </span>

          <button
            type="button"
            onClick={() => onPageChange && onPageChange(page + 1)}
            disabled={page >= totalPages || loading}
            style={{
              padding: '6px 12px',
              backgroundColor: page >= totalPages || loading ? '#9ca3af' : '#3b82f6',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: page >= totalPages || loading ? 'not-allowed' : 'pointer',
              fontSize: '0.875rem',
            }}
          >
            下一页
          </button>
        </div>
      ) : null}
    </div>
  );
}
