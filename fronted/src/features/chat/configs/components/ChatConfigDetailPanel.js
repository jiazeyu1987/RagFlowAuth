import React from 'react';

function coerceCount(value) {
  const num = Number(value);
  return Number.isFinite(num) ? num : null;
}

function getKnowledgeBaseReadyState(kb) {
  const chunkCount = coerceCount(kb?.chunk_count ?? kb?.chunkCount ?? kb?.chunk_num);
  const documentCount = coerceCount(kb?.document_count ?? kb?.documentCount);

  if (chunkCount !== null) {
    return {
      ready: chunkCount > 0,
      chunkCount,
      documentCount,
    };
  }

  if (documentCount !== null) {
    return {
      ready: documentCount > 0,
      chunkCount: null,
      documentCount,
    };
  }

  return {
    ready: true,
    chunkCount: null,
    documentCount: null,
  };
}

function getKnowledgeBaseStatusText(state) {
  if (!state.ready) {
    if (state.documentCount !== null && state.documentCount <= 0) {
      return '暂无文档，暂不可绑定对话';
    }
    return '未解析完成，暂不可绑定对话';
  }
  if (state.chunkCount !== null) {
    return `已解析 ${state.chunkCount} 个分片`;
  }
  if (state.documentCount !== null) {
    return `文档 ${state.documentCount} 个`;
  }
  return '可绑定到对话';
}

