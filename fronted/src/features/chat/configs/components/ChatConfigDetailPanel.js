import React from 'react';

export default function ChatConfigDetailPanel({
  panelStyle,
  isAdmin,
  chatSaveStatus,
  onSave,
  saveDisabled,
  chatDetailError,
  chatLocked,
  onCopyToNewChat,
  onSaveNameOnly,
  onClearParsedFiles,
  busy,
  hasChatSelected,
  chatNameText,
  onChatNameChange,
  kbLoading,
  kbList,
  kbError,
  onRefreshKb,
  selectedDatasetIds,
  onToggleDatasetSelection,
}) {
  return (
    <section style={panelStyle} data-testid="chat-config-detail-panel">
      <div style={{ padding: '14px 16px', borderBottom: '1px solid #e5e7eb' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', gap: '10px' }}>
          <div style={{ fontSize: '1rem', fontWeight: 950, color: '#111827' }}>配置</div>
          <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
            {chatSaveStatus ? <div style={{ color: '#047857', fontWeight: 900 }}>{chatSaveStatus}</div> : null}
            {isAdmin ? (
              <button
                type="button"
                onClick={onSave}
                disabled={saveDisabled}
                data-testid="chat-config-save"
                style={{
                  padding: '10px 14px',
                  borderRadius: '12px',
                  border: '1px solid #047857',
                  background: busy ? '#6ee7b7' : '#10b981',
                  color: '#ffffff',
                  cursor: busy ? 'not-allowed' : 'pointer',
                  fontWeight: 950,
                }}
              >
                保存
              </button>
            ) : null}
          </div>
        </div>
      </div>

      <div style={{ padding: '16px' }}>
        {chatDetailError ? (
          <div data-testid="chat-config-detail-error" style={{ color: '#b91c1c', marginBottom: '10px' }}>
            {chatDetailError}
          </div>
        ) : null}

        {chatLocked ? (
          <div style={{ marginBottom: '12px', display: 'flex', gap: '10px', flexWrap: 'wrap', alignItems: 'center' }}>
            <button
              type="button"
              onClick={onCopyToNewChat}
              disabled={!isAdmin || busy}
              data-testid="chat-config-copy-new"
              style={{
                padding: '8px 12px',
                borderRadius: '10px',
                border: '1px solid #1d4ed8',
                background: '#1d4ed8',
                color: '#ffffff',
                cursor: !isAdmin || busy ? 'not-allowed' : 'pointer',
                fontWeight: 950,
              }}
            >
              复制新对话
            </button>
            <button
              type="button"
              onClick={onSaveNameOnly}
              disabled={!isAdmin || busy}
              data-testid="chat-config-save-name-only"
              style={{
                padding: '8px 12px',
                borderRadius: '10px',
                border: '1px solid #e5e7eb',
                background: '#ffffff',
                color: '#111827',
                cursor: !isAdmin || busy ? 'not-allowed' : 'pointer',
                fontWeight: 950,
              }}
            >
              仅保存名称
            </button>
            <button
              type="button"
              onClick={onClearParsedFiles}
              disabled={!isAdmin || busy || !hasChatSelected}
              data-testid="chat-config-clear-parsed"
              style={{
                padding: '8px 12px',
                borderRadius: '10px',
                border: '1px solid #f59e0b',
                background: '#f59e0b',
                color: '#111827',
                cursor: !isAdmin || busy || !hasChatSelected ? 'not-allowed' : 'pointer',
                fontWeight: 950,
              }}
            >
              清除解析文件绑定
            </button>
          </div>
        ) : null}

        {!hasChatSelected ? (
          <div style={{ color: '#6b7280' }}>未加载</div>
        ) : (
          <>
            <div style={{ display: 'grid', gridTemplateColumns: '160px 1fr', gap: '10px', alignItems: 'center' }}>
              <div style={{ fontWeight: 900, color: '#111827' }}>名称</div>
              <input
                value={chatNameText}
                onChange={(event) => onChatNameChange && onChatNameChange(event.target.value)}
                disabled={!isAdmin}
                data-testid="chat-config-name"
                style={{
                  width: '100%',
                  padding: '10px 12px',
                  borderRadius: '10px',
                  border: '1px solid #e5e7eb',
                  outline: 'none',
                  background: isAdmin ? '#ffffff' : '#f9fafb',
                }}
              />
            </div>

            <div style={{ marginTop: '14px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', gap: '10px' }}>
                <div style={{ fontWeight: 950, color: '#111827' }}>知识库</div>
                <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
                  <div style={{ fontSize: '0.85rem', color: '#6b7280' }}>{kbLoading ? '加载中...' : `${kbList.length} 个`}</div>
                  <button
                    type="button"
                    onClick={onRefreshKb}
                    disabled={kbLoading}
                    data-testid="chat-config-kb-refresh"
                    style={{
                      padding: '8px 10px',
                      borderRadius: '10px',
                      border: '1px solid #e5e7eb',
                      background: kbLoading ? '#f3f4f6' : '#ffffff',
                      cursor: kbLoading ? 'not-allowed' : 'pointer',
                      fontWeight: 800,
                    }}
                  >
                    刷新
                  </button>
                </div>
              </div>

              {kbError ? (
                <div data-testid="chat-config-kb-error" style={{ marginTop: '8px', color: '#b91c1c' }}>
                  {kbError}
                </div>
              ) : null}

              <div style={{ marginTop: '10px', border: '1px solid #e5e7eb', borderRadius: '12px', overflow: 'hidden', background: '#ffffff' }}>
                <div style={{ maxHeight: '220px', overflow: 'auto', padding: '10px', display: 'grid', gap: '8px' }}>
                  {kbList.length === 0 ? (
                    <div style={{ color: '#6b7280' }}>{kbLoading ? '加载中...' : '无知识库'}</div>
                  ) : (
                    kbList.map((kb) => {
                      const id = String(kb?.id || '').trim();
                      const name = String(kb?.name || kb?.title || id || '').trim();
                      const checked = !!id && selectedDatasetIds.includes(id);
                      const safeId = id.replace(/[^a-zA-Z0-9_-]/g, '_');

                      return (
                        <label
                          key={id || name}
                          style={{
                            display: 'flex',
                            gap: '10px',
                            alignItems: 'flex-start',
                            padding: '10px 12px',
                            border: '1px solid #e5e7eb',
                            borderRadius: '12px',
                            background: checked ? '#eff6ff' : '#ffffff',
                            cursor: isAdmin ? 'pointer' : 'default',
                          }}
                        >
                          <input
                            type="checkbox"
                            checked={checked}
                            disabled={!isAdmin || !id}
                            onChange={() => onToggleDatasetSelection && onToggleDatasetSelection(id)}
                            data-testid={`chat-config-kb-check-${safeId}`}
                            style={{ marginTop: '2px' }}
                          />
                          <div style={{ minWidth: 0 }}>
                            <div style={{ fontWeight: 950, color: '#111827', lineHeight: 1.2 }}>{name}</div>
                            <div style={{ marginTop: '4px', color: '#6b7280', fontSize: '0.82rem' }}>ID: {id || '(unknown)'}</div>
                          </div>
                        </label>
                      );
                    })
                  )}
                </div>
              </div>

              <div style={{ marginTop: '8px', color: '#6b7280', fontSize: '0.85rem' }}>勾选知识库后，点击右上角保存才会生效。</div>
            </div>
          </>
        )}
      </div>
    </section>
  );
}
