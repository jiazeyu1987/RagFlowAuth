import React from 'react';

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
  if (!open) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      onMouseDown={(event) => event.target === event.currentTarget && onClose && onClose()}
      style={{ position: 'fixed', inset: 0, background: 'rgba(17,24,39,0.45)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}
    >
      <div style={{ width: 'min(680px, 95vw)', background: '#fff', borderRadius: 12, border: '1px solid #e5e7eb', overflow: 'hidden' }}>
        <div style={{ padding: '12px 14px', borderBottom: '1px solid #e5e7eb', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div style={{ fontWeight: 800 }}>新建知识库</div>
          <button type="button" onClick={onClose} style={{ border: '1px solid #d1d5db', borderRadius: 8, background: '#fff', cursor: 'pointer', padding: '6px 10px' }}>
            关闭
          </button>
        </div>
        <div style={{ padding: 14 }}>
          <div style={{ display: 'grid', gridTemplateColumns: '110px 1fr', alignItems: 'center', gap: 10, marginBottom: 10 }}>
            <label>名称</label>
            <input value={createName} onChange={(event) => onCreateNameChange && onCreateNameChange(event.target.value)} style={{ padding: '9px 10px', border: '1px solid #d1d5db', borderRadius: 8 }} />
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '110px 1fr', alignItems: 'center', gap: 10 }}>
            <label>复制配置</label>
            <select
              value={createFromId}
              onChange={(event) => onCreateFromIdChange && onCreateFromIdChange(event.target.value)}
              style={{ padding: '9px 10px', border: '1px solid #d1d5db', borderRadius: 8 }}
              disabled={!kbList.length}
            >
              {kbList.map((dataset) => (
                <option key={String(dataset?.id || '')} value={String(dataset?.id || '')}>
                  {String(dataset?.name || dataset?.id || '')}
                </option>
              ))}
            </select>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '110px 1fr', alignItems: 'center', gap: 10, marginTop: 10 }}>
            <label>挂载目录</label>
            <select value={createDirId} onChange={(event) => onCreateDirIdChange && onCreateDirIdChange(event.target.value)} style={{ padding: '9px 10px', border: '1px solid #d1d5db', borderRadius: 8 }}>
              {dirOptions.map((option) => (
                <option key={option.id || '__root__'} value={option.id}>{option.label}</option>
              ))}
            </select>
          </div>
          {createError ? <div style={{ color: '#b91c1c', marginTop: 10 }}>{createError}</div> : null}
        </div>
        <div style={{ padding: '12px 14px', borderTop: '1px solid #e5e7eb', display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
          <button type="button" onClick={onClose} style={{ border: '1px solid #d1d5db', borderRadius: 8, background: '#fff', cursor: 'pointer', padding: '8px 12px' }}>取消</button>
          <button type="button" onClick={onCreate} disabled={!isAdmin || kbBusy} style={{ border: '1px solid #2563eb', borderRadius: 8, background: kbBusy ? '#93c5fd' : '#2563eb', color: '#fff', cursor: kbBusy ? 'not-allowed' : 'pointer', padding: '8px 12px' }}>创建</button>
        </div>
      </div>
    </div>
  );
}
