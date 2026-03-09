import React from 'react';

export default function DownloadHistorySidebar({
  rows,
  selectedKey,
  addingKey,
  deletingKey,
  loading,
  loadingItems,
  onRefresh,
  onSelectKey,
  onAdd,
  onDelete,
  title = 'History Keywords',
  refreshText = 'Refresh',
  loadingText = 'Loading...',
  emptyText = 'No history keywords',
  addText = 'Add to KB',
  addingText = 'Adding...',
  deleteText = 'Delete',
  deletingText = 'Deleting...',
  getRowKey = (row) => String(row?.history_key || ''),
  getRowTitle = (row) => row?.keyword_display || '-',
}) {
  const list = Array.isArray(rows) ? rows : [];
  const selected = String(selectedKey || '');

  return (
    <div style={{ border: '1px solid #e5e7eb', borderRadius: '10px', padding: '8px', maxHeight: '70vh', overflow: 'auto' }}>
      <div style={{ fontWeight: 800, color: '#111827', marginBottom: '6px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <span>{title}</span>
        <button
          type="button"
          onClick={onRefresh}
          disabled={Boolean(loading || loadingItems)}
          style={{
            padding: '4px 8px',
            borderRadius: '7px',
            border: '1px solid #2563eb',
            background: loading || loadingItems ? '#93c5fd' : '#2563eb',
            color: '#fff',
            cursor: loading || loadingItems ? 'not-allowed' : 'pointer',
            fontSize: '0.78rem',
            fontWeight: 700,
          }}
        >
          {refreshText}
        </button>
      </div>

      {loading ? <div style={{ color: '#6b7280', fontSize: '0.86rem' }}>{loadingText}</div> : null}
      {!loading && !list.length ? <div style={{ color: '#9ca3af', fontSize: '0.86rem' }}>{emptyText}</div> : null}

      <div style={{ display: 'grid', gap: '6px' }}>
        {list.map((row) => {
          const key = getRowKey(row);
          const safeKey = String(key || '').replace(/[^a-zA-Z0-9_-]/g, '_');
          const active = key === selected;
          const downloadedCount = Number(row?.downloaded_count || 0);
          const analyzedCount = Number(row?.analyzed_count || 0);
          const addedCount = Number(row?.added_count || 0);
          const canAdd = downloadedCount > 0 && addedCount < downloadedCount;
          const adding = String(addingKey || '') === key;
          const deleting = String(deletingKey || '') === key;
          const allAdded = downloadedCount > 0 && addedCount >= downloadedCount;
          const partialAdded = addedCount > 0 && addedCount < downloadedCount;
          const addBtnBg = allAdded ? '#d1d5db' : partialAdded ? '#f59e0b' : '#16a34a';
          const addBtnBorder = allAdded ? '#9ca3af' : partialAdded ? '#d97706' : '#15803d';

          return (
            <div
              key={key}
              data-testid={`download-history-row-${safeKey}`}
              style={{
                border: active ? '1px solid #60a5fa' : '1px solid #e5e7eb',
                background: active ? '#eff6ff' : '#fff',
                borderRadius: '8px',
                padding: '8px',
                display: 'grid',
                gap: '6px',
              }}
            >
              <button
                type="button"
                onClick={() => onSelectKey && onSelectKey(key, row)}
                style={{ textAlign: 'left', border: 'none', background: 'transparent', padding: 0, cursor: 'pointer' }}
              >
                <div style={{ fontWeight: 700, color: '#111827', fontSize: '0.88rem' }}>{getRowTitle(row)}</div>
                <div style={{ fontSize: '0.78rem', color: '#6b7280', marginTop: '4px' }}>
                  downloaded {downloadedCount}, analyzed {analyzedCount}, added {addedCount}
                </div>
              </button>

              <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                <button
                  type="button"
                  onClick={() => onAdd && onAdd(row)}
                  disabled={!canAdd || adding}
                  data-testid={`download-history-add-${safeKey}`}
                  style={{
                    padding: '4px 8px',
                    borderRadius: '7px',
                    border: `1px solid ${addBtnBorder}`,
                    background: addBtnBg,
                    color: '#fff',
                    cursor: !canAdd || adding ? 'not-allowed' : 'pointer',
                    fontSize: '0.78rem',
                    fontWeight: 700,
                    opacity: !canAdd || adding ? 0.75 : 1,
                  }}
                >
                  {adding ? addingText : addText}
                </button>
                <button
                  type="button"
                  onClick={() => onDelete && onDelete(row)}
                  disabled={deleting}
                  data-testid={`download-history-delete-${safeKey}`}
                  style={{
                    padding: '4px 8px',
                    borderRadius: '7px',
                    border: '1px solid #ef4444',
                    background: deleting ? '#fecaca' : '#ef4444',
                    color: '#fff',
                    cursor: deleting ? 'not-allowed' : 'pointer',
                    fontSize: '0.78rem',
                    fontWeight: 700,
                  }}
                >
                  {deleting ? deletingText : deleteText}
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
