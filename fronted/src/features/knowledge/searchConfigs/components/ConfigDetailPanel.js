import React from 'react';

export default function ConfigDetailPanel({
  panelClassName,
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
    <section className={panelClassName}>
      <div className="admin-med-panel__head">
        <div className="admin-med-head">
          <div style={{ fontWeight: 700, color: '#163f63' }}>配置详情</div>
          <div className="admin-med-inline-note">{selected?.name || '未选择'}</div>
        </div>
      </div>

      <div className="admin-med-panel__body">
        {detailLoading ? <div className="medui-empty" style={{ paddingTop: 4 }}>加载中...</div> : null}
        {detailError ? <div className="admin-med-danger">{detailError}</div> : null}
        {!selected && !detailLoading ? <div className="medui-empty">请先选择左侧配置项</div> : null}

        {selected ? (
          <>
            <div className="admin-med-form-grid admin-med-form-grid--2">
              <div style={{ fontWeight: 700, color: '#17324d' }}>配置名称</div>
              <input
                value={nameText}
                disabled={!isAdmin}
                onChange={(event) => onChangeName(event.target.value)}
                placeholder="请输入配置名称"
                className="medui-input"
                style={{ background: !isAdmin ? '#f5f9fd' : '#fff' }}
              />
            </div>

            <div className="admin-med-head" style={{ marginTop: 14 }}>
              <div style={{ fontWeight: 700, color: '#17324d' }}>配置 JSON</div>
              <div className="admin-med-actions">
                <button type="button" onClick={onReset} disabled={busy} className="medui-btn medui-btn--neutral">
                  重置
                </button>
                {isAdmin ? (
                  <button type="button" onClick={onSave} disabled={busy} className="medui-btn medui-btn--primary">
                    保存
                  </button>
                ) : null}
              </div>
            </div>

            <textarea
              value={jsonText}
              disabled={!isAdmin}
              onChange={(event) => onChangeJson(event.target.value)}
              spellCheck={false}
              className="medui-textarea admin-med-code"
              style={{ minHeight: 360, marginTop: 10, background: !isAdmin ? '#f5f9fd' : '#fff' }}
            />

            {saveStatus ? <div className="admin-med-success" style={{ marginTop: 10 }}>{saveStatus}</div> : null}
          </>
        ) : null}
      </div>
    </section>
  );
}
