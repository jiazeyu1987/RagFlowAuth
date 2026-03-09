import React from 'react';
import { TEXT } from '../constants';
import { toolbarButtonStyle } from '../styles';

export default function BatchTransferProgress({ progress, onClose }) {
  if (!progress) return null;

  return (
    <div style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: 8, padding: 14, marginBottom: 16 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
        <strong>{TEXT.transferInProgress}</strong>
        {progress.done ? (
          <button type="button" onClick={onClose} style={toolbarButtonStyle('neutral')}>
            {TEXT.cancel}
          </button>
        ) : null}
      </div>
      <div style={{ color: '#4b5563', fontSize: '0.9rem' }}>
        {TEXT.transferCurrent}: {progress.current || '-'}
      </div>
      <div style={{ marginTop: 6, color: '#4b5563', fontSize: '0.9rem' }}>
        {progress.processed}/{progress.total} | {TEXT.transferSuccess}: {progress.success} | {TEXT.transferFailed}: {progress.failed}
      </div>
      <div style={{ marginTop: 8, height: 8, background: '#e5e7eb', borderRadius: 999, overflow: 'hidden' }}>
        <div
          style={{
            width: `${Math.round((progress.processed / Math.max(progress.total, 1)) * 100)}%`,
            height: '100%',
            background: '#2563eb',
            transition: 'width 0.2s',
          }}
        />
      </div>
      {progress.done ? <div style={{ marginTop: 8, color: '#166534', fontSize: '0.9rem' }}>{TEXT.transferDone}</div> : null}
    </div>
  );
}
