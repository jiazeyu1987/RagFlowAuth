import React from 'react';
import { getStatusChip } from '../downloadPageUtils';

const defaultListStyle = {
  display: 'grid',
  gap: '8px',
};

const defaultCardStyle = {
  border: '1px solid #e5e7eb',
  borderRadius: '10px',
  padding: '10px',
  display: 'grid',
  gap: '6px',
};

const defaultTitleStyle = {
  fontWeight: 700,
  color: '#111827',
};

export default function DownloadResultList({
  items,
  sessionId = '',
  emptyText = '暂无列表',
  listStyle,
  cardStyle,
  titleStyle,
  getTitle,
  renderMeta,
  renderAnalysis,
  canView = (item) => Boolean(item?.has_file),
  isAddDisabled = () => false,
  addingItemId = null,
  deletingItemId = null,
  onView,
  onAdd,
  onDelete,
  viewText = '查看',
  addText = '加入知识库',
  addingText = '加入中...',
  addedText = '已加入',
  deleteText = '删除',
  deletingText = '删除中...',
  detailLinkText = '原始链接',
  itemKeyPrefix = 's',
}) {
  if (!Array.isArray(items) || items.length === 0) {
    return <div style={{ color: '#9ca3af', fontSize: '0.9rem' }}>{emptyText}</div>;
  }

  return (
    <div style={{ ...defaultListStyle, ...(listStyle || {}) }}>
      {items.map((item) => {
        const chip = getStatusChip(item);
        const adding = addingItemId === item?.item_id;
        const deleting = deletingItemId === item?.item_id;
        const viewEnabled = Boolean(canView(item));
        const addDisabled = Boolean(isAddDisabled(item, { adding }));
        const title = typeof getTitle === 'function' ? getTitle(item) : item?.title || item?.filename || '-';
        const itemKey = `${item?.session_id || sessionId || itemKeyPrefix}-${item?.item_id || 'x'}`;
        const safeItemId = String(item?.item_id || 'x').replace(/[^a-zA-Z0-9_-]/g, '_');
        const analysisNode = typeof renderAnalysis === 'function' ? renderAnalysis(item) : null;

        return (
          <div key={itemKey} style={{ ...defaultCardStyle, ...(cardStyle || {}) }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '8px' }}>
              <div style={{ ...defaultTitleStyle, ...(titleStyle || {}) }}>{title}</div>
              <span
                style={{
                  fontSize: '0.75rem',
                  color: chip.color,
                  background: chip.bg,
                  border: `1px solid ${chip.border}`,
                  borderRadius: '999px',
                  padding: '2px 8px',
                  whiteSpace: 'nowrap',
                }}
              >
                {chip.text}
              </span>
            </div>

            {typeof renderMeta === 'function' ? renderMeta(item) : null}

            {item?.detail_url ? (
              <div style={{ fontSize: '0.82rem' }}>
                <a href={item.detail_url} target="_blank" rel="noreferrer" style={{ color: '#2563eb', textDecoration: 'none' }}>
                  {detailLinkText}
                </a>
              </div>
            ) : null}

            {analysisNode}

            <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
              <button
                type="button"
                onClick={() => onView && onView(item)}
                disabled={!viewEnabled}
                data-testid={`download-view-${safeItemId}`}
                style={{
                  padding: '7px 10px',
                  borderRadius: '8px',
                  border: '1px solid #0ea5e9',
                  background: viewEnabled ? '#0ea5e9' : '#bae6fd',
                  color: '#fff',
                  cursor: viewEnabled ? 'pointer' : 'not-allowed',
                  fontWeight: 700,
                }}
              >
                {viewText}
              </button>
              <button
                type="button"
                onClick={() => onAdd && onAdd(item)}
                disabled={addDisabled}
                data-testid={`download-add-${safeItemId}`}
                style={{
                  padding: '7px 10px',
                  borderRadius: '8px',
                  border: '1px solid #16a34a',
                  background: '#16a34a',
                  color: '#fff',
                  cursor: addDisabled ? 'not-allowed' : 'pointer',
                  opacity: addDisabled ? 0.55 : 1,
                  fontWeight: 700,
                }}
              >
                {item?.added_doc_id ? addedText : adding ? addingText : addText}
              </button>
              <button
                type="button"
                onClick={() => onDelete && onDelete(item)}
                disabled={deleting}
                data-testid={`download-delete-${safeItemId}`}
                style={{
                  padding: '7px 10px',
                  borderRadius: '8px',
                  border: '1px solid #ef4444',
                  background: deleting ? '#fecaca' : '#ef4444',
                  color: '#fff',
                  cursor: deleting ? 'not-allowed' : 'pointer',
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
  );
}
