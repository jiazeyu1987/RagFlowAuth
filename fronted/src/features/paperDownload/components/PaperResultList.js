import React from 'react';
import DownloadResultList from '../../download/components/DownloadResultList';
import { isDownloadedItem } from '../../download/downloadPageUtils';
import { PAPER_SOURCE_LABEL_MAP } from '../paperDownloadPageUtils';

function renderPaperMeta(item) {
  return (
    <div
      style={{
        display: 'flex',
        flexWrap: 'wrap',
        gap: '8px',
        color: '#6b7280',
        fontSize: '0.82rem',
      }}
    >
      <span>{item.source_label || PAPER_SOURCE_LABEL_MAP[item.source] || item.source || '-'}</span>
      <span>{item.publication_number || '-'}</span>
      <span>{item.publication_date || '-'}</span>
      <span>{item.inventor || '-'}</span>
      <span>{item.patent_id || '-'}</span>
      {item.error ? <span style={{ color: '#b91c1c' }}>{item.error}</span> : null}
    </div>
  );
}

function renderPaperAnalysis(item) {
  return item.analysis_text ? (
    <div
      style={{
        fontSize: '0.83rem',
        color: '#1f2937',
        lineHeight: 1.5,
        background: '#f9fafb',
        border: '1px solid #e5e7eb',
        borderRadius: '8px',
        padding: '8px',
      }}
    >
      <strong>解析结果:</strong> {item.analysis_text}
    </div>
  ) : null;
}

export default function PaperResultList({
  items,
  sessionId,
  addingItemId,
  deletingItemId,
  onView,
  onAdd,
  onDelete,
}) {
  return (
    <DownloadResultList
      items={items}
      sessionId={sessionId}
      emptyText="暂无论文结果"
      addingItemId={addingItemId}
      deletingItemId={deletingItemId}
      isAddDisabled={(item, { adding }) =>
        Boolean(item?.added_doc_id) || !isDownloadedItem(item) || adding
      }
      onView={onView}
      onAdd={onAdd}
      onDelete={onDelete}
      getTitle={(item) => item.title || item.filename || `论文_${item.item_id}`}
      renderMeta={renderPaperMeta}
      renderAnalysis={renderPaperAnalysis}
    />
  );
}
