import React, { useEffect, useState } from 'react';

const MOBILE_BREAKPOINT = 768;
const DIALOG_TEXT = {
  title: '\u65b0\u5efa\u77e5\u8bc6\u5e93',
  close: '\u5173\u95ed',
  name: '\u540d\u79f0',
  namePlaceholder: '\u8f93\u5165\u77e5\u8bc6\u5e93\u540d\u79f0',
  copyFrom: '\u590d\u5236\u914d\u7f6e',
  mountDir: '\u6302\u8f7d\u76ee\u5f55',
  cancel: '\u53d6\u6d88',
  create: '\u521b\u5efa',
};

export default function CreateKnowledgeBaseDialog({
  open,
  onClose,
  createName,
  onCreateNameChange,
  createFromId,
  onCreateFromIdChange,
  kbList,
  createDirId,
  onCreateDirIdChange,
  dirOptions,
  createError,
  onCreate,
  isAdmin,
  kbBusy,
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

  if (!open) return null;

  return (
    <div
      data-testid="create-kb-dialog"
      role="dialog"
      aria-modal="true"
      onMouseDown={(event) => event.target === event.currentTarget && onClose && onClose()}
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(17,24,39,0.45)',
        display: 'flex',
        alignItems: isMobile ? 'stretch' : 'center',
        justifyContent: 'center',
        zIndex: 1000,
        padding: isMobile ? '12px' : 0,
      }}
    >
      <div
        style={{
          width: 'min(680px, 95vw)',
          maxHeight: isMobile ? '100%' : '90vh',
          background: '#fff',
          borderRadius: 12,
          border: '1px solid #e5e7eb',
          overflow: 'hidden',
          display: 'flex',
          flexDirection: 'column',
          margin: isMobile ? 'auto 0' : 0,
        }}
      >
        <div
          style={{
            padding: '12px 14px',
            borderBottom: '1px solid #e5e7eb',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: isMobile ? 'stretch' : 'center',
            flexDirection: isMobile ? 'column' : 'row',
            gap: '10px',
          }}
        >
          <div data-testid="create-kb-dialog-title" style={{ fontWeight: 800 }}>{DIALOG_TEXT.title}</div>
          <button
            type="button"
            onClick={onClose}
            style={{
              border: '1px solid #d1d5db',
              borderRadius: 8,
              background: '#fff',
              cursor: 'pointer',
              padding: '6px 10px',
              alignSelf: isMobile ? 'flex-end' : 'auto',
            }}
          >
            {DIALOG_TEXT.close}
          </button>
        </div>
        <div style={{ padding: 14, overflowY: 'auto' }}>
          <div style={{ display: 'grid', gridTemplateColumns: isMobile ? '1fr' : '110px 1fr', alignItems: 'center', gap: 10, marginBottom: 10 }}>
            <label>{DIALOG_TEXT.name}</label>
            <input
              placeholder={DIALOG_TEXT.namePlaceholder}
              value={createName}
              onChange={(event) => onCreateNameChange && onCreateNameChange(event.target.value)}
              style={{ padding: '9px 10px', border: '1px solid #d1d5db', borderRadius: 8, width: '100%', boxSizing: 'border-box' }}
            />
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: isMobile ? '1fr' : '110px 1fr', alignItems: 'center', gap: 10 }}>
            <label>{DIALOG_TEXT.copyFrom}</label>
            <select value={createFromId} onChange={(event) => onCreateFromIdChange && onCreateFromIdChange(event.target.value)} style={{ padding: '9px 10px', border: '1px solid #d1d5db', borderRadius: 8, width: '100%', boxSizing: 'border-box' }} disabled={!kbList.length}>
              {kbList.map((dataset) => <option key={String(dataset?.id || '')} value={String(dataset?.id || '')}>{String(dataset?.name || dataset?.id || '')}</option>)}
            </select>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: isMobile ? '1fr' : '110px 1fr', alignItems: 'center', gap: 10, marginTop: 10 }}>
            <label>{DIALOG_TEXT.mountDir}</label>
            <select value={createDirId} onChange={(event) => onCreateDirIdChange && onCreateDirIdChange(event.target.value)} style={{ padding: '9px 10px', border: '1px solid #d1d5db', borderRadius: 8, width: '100%', boxSizing: 'border-box' }}>
              {dirOptions.map((option) => <option key={option.id || '__root__'} value={option.id}>{option.label}</option>)}
            </select>
          </div>
          {createError ? <div style={{ color: '#b91c1c', marginTop: 10 }}>{createError}</div> : null}
        </div>
        <div style={{ padding: '12px 14px', borderTop: '1px solid #e5e7eb', display: 'flex', justifyContent: 'flex-end', gap: 8, flexDirection: isMobile ? 'column' : 'row' }}>
          <button type="button" onClick={onClose} style={{ border: '1px solid #d1d5db', borderRadius: 8, background: '#fff', cursor: 'pointer', padding: '8px 12px', width: isMobile ? '100%' : 'auto' }}>{DIALOG_TEXT.cancel}</button>
          <button type="button" onClick={onCreate} disabled={!isAdmin || kbBusy} style={{ border: '1px solid #2563eb', borderRadius: 8, background: kbBusy ? '#93c5fd' : '#2563eb', color: '#fff', cursor: kbBusy ? 'not-allowed' : 'pointer', padding: '8px 12px', width: isMobile ? '100%' : 'auto' }}>{DIALOG_TEXT.create}</button>
        </div>
      </div>
    </div>
  );
}
