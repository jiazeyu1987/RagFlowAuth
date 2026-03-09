import React from 'react';

export default function DownloadHistoryDetailPanel({
  error = '',
  loading = false,
  loadingText = 'Loading...',
  payload = null,
  itemLabel = 'items',
  children = null,
}) {
  const summary = payload?.history || null;

  return (
    <div>
      {error ? <div style={{ color: '#b91c1c', fontSize: '0.88rem', marginBottom: '8px' }}>{error}</div> : null}
      {loading ? <div style={{ color: '#6b7280', fontSize: '0.88rem' }}>{loadingText}</div> : null}
      {!loading && summary ? (
        <div style={{ color: '#6b7280', fontSize: '0.82rem', marginBottom: '8px' }}>
          Keyword: {summary.keyword_display || '-'}, Sessions {summary.session_count || 0}, {itemLabel} {summary.item_count || 0}
        </div>
      ) : null}
      {!loading ? children : null}
    </div>
  );
}
