import React from 'react';
import { TEXT } from '../constants';

export default function BatchTransferProgress({ progress, onClose }) {
  if (!progress) return null;

  return (
    <div className="medui-surface medui-card-pad">
      <div className="medui-header-row" style={{ marginBottom: 8 }}>
        <strong style={{ color: '#173d60' }}>{TEXT.transferInProgress}</strong>
        {progress.done ? (
          <button type="button" onClick={onClose} className="medui-btn medui-btn--neutral">
            关闭
          </button>
        ) : null}
      </div>
      <div className="medui-subtitle">
        {TEXT.transferCurrent}: {progress.current || '-'}
      </div>
      <div style={{ marginTop: 6, color: '#4b5563', fontSize: '0.9rem' }}>
        {progress.processed}/{progress.total} | {TEXT.transferSuccess}: {progress.success} | {TEXT.transferFailed}: {progress.failed}
      </div>
      <div style={{ marginTop: 8, height: 8, background: '#dbe7f3', borderRadius: 999, overflow: 'hidden' }}>
        <div
          style={{
            width: `${Math.round((progress.processed / Math.max(progress.total, 1)) * 100)}%`,
            height: '100%',
            background: '#0d5ea6',
            transition: 'width 0.2s',
          }}
        />
      </div>
      {progress.done ? <div style={{ marginTop: 8, color: '#166534', fontSize: '0.9rem' }}>{TEXT.transferDone}</div> : null}
    </div>
  );
}
