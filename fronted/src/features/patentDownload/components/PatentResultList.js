import React from 'react';
import DownloadResultList from '../../download/components/DownloadResultList';
import { isDownloadedItem } from '../../download/downloadPageUtils';
import {
  isAnalysisErrorText,
  PATENT_SOURCE_LABEL_MAP,
  stripHtml,
} from '../patentDownloadPageUtils';

function renderPatentMeta(item) {
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
      <span>{PATENT_SOURCE_LABEL_MAP[item.source] || item.source || '-'}</span>
      <span>{item.publication_number || '-'}</span>
      <span>{item.publication_date || '-'}</span>
      <span>申请人: {item.assignee || '-'}</span>
      <span>发明人: {item.inventor || '-'}</span>
      <span>专利 ID: {item.patent_id || '-'}</span>
      {item.error ? <span style={{ color: '#b91c1c' }}>{item.error}</span> : null}
    </div>
  );
}

function renderPatentAnalysis(item) {
  return item.analysis_text && !isAnalysisErrorText(item.analysis_text) ? (
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

export default function PatentResultList({
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
      itemKeyPrefix="s"
      emptyText="暂无专利结果"
      listStyle={{ maxHeight: '70vh', overflow: 'auto', paddingRight: '4px' }}
      cardStyle={{ background: '#fff', gap: '8px' }}
      titleStyle={{ fontWeight: 800, lineHeight: 1.35 }}
      addingItemId={addingItemId}
      deletingItemId={deletingItemId}
      isAddDisabled={(item, { adding }) =>
        !isDownloadedItem(item) || Boolean(item?.added_doc_id) || adding
      }
      onView={onView}
      onAdd={onAdd}
      onDelete={onDelete}
      getTitle={(item) =>
        stripHtml(item.title || item.filename || `专利_${item.item_id || '-'}`)
      }
      renderMeta={renderPatentMeta}
      renderAnalysis={renderPatentAnalysis}
    />
  );
}
