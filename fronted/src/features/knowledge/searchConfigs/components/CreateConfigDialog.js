import React from 'react';

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
    <div onClick={onClose} className="admin-med-dialog">
      <div onClick={(event) => event.stopPropagation()} className="admin-med-dialog__panel">
        <div className="admin-med-dialog__head">
          <div style={{ fontWeight: 700, color: '#163f63' }}>创建检索配置</div>
          <button type="button" onClick={onClose} className="medui-btn medui-btn--secondary">
            关闭
          </button>
        </div>

        <div className="admin-med-dialog__body">
          <div className="admin-med-form-grid admin-med-form-grid--2">
            <div style={{ fontWeight: 700, color: '#17324d' }}>创建方式</div>
            <div className="admin-med-actions">
              <button type="button" onClick={() => onChangeMode('blank')} className={`medui-btn ${mode === 'blank' ? 'medui-btn--primary' : 'medui-btn--secondary'}`}>
                空白创建
              </button>
              <button type="button" onClick={() => onChangeMode('copy')} className={`medui-btn ${mode === 'copy' ? 'medui-btn--primary' : 'medui-btn--secondary'}`}>
                复制现有配置
              </button>
            </div>
          </div>

          <div className="admin-med-form-grid admin-med-form-grid--2">
            <div style={{ fontWeight: 700, color: '#17324d' }}>配置名称</div>
            <input value={name} onChange={(event) => onChangeName(event.target.value)} placeholder="请输入配置名称" className="medui-input" />
          </div>

          {mode === 'copy' ? (
            <div className="admin-med-form-grid admin-med-form-grid--2">
              <div style={{ fontWeight: 700, color: '#17324d' }}>复制来源</div>
              <select value={fromId} onChange={(event) => onChangeFromId(event.target.value)} className="medui-select">
                <option value="">请选择...</option>
                {list.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.name || item.id}
                  </option>
                ))}
              </select>
            </div>
          ) : null}

          <div>
            <div style={{ fontWeight: 700, color: '#17324d', marginBottom: 8 }}>配置 JSON</div>
            <textarea
              value={jsonText}
              onChange={(event) => onChangeJsonText(event.target.value)}
              spellCheck={false}
              className="medui-textarea admin-med-code"
              style={{ minHeight: 260 }}
            />
          </div>

          {error ? <div className="admin-med-danger">{error}</div> : null}
        </div>

        <div className="admin-med-dialog__foot">
          <button type="button" onClick={onClose} className="medui-btn medui-btn--neutral">
            取消
          </button>
          <button type="button" onClick={onCreate} disabled={busy} className="medui-btn medui-btn--primary">
            {busy ? '创建中...' : '创建'}
          </button>
        </div>
      </div>
    </div>
  );
}