export default function ChatConfigDetailPanel({
  panelStyle,
  isMobile,
  canManageChats,
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
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: isMobile ? 'stretch' : 'baseline',
            gap: '10px',
            flexDirection: isMobile ? 'column' : 'row',
          }}
        >
          <div style={{ fontSize: '1rem', fontWeight: 950, color: '#111827' }}>配置详情</div>
          <div
            style={{
              display: 'flex',
              gap: '10px',
              alignItems: isMobile ? 'stretch' : 'center',
              width: isMobile ? '100%' : 'auto',
              flexDirection: isMobile ? 'column' : 'row',
            }}
          >
            {chatSaveStatus ? <div style={{ color: '#047857', fontWeight: 900 }}>{chatSaveStatus}</div> : null}
            {canManageChats ? (
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
                  width: isMobile ? '100%' : 'auto',
                }}
              >
                保存配置
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
          <div
            style={{
              marginBottom: '12px',
              display: 'flex',
              gap: '10px',
              flexWrap: 'wrap',
              alignItems: isMobile ? 'stretch' : 'center',
              flexDirection: isMobile ? 'column' : 'row',
            }}
          >
            <button
              type="button"
              onClick={onCopyToNewChat}
              disabled={!canManageChats || busy}
              data-testid="chat-config-copy-new"
              style={{
                padding: '8px 12px',
                borderRadius: '10px',
                border: '1px solid #1d4ed8',
                background: '#1d4ed8',
                color: '#ffffff',
                cursor: !canManageChats || busy ? 'not-allowed' : 'pointer',
                fontWeight: 950,
                width: isMobile ? '100%' : 'auto',
              }}
            >
              复制为新对话
            </button>
            <button
              type="button"
              onClick={onSaveNameOnly}
              disabled={!canManageChats || busy}
              data-testid="chat-config-save-name-only"
              style={{
                padding: '8px 12px',
                borderRadius: '10px',
                border: '1px solid #e5e7eb',
                background: '#ffffff',
                color: '#111827',
                cursor: !canManageChats || busy ? 'not-allowed' : 'pointer',
                fontWeight: 950,
                width: isMobile ? '100%' : 'auto',
              }}
            >
              仅保存名称
            </button>
            <button
              type="button"
              onClick={onClearParsedFiles}
              disabled={!canManageChats || busy || !hasChatSelected}
              data-testid="chat-config-clear-parsed"
              style={{
                padding: '8px 12px',
                borderRadius: '10px',
                border: '1px solid #f59e0b',
                background: '#f59e0b',
                color: '#111827',
                cursor: !canManageChats || busy || !hasChatSelected ? 'not-allowed' : 'pointer',
                fontWeight: 950,
                width: isMobile ? '100%' : 'auto',
              }}
            >
              清除解析文件绑定
            </button>
          </div>
        ) : null}

        {!hasChatSelected ? (
          <div style={{ color: '#6b7280' }}>尚未选择对话配置</div>
        ) : (
          <>
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: isMobile ? '1fr' : '160px 1fr',
                gap: '10px',
                alignItems: 'center',
              }}
            >
              <div style={{ fontWeight: 900, color: '#111827' }}>名称</div>
              <input
                value={chatNameText}
                onChange={(event) => onChatNameChange && onChatNameChange(event.target.value)}
                disabled={!canManageChats}
                data-testid="chat-config-name"
                style={{
                  width: '100%',
                  padding: '10px 12px',
                  borderRadius: '10px',
                  border: '1px solid #e5e7eb',
                  outline: 'none',
                  background: canManageChats ? '#ffffff' : '#f9fafb',
                  boxSizing: 'border-box',
                }}
              />
            </div>

            <div style={{ marginTop: '14px' }}>
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: isMobile ? 'stretch' : 'baseline',
                  gap: '10px',
                  flexDirection: isMobile ? 'column' : 'row',
                }}
              >
                <div style={{ fontWeight: 950, color: '#111827' }}>知识库</div>
                <div
                  style={{
                    display: 'flex',
                    gap: '10px',
                    alignItems: isMobile ? 'stretch' : 'center',
                    width: isMobile ? '100%' : 'auto',
                    flexDirection: isMobile ? 'column' : 'row',
                  }}
                >
                  <div style={{ fontSize: '0.85rem', color: '#6b7280' }}>
                    {kbLoading ? '加载中...' : `${kbList.length} 个`}
                  </div>
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
                      width: isMobile ? '100%' : 'auto',
                    }}
                  >
                    刷新知识库
                  </button>
                </div>
              </div>

              {kbError ? (
                <div data-testid="chat-config-kb-error" style={{ marginTop: '8px', color: '#b91c1c' }}>
                  {kbError}
                </div>
              ) : null}

              <div
                style={{
                  marginTop: '10px',
                  border: '1px solid #e5e7eb',
                  borderRadius: '12px',
                  overflow: 'hidden',
                  background: '#ffffff',
                }}
              >
                <div
                  style={{
                    maxHeight: isMobile ? '280px' : '220px',
                    overflow: 'auto',
                    padding: '10px',
                    display: 'grid',
                    gap: '8px',
                  }}
                >
                  {kbList.length === 0 ? (
                    <div style={{ color: '#6b7280' }}>{kbLoading ? '加载中...' : '暂无知识库'}</div>
                  ) : (
                    kbList.map((kb) => {
                      const id = String(kb?.id || '').trim();
                      const name = String(kb?.name || kb?.title || id || '').trim();
                      const checked = !!id && selectedDatasetIds.includes(id);
                      const safeId = id.replace(/[^a-zA-Z0-9_-]/g, '_');
                      const state = getKnowledgeBaseReadyState(kb);
                      const disabled = !canManageChats || !id || (!state.ready && !checked);

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
                            cursor: disabled ? 'not-allowed' : 'pointer',
                            opacity: !state.ready && !checked ? 0.65 : 1,
                          }}
                        >
                          <input
                            type="checkbox"
                            checked={checked}
                            disabled={disabled}
                            onChange={() => onToggleDatasetSelection && onToggleDatasetSelection(id)}
                            data-testid={`chat-config-kb-check-${safeId}`}
                            style={{ marginTop: '2px' }}
                          />
                          <div style={{ minWidth: 0 }}>
                            <div style={{ fontWeight: 950, color: '#111827', lineHeight: 1.2, wordBreak: 'break-word' }}>
                              {name}
                            </div>
                            <div style={{ marginTop: '4px', color: state.ready ? '#6b7280' : '#b45309', fontSize: '0.82rem' }}>
                              {getKnowledgeBaseStatusText(state)}
                            </div>
                            <div
                              style={{
                                marginTop: '4px',
                                color: '#6b7280',
                                fontSize: '0.82rem',
                                wordBreak: 'break-all',
                              }}
                            >
                              ID: {id || '未知'}
                            </div>
                          </div>
                        </label>
                      );
                    })
                  )}
                </div>
              </div>

              <div style={{ marginTop: '8px', color: '#6b7280', fontSize: '0.85rem' }}>
                只能绑定已经完成解析的知识库。勾选后点击右上角“保存配置”才会生效。
              </div>
            </div>
          </>
        )}
      </div>
    </section>
  );
}
