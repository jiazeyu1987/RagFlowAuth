import React from 'react';

export default function DownloadHistoryDetailPanel({
  error = '',
  loading = false,
  loadingText = '加载中...',
  payload = null,
  itemLabel = '条',
  children = null,
}) {
  const summary = payload?.history || null;

  return (
    <div>
      {error ? <div style={{ color: '#b91c1c', fontSize: '0.88rem', marginBottom: '8px' }}>{error}</div> : null}
      {loading ? <div style={{ color: '#6b7280', fontSize: '0.88rem' }}>{loadingText}</div> : null}
      {!loading && summary ? (
        <div style={{ color: '#6b7280', fontSize: '0.82rem', marginBottom: '8px' }}>
          关键词：{summary.keyword_display || '-'}，会话数 {summary.session_count || 0}，{itemLabel}数 {summary.item_count || 0}
        </div>
      ) : null}
      {!loading ? children : null}
    </div>
  );
}
