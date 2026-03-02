import React from 'react';

const BatchSummaryCard = ({ summary, expanded, copied, onToggleExpanded, onCopy, onResolveConflict }) => {
  if (!summary) return null;

  return (
    <div
      style={{
        backgroundColor: '#f8fafc',
        border: '1px solid #dbeafe',
        color: '#1e3a8a',
        padding: '12px 16px',
        borderRadius: '6px',
        marginBottom: '20px',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: '12px', alignItems: 'center', marginBottom: '8px' }}>
        <div style={{ fontWeight: 600 }}>{summary.mode === 'approve' ? '批量通过结果' : '批量驳回结果'}</div>
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          <button
            type="button"
            onClick={onToggleExpanded}
            style={{
              padding: '4px 10px',
              borderRadius: '6px',
              border: '1px solid #93c5fd',
              background: 'white',
              color: '#1d4ed8',
              cursor: 'pointer',
              fontSize: '0.85rem',
            }}
          >
            {expanded ? '收起' : '展开全部'}
          </button>
          <button
            type="button"
            onClick={onCopy}
            style={{
              padding: '4px 10px',
              borderRadius: '6px',
              border: '1px solid #93c5fd',
              background: 'white',
              color: '#1d4ed8',
              cursor: 'pointer',
              fontSize: '0.85rem',
            }}
          >
            {copied ? '已复制' : '复制明细'}
          </button>
        </div>
      </div>

      <div style={{ fontSize: '0.95rem', marginBottom: '8px' }}>
        {`成功 ${summary.successCount}，失败 ${summary.failedCount}，冲突跳过 ${summary.conflicted.length}，检查失败 ${summary.checkFailed.length}`}
      </div>

      {summary.failedItems.length > 0 && (
        <div style={{ marginBottom: '8px' }}>
          <div style={{ fontWeight: 600, color: '#991b1b' }}>失败项</div>
          {summary.failedItems.slice(0, expanded ? summary.failedItems.length : 10).map((item) => (
            <div key={`failed-${item.doc_id}`} style={{ fontSize: '0.9rem', color: '#374151' }}>
              {`${item.doc_id}: ${item.detail}`}
            </div>
          ))}
        </div>
      )}

      {summary.conflicted.length > 0 && (
        <div style={{ marginBottom: '8px' }}>
          <div style={{ fontWeight: 600, color: '#92400e' }}>冲突项</div>
          {summary.conflicted.slice(0, expanded ? summary.conflicted.length : 10).map((item) => (
            <div
              key={`conflict-${item.docId}`}
              style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.9rem', color: '#374151', marginBottom: '4px' }}
            >
              <span style={{ flex: 1 }}>{`${item.filename}: ${item.detail}`}</span>
              {item.existing && (
                <button
                  type="button"
                  onClick={() => onResolveConflict(item)}
                  style={{
                    padding: '4px 10px',
                    borderRadius: '6px',
                    border: '1px solid #d97706',
                    background: '#fff7ed',
                    color: '#9a3412',
                    cursor: 'pointer',
                    fontSize: '0.85rem',
                  }}
                >
                  处理
                </button>
              )}
            </div>
          ))}
        </div>
      )}

      {summary.checkFailed.length > 0 && (
        <div>
          <div style={{ fontWeight: 600, color: '#7c2d12' }}>检查失败</div>
          {summary.checkFailed.slice(0, expanded ? summary.checkFailed.length : 10).map((item) => (
            <div key={`check-${item.docId}`} style={{ fontSize: '0.9rem', color: '#374151' }}>
              {`${item.filename}: ${item.detail}`}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default BatchSummaryCard;
