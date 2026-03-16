import React from 'react';

export default function ChatConfigDetailPanel({
  panelClassName,
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
    <section className={panelClassName} data-testid="chat-config-detail-panel">
      <div className="admin-med-panel__head">
        <div className="admin-med-head">
          <div style={{ fontSize: '1rem', fontWeight: 700, color: '#163f63' }}>对话详情</div>
          <div className="admin-med-actions">
            {chatSaveStatus ? <div className="admin-med-success" style={{ padding: '6px 10px' }}>{chatSaveStatus}</div> : null}
            {isAdmin ? (
              <button type="button" onClick={onSave} disabled={saveDisabled} data-testid="chat-config-save" className="medui-btn medui-btn--primary">
                保存
              </button>
            ) : null}
          </div>
        </div>
      </div>

      <div className="admin-med-panel__body">
        {chatDetailError ? <div data-testid="chat-config-detail-error" className="admin-med-danger">{chatDetailError}</div> : null}

        {chatLocked ? (
          <div className="admin-med-actions" style={{ marginTop: chatDetailError ? 10 : 0, marginBottom: 12 }}>
            <button type="button" onClick={onCopyToNewChat} disabled={!isAdmin || busy} data-testid="chat-config-copy-new" className="medui-btn medui-btn--secondary">
              复制为新对话
            </button>
            <button type="button" onClick={onSaveNameOnly} disabled={!isAdmin || busy} data-testid="chat-config-save-name-only" className="medui-btn medui-btn--neutral">
              仅保存名称
            </button>
            <button type="button" onClick={onClearParsedFiles} disabled={!isAdmin || busy || !hasChatSelected} data-testid="chat-config-clear-parsed" className="medui-btn medui-btn--warn">
              清除解析绑定
            </button>
          </div>
        ) : null}

        {!hasChatSelected ? (
          <div className="medui-empty">请选择左侧对话后进行配置</div>
        ) : (
          <>
            <div className="admin-med-form-grid admin-med-form-grid--2">
              <div style={{ fontWeight: 700, color: '#17324d' }}>对话名称</div>
              <input
                value={chatNameText}
                onChange={(event) => onChatNameChange && onChatNameChange(event.target.value)}
                disabled={!isAdmin}
                data-testid="chat-config-name"
                className="medui-input"
                style={{ background: isAdmin ? '#fff' : '#f5f9fd' }}
              />
            </div>

            <div style={{ marginTop: 14 }}>
              <div className="admin-med-head">
                <div style={{ fontWeight: 700, color: '#17324d' }}>关联知识库</div>
                <div className="admin-med-actions">
                  <div className="admin-med-inline-note">{kbLoading ? '加载中...' : `共 ${kbList.length} 个`}</div>
                  <button type="button" onClick={onRefreshKb} disabled={kbLoading} data-testid="chat-config-kb-refresh" className="medui-btn medui-btn--secondary">
                    刷新
                  </button>
                </div>
              </div>

              {kbError ? <div data-testid="chat-config-kb-error" className="admin-med-danger" style={{ marginTop: 8 }}>{kbError}</div> : null}

              <div className="admin-med-kb-list" style={{ marginTop: 10 }}>
                {kbList.length === 0 ? (
                  <div className="medui-empty" style={{ padding: '12px 0' }}>{kbLoading ? '加载中...' : '暂无知识库'}</div>
                ) : (
                  kbList.map((kb) => {
                    const id = String(kb?.id || '').trim();
                    const name = String(kb?.name || kb?.title || id || '').trim();
                    const checked = !!id && selectedDatasetIds.includes(id);
                    const safeId = id.replace(/[^a-zA-Z0-9_-]/g, '_');

                    return (
                      <label key={id || name} className={`admin-med-kb-item${checked ? ' is-active' : ''}`}>
                        <input
                          type="checkbox"
                          checked={checked}
                          disabled={!isAdmin || !id}
                          onChange={() => onToggleDatasetSelection && onToggleDatasetSelection(id)}
                          data-testid={`chat-config-kb-check-${safeId}`}
                          style={{ marginTop: 2 }}
                        />
                        <div style={{ minWidth: 0 }}>
                          <div style={{ fontWeight: 700, color: '#16324d', lineHeight: 1.2 }}>{name}</div>
                          <div className="admin-med-small" style={{ marginTop: 4 }}>{`编号：${id || '（未知）'}`}</div>
                        </div>
                      </label>
                    );
                  })
                )}
              </div>

              <div className="admin-med-inline-note" style={{ marginTop: 8 }}>
                勾选后点击页面顶部“保存”，才会写入对话配置。
              </div>
            </div>
          </>
        )}
      </div>
    </section>
  );
}
