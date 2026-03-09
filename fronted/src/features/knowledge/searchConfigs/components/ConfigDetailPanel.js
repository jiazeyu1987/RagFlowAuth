import React from 'react';

export default function ConfigDetailPanel({
  selected,
  detailLoading,
  detailError,
  nameText,
  jsonText,
  saveStatus,
  busy,
  isAdmin,
  onChangeName,
  onChangeJson,
  onReset,
  onSave,
}) {
  return (
    <div
      style={{
        background: '#ffffff',
        border: '1px solid #e5e7eb',
        borderRadius: '12px',
        overflow: 'hidden',
        boxShadow: '0 6px 18px rgba(15, 23, 42, 0.06)',
      }}
    >
      <div
        style={{
          padding: '14px',
          borderBottom: '1px solid #e5e7eb',
          display: 'flex',
          justifyContent: 'space-between',
          gap: '10px',
        }}
      >
        <div style={{ fontWeight: 900, color: '#111827' }}>Config</div>
        <div style={{ color: '#6b7280', fontWeight: 700 }}>{selected?.name || ''}</div>
      </div>

      <div style={{ padding: '14px' }}>
        {detailLoading ? <div style={{ color: '#6b7280' }}>Loading...</div> : null}
        {detailError ? (
          <div style={{ color: '#b91c1c', fontWeight: 800 }}>{detailError}</div>
        ) : null}
        {!selected && !detailLoading ? <div style={{ color: '#6b7280' }}>No selected config</div> : null}

        {selected ? (
          <div>
            <div style={{ fontWeight: 900, color: '#111827', marginTop: '8px' }}>Name</div>
            <input
              value={nameText}
              disabled={!isAdmin}
              onChange={(event) => onChangeName(event.target.value)}
              placeholder="Config name"
              style={{
                width: '100%',
                padding: '10px 12px',
                borderRadius: '12px',
                border: '1px solid #e5e7eb',
                outline: 'none',
                fontWeight: 700,
                marginTop: '8px',
                background: !isAdmin ? '#f9fafb' : '#ffffff',
              }}
            />

            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                marginTop: '14px',
              }}
            >
              <div style={{ fontWeight: 900, color: '#111827' }}>Raw JSON</div>
              <div style={{ display: 'flex', gap: '10px' }}>
                <button
                  onClick={onReset}
                  disabled={busy}
                  style={{
                    padding: '10px 14px',
                    borderRadius: '12px',
                    border: '1px solid #e5e7eb',
                    background: '#ffffff',
                    cursor: busy ? 'not-allowed' : 'pointer',
                    fontWeight: 900,
                  }}
                >
                  Reset
                </button>
                {isAdmin ? (
                  <button
                    onClick={onSave}
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
                    Save
                  </button>
                ) : null}
              </div>
            </div>

            <textarea
              value={jsonText}
              disabled={!isAdmin}
              onChange={(event) => onChangeJson(event.target.value)}
              spellCheck={false}
              style={{
                width: '100%',
                minHeight: '360px',
                marginTop: '10px',
                borderRadius: '12px',
                border: '1px solid #e5e7eb',
                padding: '12px',
                fontFamily:
                  'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace',
                fontSize: '12px',
                outline: 'none',
                background: !isAdmin ? '#f9fafb' : '#ffffff',
              }}
            />

            {saveStatus ? (
              <div style={{ marginTop: '10px', color: '#065f46', fontWeight: 800 }}>
                {saveStatus}
              </div>
            ) : null}
          </div>
        ) : null}
      </div>
    </div>
  );
}
