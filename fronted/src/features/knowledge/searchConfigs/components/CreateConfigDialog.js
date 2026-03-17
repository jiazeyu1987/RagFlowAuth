import React from 'react';

const modeButtonStyle = (active, isMobile) => ({
  flex: isMobile ? '1 1 100%' : '1 1 140px',
  padding: '10px 12px',
  borderRadius: '10px',
  border: `1px solid ${active ? '#1d4ed8' : '#e5e7eb'}`,
  background: active ? '#1d4ed8' : '#ffffff',
  color: active ? '#ffffff' : '#111827',
  cursor: 'pointer',
  fontWeight: 800,
  width: isMobile ? '100%' : 'auto',
});

export default function CreateConfigDialog({
  open,
  list,
  busy,
  mode,
  name,
  fromId,
  jsonText,
  error,
  isMobile,
  onClose,
  onChangeMode,
  onChangeName,
  onChangeFromId,
  onChangeJsonText,
  onCreate,
}) {
  if (!open) return null;

  return (
    <div onClick={onClose} style={{ position: 'fixed', inset: 0, background: 'rgba(15, 23, 42, 0.45)', display: 'flex', alignItems: isMobile ? 'stretch' : 'center', justifyContent: 'center', padding: isMobile ? '12px' : '18px', zIndex: 9999 }}>
      <div onClick={(event) => event.stopPropagation()} style={{ width: 'min(900px, 96vw)', maxHeight: isMobile ? '100%' : '90vh', background: '#ffffff', borderRadius: '16px', border: '1px solid #e5e7eb', overflow: 'hidden', boxShadow: '0 24px 80px rgba(0, 0, 0, 0.25)', display: 'flex', flexDirection: 'column', margin: isMobile ? 'auto 0' : 0 }}>
        <div style={{ padding: '14px 16px', borderBottom: '1px solid #e5e7eb', display: 'flex', justifyContent: 'space-between', alignItems: isMobile ? 'stretch' : 'center', flexDirection: isMobile ? 'column' : 'row', gap: '10px' }}>
          <div style={{ fontWeight: 900 }}>新建搜索配置</div>
          <button onClick={onClose} style={{ border: 'none', background: 'transparent', cursor: 'pointer', fontSize: '18px', fontWeight: 900, alignSelf: isMobile ? 'flex-end' : 'auto' }}>×</button>
        </div>

        <div style={{ padding: '14px 16px', overflowY: 'auto' }}>
          <div style={{ display: 'grid', gridTemplateColumns: isMobile ? '1fr' : '1fr 1fr', gap: '12px' }}>
            <div>
              <div style={{ fontWeight: 900, color: '#111827' }}>创建方式</div>
              <div style={{ display: 'flex', gap: '10px', marginTop: '8px', flexDirection: isMobile ? 'column' : 'row' }}>
                <button onClick={() => onChangeMode('blank')} style={modeButtonStyle(mode === 'blank', isMobile)}>空白创建</button>
                <button onClick={() => onChangeMode('copy')} style={modeButtonStyle(mode === 'copy', isMobile)}>复制现有配置</button>
              </div>
            </div>
            <div>
              <div style={{ fontWeight: 900, color: '#111827' }}>名称</div>
              <input value={name} onChange={(event) => onChangeName(event.target.value)} placeholder="请输入名称" style={{ width: '100%', marginTop: '8px', padding: '10px 12px', borderRadius: '12px', border: '1px solid #e5e7eb', outline: 'none', fontWeight: 700, boxSizing: 'border-box' }} />
            </div>
          </div>

          {mode === 'copy' ? (
            <div style={{ paddingTop: '14px' }}>
              <div style={{ fontWeight: 900, color: '#111827' }}>从现有配置复制</div>
              <select value={fromId} onChange={(event) => onChangeFromId(event.target.value)} style={{ width: '100%', marginTop: '8px', padding: '10px 12px', borderRadius: '12px', border: '1px solid #e5e7eb', outline: 'none', fontWeight: 700, background: '#ffffff', boxSizing: 'border-box' }}>
                <option value="">请选择...</option>
                {list.map((item) => (
                  <option key={item.id} value={item.id}>{item.name || item.id}</option>
                ))}
              </select>
            </div>
          ) : null}

          <div style={{ paddingTop: '16px' }}>
            <div style={{ fontWeight: 900, color: '#111827' }}>配置 JSON</div>
            <textarea value={jsonText} onChange={(event) => onChangeJsonText(event.target.value)} spellCheck={false} style={{ width: '100%', minHeight: isMobile ? '220px' : '240px', marginTop: '8px', borderRadius: '12px', border: '1px solid #e5e7eb', padding: '12px', fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace', fontSize: '12px', outline: 'none', boxSizing: 'border-box' }} />
            {error ? <div style={{ marginTop: '10px', color: '#b91c1c', fontWeight: 800 }}>{error}</div> : null}
          </div>
        </div>

        <div style={{ padding: '14px 16px', borderTop: '1px solid #e5e7eb', display: 'flex', justifyContent: 'flex-end', gap: '10px', flexDirection: isMobile ? 'column' : 'row' }}>
          <button onClick={onClose} style={{ padding: '10px 14px', borderRadius: '12px', border: '1px solid #e5e7eb', background: '#ffffff', cursor: 'pointer', fontWeight: 800, width: isMobile ? '100%' : 'auto' }}>取消</button>
          <button onClick={onCreate} disabled={busy} style={{ padding: '10px 14px', borderRadius: '12px', border: '1px solid #1d4ed8', background: busy ? '#93c5fd' : '#2563eb', color: '#ffffff', cursor: busy ? 'not-allowed' : 'pointer', fontWeight: 900, width: isMobile ? '100%' : 'auto' }}>创建</button>
        </div>
      </div>
    </div>
  );
}
