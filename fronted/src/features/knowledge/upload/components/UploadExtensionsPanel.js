import React from 'react';

export default function UploadExtensionsPanel({
  loadingExtensions,
  acceptAttr,
  allowedExtensions,
  canManageExtensions,
  extensionDraft,
  onExtensionDraftChange,
  onAddExtension,
  onDeleteExtension,
  onSaveExtensions,
  savingExtensions,
  extensionsMessage,
}) {
  return (
    <div style={{ marginBottom: '24px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 16, alignItems: 'center', flexWrap: 'wrap', marginBottom: 8 }}>
        <label style={{ fontWeight: '500', color: '#374151' }}>允许上传的文件后缀</label>
        <div style={{ fontSize: '0.85rem', color: '#6b7280' }}>
          {loadingExtensions ? '正在加载配置...' : `当前配置：${acceptAttr}`}
        </div>
      </div>

      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 12 }}>
        {allowedExtensions.map((extension) => (
          <span
            key={extension}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 8,
              padding: '6px 10px',
              borderRadius: 999,
              backgroundColor: '#eff6ff',
              color: '#1d4ed8',
              fontSize: '0.9rem',
            }}
          >
            {extension}
            {canManageExtensions ? (
              <button
                type="button"
                onClick={() => onDeleteExtension && onDeleteExtension(extension)}
                style={{
                  border: 'none',
                  background: 'transparent',
                  color: '#1d4ed8',
                  cursor: 'pointer',
                  fontWeight: 700,
                  padding: 0,
                  lineHeight: 1,
                }}
                aria-label={`删除 ${extension}`}
              >
                ×
              </button>
            ) : null}
          </span>
        ))}
      </div>

      {canManageExtensions ? (
        <div style={{ border: '1px solid #e5e7eb', borderRadius: 8, padding: 16, backgroundColor: '#f9fafb', marginBottom: 12 }}>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
            <input
              type="text"
              value={extensionDraft}
              onChange={(event) => onExtensionDraftChange && onExtensionDraftChange(event.target.value)}
              onKeyDown={(event) => {
                if (event.key !== 'Enter') return;
                event.preventDefault();
                if (onAddExtension) onAddExtension();
              }}
              placeholder="输入后缀，例如 .dwg 或 dwg"
              style={{
                flex: '1 1 260px',
                minWidth: 220,
                padding: '10px 12px',
                border: '1px solid #d1d5db',
                borderRadius: 6,
                fontSize: '0.95rem',
              }}
            />
            <button
              type="button"
              onClick={onAddExtension}
              style={{
                padding: '10px 14px',
                backgroundColor: '#2563eb',
                color: 'white',
                border: 'none',
                borderRadius: 6,
                cursor: 'pointer',
                fontWeight: 500,
              }}
            >
              添加后缀
            </button>
            <button
              type="button"
              onClick={onSaveExtensions}
              disabled={savingExtensions}
              style={{
                padding: '10px 14px',
                backgroundColor: savingExtensions ? '#9ca3af' : '#059669',
                color: 'white',
                border: 'none',
                borderRadius: 6,
                cursor: savingExtensions ? 'not-allowed' : 'pointer',
                fontWeight: 500,
              }}
            >
              {savingExtensions ? '保存中...' : '保存配置'}
            </button>
          </div>
          <div style={{ marginTop: 10, fontSize: '0.85rem', color: '#6b7280' }}>
            admin 可在这里新增、删除并保存允许上传的文件后缀。修改后会影响后续上传校验。
          </div>
        </div>
      ) : null}

      {extensionsMessage ? (
        <div
          style={{
            marginBottom: 12,
            padding: '10px 12px',
            borderRadius: 6,
            backgroundColor: extensionsMessage.type === 'success' ? '#d1fae5' : '#fee2e2',
            color: extensionsMessage.type === 'success' ? '#065f46' : '#991b1b',
            fontSize: '0.9rem',
          }}
        >
          {extensionsMessage.text}
        </div>
      ) : null}
    </div>
  );
}
