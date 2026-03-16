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
            border: '1px solid #d5e3f1',
            padding: '8px 10px',
            textAlign: 'left',
            background: '#f4f9ff',
            fontWeight: 700,
          }}
          {...props}
        />
      ),
      td: ({ node, ...props }) => (
        <td
          style={{
            border: '1px solid #dfeaf6',
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
                  background: '#dce9f7',
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
            background: '#17324a',
            color: '#f4f8fd',
            borderRadius: '10px',
            overflowX: 'auto',
          }}
          {...props}
        />
      ),
      a: ({ node, ...props }) => (
        <a {...props} target="_blank" rel="noreferrer" style={{ color: '#0d5ea6', textDecoration: 'underline' }}>
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
      <div data-testid="agents-results-empty-initial" className="agents-med-result">
        <div className="agents-med-empty">
          <div className="agents-med-empty__icon">搜</div>
          <div>输入关键词开始检索知识库。</div>
        </div>
      </div>
    );
  }

  if (!chunks.length) {
    return (
      <div data-testid="agents-results-empty-search" className="agents-med-result">
        <div className="agents-med-empty">
          <div className="agents-med-empty__icon">无</div>
          <div>未找到匹配结果。</div>
          <div style={{ fontSize: '0.875rem' }}>可尝试调整关键词或降低相似度阈值。</div>
        </div>
      </div>
    );
  }

  return (
    <div className="agents-med-result">
      <div data-testid="agents-results-summary" className="agents-med-summary">
        共找到 {total} 条结果（第 {page} 页）
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
          <div key={index} data-testid={`agents-result-item-${index}`} className="agents-med-result-item">
            <div className="agents-med-result-head">
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
                {docName ? <span className="agents-med-doc-tag">文档: {docName}</span> : null}

                {chunk?.similarity !== undefined ? (
                  <span className="medui-badge medui-badge--success">相似度 {(chunk.similarity * 100).toFixed(1)}%</span>
                ) : null}
              </div>

              <div style={{ display: 'flex', gap: 8 }}>
                {docId ? (
                  <button
                    type="button"
                    onClick={() => onPreviewDocument && onPreviewDocument(docId, docName, datasetId)}
                    data-testid={`agents-doc-view-${String(datasetId || '')}-${String(docId || '')}`}
                    className="medui-btn medui-btn--secondary"
                    title="查看文件内容"
                  >
                    查看
                  </button>
                ) : null}

                {docId && canDownloadFiles ? (
                  <button
                    type="button"
                    onClick={() => onDownloadDocument && onDownloadDocument(docId, docName, datasetId)}
                    className="medui-btn medui-btn--primary"
                    title="下载完整源文件"
                  >
                    下载
                  </button>
                ) : null}
              </div>
            </div>

            {useMarkdown ? (
              <div style={{ fontSize: '0.9rem', lineHeight: 1.65, color: '#17324d' }}>
                <ReactMarkdown components={markdownComponents} remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeRaw, rehypeSanitize]}>
                  {normalizeInlinePipeKvTables(rawContent)}
                </ReactMarkdown>
              </div>
            ) : (
              <div
                style={{
                  fontSize: '0.89rem',
                  lineHeight: '1.62',
                  color: '#17324d',
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
            gap: 12,
            marginTop: 16,
            paddingTop: 16,
            borderTop: '1px solid #dce9f7',
          }}
        >
          <button
            type="button"
            onClick={() => onPageChange && onPageChange(Math.max(1, page - 1))}
            disabled={page <= 1 || loading}
            className="medui-btn medui-btn--secondary"
          >
            上一页
          </button>

          <span className="medui-subtitle">
            第 {page} / {totalPages} 页
          </span>

          <button
            type="button"
            onClick={() => onPageChange && onPageChange(page + 1)}
            disabled={page >= totalPages || loading}
            className="medui-btn medui-btn--secondary"
          >
            下一页
          </button>
        </div>
      ) : null}
    </div>
  );
}
