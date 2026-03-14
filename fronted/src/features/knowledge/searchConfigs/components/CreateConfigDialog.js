import React from 'react';

const modeButtonStyle = (active) => ({
  flex: '1 1 140px',
  padding: '10px 12px',
  borderRadius: '10px',
  border: `1px solid ${active ? '#1d4ed8' : '#e5e7eb'}`,
  background: active ? '#1d4ed8' : '#ffffff',
  color: active ? '#ffffff' : '#111827',
  cursor: 'pointer',
  fontWeight: 800,
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
  onClose,
  onChangeMode,
  onChangeName,
  onChangeFromId,
  onChangeJsonText,
  onCreate,
}) {
  if (!open) return null;

  return (
    <div
      onClick={onClose}
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(15, 23, 42, 0.45)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '18px',
        zIndex: 9999,
      }}
    >
      <div
        onClick={(event) => event.stopPropagation()}
        style={{
          width: 'min(900px, 96vw)',
          background: '#ffffff',
          borderRadius: '16px',
          border: '1px solid #e5e7eb',
          overflow: 'hidden',
          boxShadow: '0 24px 80px rgba(0, 0, 0, 0.25)',
        }}
      >
        <div
          style={{
            padding: '14px 16px',
            borderBottom: '1px solid #e5e7eb',
            display: 'flex',
            justifyContent: 'space-between',
          }}
        >
          <div style={{ fontWeight: 900 }}>创建检索配置</div>
          <button
            onClick={onClose}
            style={{
              border: 'none',
              background: 'transparent',
              cursor: 'pointer',
              fontSize: '18px',
              fontWeight: 900,
            }}
          >
            x
          </button>
        </div>

        <div
          style={{
            padding: '14px 16px',
            display: 'grid',
            gridTemplateColumns: '1fr 1fr',
            gap: '12px',
          }}
        >
          <div>
            <div style={{ fontWeight: 900, color: '#111827' }}>创建方式</div>
            <div style={{ display: 'flex', gap: '10px', marginTop: '8px' }}>
              <button onClick={() => onChangeMode('blank')} style={modeButtonStyle(mode === 'blank')}>
                空白创建
              </button>
              <button onClick={() => onChangeMode('copy')} style={modeButtonStyle(mode === 'copy')}>
                复制现有配置
              </button>
            </div>
          </div>
          <div>
            <div style={{ fontWeight: 900, color: '#111827' }}>名称</div>
            <input
              value={name}
              onChange={(event) => onChangeName(event.target.value)}
              placeholder="请输入名称"
              style={{
                width: '100%',
                marginTop: '8px',
                padding: '10px 12px',
                borderRadius: '12px',
                border: '1px solid #e5e7eb',
                outline: 'none',
                fontWeight: 700,
              }}
            />
          </div>
        </div>

        {mode === 'copy' ? (
          <div style={{ padding: '0 16px 14px' }}>
            <div style={{ fontWeight: 900, color: '#111827' }}>从已有配置复制</div>
            <select
              value={fromId}
              onChange={(event) => onChangeFromId(event.target.value)}
              style={{
                width: '100%',
                marginTop: '8px',
                padding: '10px 12px',
                borderRadius: '12px',
                border: '1px solid #e5e7eb',
                outline: 'none',
                fontWeight: 700,
                background: '#ffffff',
              }}
            >
              <option value="">请选择...</option>
              {list.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.name || item.id}
                </option>
              ))}
            </select>
          </div>
        ) : null}

        <div style={{ padding: '0 16px 16px' }}>
          <div style={{ fontWeight: 900, color: '#111827' }}>配置 JSON</div>
          <textarea
            value={jsonText}
            onChange={(event) => onChangeJsonText(event.target.value)}
            spellCheck={false}
            style={{
              width: '100%',
              minHeight: '240px',
              marginTop: '8px',
              borderRadius: '12px',
              border: '1px solid #e5e7eb',
              padding: '12px',
              fontFamily:
                'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace',
              fontSize: '12px',
              outline: 'none',
            }}
          />
          {error ? (
            <div style={{ marginTop: '10px', color: '#b91c1c', fontWeight: 800 }}>{error}</div>
          ) : null}
        </div>

        <div
          style={{
            padding: '14px 16px',
            borderTop: '1px solid #e5e7eb',
            display: 'flex',
            justifyContent: 'flex-end',
            gap: '10px',
          }}
        >
          <button
            onClick={onClose}
            style={{
              padding: '10px 14px',
              borderRadius: '12px',
              border: '1px solid #e5e7eb',
              background: '#ffffff',
              cursor: 'pointer',
              fontWeight: 800,
            }}
          >
            取消
          </button>
          <button
            onClick={onCreate}
            disabled={busy}
            style={{
              padding: '10px 14px',
              borderRadius: '12px',
              border: '1px solid #1d4ed8',
              background: busy ? '#93c5fd' : '#2563eb',
              color: '#ffffff',
              cursor: busy ? 'not-allowed' : 'pointer',
              fontWeight: 900,
            }}
          >
            创建
          </button>
        </div>
      </div>
    </div>
  );
}
