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
      data-testid="kbs-create-dialog"
      aria-modal="true"
      onMouseDown={(event) => event.target === event.currentTarget && onClose && onClose()}
      className="medui-modal-backdrop"
    >
      <div className="medui-modal" style={{ maxWidth: 680 }}>
        <div className="medui-modal__head">
          <div className="medui-header-row">
            <div className="medui-modal__title">创建知识库</div>
            <button type="button" onClick={onClose} className="medui-btn medui-btn--neutral" style={{ height: 32 }}>
              关闭
            </button>
          </div>
        </div>
        <div className="medui-modal__body">
          <div style={{ display: 'grid', gridTemplateColumns: '110px 1fr', alignItems: 'center', gap: 10, marginBottom: 10 }}>
            <label>名称</label>
            <input
              data-testid="kbs-create-name"
              value={createName}
              onChange={(event) => onCreateNameChange && onCreateNameChange(event.target.value)}
              className="medui-input"
            />
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '110px 1fr', alignItems: 'center', gap: 10 }}>
            <label>复制来源</label>
            <select
              value={createFromId}
              onChange={(event) => onCreateFromIdChange && onCreateFromIdChange(event.target.value)}
              className="medui-select"
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
            <label>所属目录</label>
            <select value={createDirId} onChange={(event) => onCreateDirIdChange && onCreateDirIdChange(event.target.value)} className="medui-select">
              {dirOptions.map((option) => (
                <option key={option.id || '__root__'} value={option.id}>{option.label}</option>
              ))}
            </select>
          </div>
          {createError ? <div className="kb-med-error" style={{ marginTop: 10 }}>{createError}</div> : null}
        </div>
        <div className="medui-modal__foot">
          <button type="button" onClick={onClose} className="medui-btn medui-btn--neutral">取消</button>
          <button
            type="button"
            data-testid="kbs-create-submit"
            onClick={onCreate}
            disabled={!isAdmin || kbBusy}
            className="medui-btn medui-btn--primary"
          >
            创建
          </button>
        </div>
      </div>
    </div>
  );
}
