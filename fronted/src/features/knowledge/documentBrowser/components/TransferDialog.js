import React, { useEffect, useState } from 'react';
import { TEXT } from '../constants';
import { toolbarButtonStyle } from '../styles';

const MOBILE_BREAKPOINT = 768;

export default function TransferDialog({
  transferDialog,
  selectedCount,
  transferTargetOptions,
  onClose,
  onConfirm,
  onChangeTarget,
}) {
  const [isMobile, setIsMobile] = useState(() => {
    if (typeof window === 'undefined') return false;
    return window.innerWidth <= MOBILE_BREAKPOINT;
  });

  useEffect(() => {
    if (typeof window === 'undefined') return undefined;
    const handleResize = () => setIsMobile(window.innerWidth <= MOBILE_BREAKPOINT);
    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  if (!transferDialog) return null;

  const options = transferDialog.scope === 'single' ? transferTargetOptions.filter((name) => name !== transferDialog.sourceDatasetName) : transferTargetOptions;

  return (
    <div style={{ position: 'fixed', inset: 0, background: 'rgba(15,23,42,0.45)', zIndex: 1000, display: 'flex', alignItems: isMobile ? 'stretch' : 'center', justifyContent: 'center', padding: isMobile ? '12px' : 0 }}>
      <div style={{ width: 'min(520px, 94vw)', maxHeight: isMobile ? '100%' : '90vh', background: '#fff', border: '1px solid #e5e7eb', borderRadius: 12, overflow: 'hidden', display: 'flex', flexDirection: 'column', margin: isMobile ? 'auto 0' : 0 }}>
        <div style={{ padding: '12px 14px', borderBottom: '1px solid #e5e7eb', fontWeight: 800 }}>{transferDialog.operation === 'move' ? TEXT.transferTitleMove : TEXT.transferTitleCopy}</div>
        <div style={{ padding: 14, overflowY: 'auto' }}>
          <div style={{ marginBottom: 10, color: '#4b5563', fontSize: '0.9rem', wordBreak: 'break-all' }}>{transferDialog.scope === 'single' ? `${transferDialog.sourceDatasetName} / ${transferDialog.docId}` : `${selectedCount} docs`}</div>
          <label style={{ display: 'block', marginBottom: 6 }}>{TEXT.targetKb}</label>
          <select value={transferDialog.targetDatasetName} onChange={(event) => onChangeTarget && onChangeTarget(event.target.value)} style={{ width: '100%', border: '1px solid #d1d5db', borderRadius: 8, padding: '8px 10px', boxSizing: 'border-box' }}>
            {options.map((name) => <option key={name} value={name}>{name}</option>)}
          </select>
        </div>
        <div style={{ padding: '12px 14px', borderTop: '1px solid #e5e7eb', display: 'flex', justifyContent: 'flex-end', gap: 8, flexDirection: isMobile ? 'column' : 'row' }}>
          <button type="button" onClick={onClose} style={{ ...toolbarButtonStyle('neutral'), width: isMobile ? '100%' : 'auto' }}>{TEXT.cancel}</button>
          <button type="button" onClick={onConfirm} style={{ ...toolbarButtonStyle('primary'), width: isMobile ? '100%' : 'auto' }}>{TEXT.confirm}</button>
        </div>
      </div>
    </div>
  );
}
