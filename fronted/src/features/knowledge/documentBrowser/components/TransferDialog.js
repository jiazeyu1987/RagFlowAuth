import React from 'react';
import { TEXT } from '../constants';

export default function TransferDialog({
  transferDialog,
  selectedCount,
  transferTargetOptions,
  onClose,
  onConfirm,
  onChangeTarget,
}) {
  if (!transferDialog) return null;

  const options = transferDialog.scope === 'single'
    ? transferTargetOptions.filter((name) => name !== transferDialog.sourceDatasetName)
    : transferTargetOptions;

  return (
    <div className="medui-modal-backdrop">
      <div className="medui-modal" style={{ maxWidth: 520 }}>
        <div className="medui-modal__head">
          <div className="medui-modal__title">
            {transferDialog.operation === 'move' ? TEXT.transferTitleMove : TEXT.transferTitleCopy}
          </div>
        </div>
        <div className="medui-modal__body">
          <div className="medui-subtitle" style={{ marginBottom: 10 }}>
            {transferDialog.scope === 'single'
              ? `${transferDialog.sourceDatasetName} / ${transferDialog.docId}`
              : `已选择 ${selectedCount} 个文档`}
          </div>
          <label style={{ display: 'block', marginBottom: 6, color: '#365774', fontWeight: 700 }}>{TEXT.targetKb}</label>
          <select
            value={transferDialog.targetDatasetName}
            onChange={(event) => onChangeTarget && onChangeTarget(event.target.value)}
            className="medui-select"
          >
            {options.map((name) => (
              <option key={name} value={name}>{name}</option>
            ))}
          </select>
        </div>
        <div className="medui-modal__foot">
          <button type="button" onClick={onClose} className="medui-btn medui-btn--neutral">{TEXT.cancel}</button>
          <button type="button" onClick={onConfirm} className="medui-btn medui-btn--primary">{TEXT.confirm}</button>
        </div>
      </div>
    </div>
  );
}
