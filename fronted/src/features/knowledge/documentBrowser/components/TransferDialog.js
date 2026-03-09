import React from 'react';
import { TEXT } from '../constants';
import { toolbarButtonStyle } from '../styles';

export default function TransferDialog({
  transferDialog,
  selectedCount,
  transferTargetOptions,
  onClose,
  onConfirm,
  onChangeTarget,
}) {
  if (!transferDialog) return null;

  const options = transferDialog.scope === 'single'
    ? transferTargetOptions.filter((name) => name !== transferDialog.sourceDatasetName)
    : transferTargetOptions;

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(15,23,42,0.45)',
        zIndex: 1000,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
      }}
    >
      <div style={{ width: 'min(520px, 94vw)', background: '#fff', border: '1px solid #e5e7eb', borderRadius: 12 }}>
        <div style={{ padding: '12px 14px', borderBottom: '1px solid #e5e7eb', fontWeight: 800 }}>
          {transferDialog.operation === 'move' ? TEXT.transferTitleMove : TEXT.transferTitleCopy}
        </div>
        <div style={{ padding: 14 }}>
          <div style={{ marginBottom: 10, color: '#4b5563', fontSize: '0.9rem' }}>
            {transferDialog.scope === 'single'
              ? `${transferDialog.sourceDatasetName} / ${transferDialog.docId}`
              : `${selectedCount} docs`}
          </div>
          <label style={{ display: 'block', marginBottom: 6 }}>{TEXT.targetKb}</label>
          <select
            value={transferDialog.targetDatasetName}
            onChange={(event) => onChangeTarget && onChangeTarget(event.target.value)}
            style={{ width: '100%', border: '1px solid #d1d5db', borderRadius: 8, padding: '8px 10px' }}
          >
            {options.map((name) => (
              <option key={name} value={name}>{name}</option>
            ))}
          </select>
        </div>
        <div style={{ padding: '12px 14px', borderTop: '1px solid #e5e7eb', display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
          <button type="button" onClick={onClose} style={toolbarButtonStyle('neutral')}>{TEXT.cancel}</button>
          <button type="button" onClick={onConfirm} style={toolbarButtonStyle('primary')}>{TEXT.confirm}</button>
        </div>
      </div>
    </div>
  );
}
