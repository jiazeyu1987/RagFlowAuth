import React from 'react';

import { BUTTON_STYLES } from '../utils';

export default function NasBrowserImportDialog({
  isMobile,
  importDialogOpen,
  importTarget,
  datasets,
  selectedKb,
  setSelectedKb,
  importLoading,
  closeImportDialog,
  handleImport,
}) {
  if (!importDialogOpen || !importTarget) {
    return null;
  }

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(15, 23, 42, 0.45)',
        display: 'flex',
        alignItems: isMobile ? 'flex-end' : 'center',
        justifyContent: 'center',
        padding: isMobile ? '16px' : '24px',
        zIndex: 50,
      }}
      onClick={closeImportDialog}
    >
      <div
        data-testid="nas-import-dialog"
        style={{
          width: 'min(520px, 100%)',
          maxHeight: '90vh',
          overflowY: 'auto',
          background: '#fff',
          borderRadius: isMobile ? '14px' : '16px',
          padding: isMobile ? '16px' : '20px',
          border: '1px solid #e5e7eb',
        }}
        onClick={(event) => event.stopPropagation()}
      >
        <div style={{ fontSize: '1.15rem', fontWeight: 800, color: '#111827' }}>
          {importTarget.is_dir ? '上传文件夹到知识库' : '上传文件到知识库'}
        </div>
        <div style={{ marginTop: '10px', color: '#475569', lineHeight: 1.6 }}>
          名称: {importTarget.name}
          <br />
          路径: {importTarget.path}
          <br />
          {importTarget.is_dir
            ? '会先统计支持格式的文件数量，然后递归上传当前文件夹及其子目录中的文件。'
            : '仅上传当前文件，并且只支持知识库允许的文件格式。'}
        </div>
        <div style={{ marginTop: '16px' }}>
          <label
            style={{
              display: 'block',
              marginBottom: '8px',
              fontWeight: 700,
              color: '#111827',
            }}
          >
            选择知识库
          </label>
          <select
            data-testid="nas-import-kb-select"
            value={selectedKb}
            onChange={(event) => setSelectedKb(event.target.value)}
            style={{
              width: '100%',
              padding: '10px 12px',
              borderRadius: '10px',
              border: '1px solid #d1d5db',
              background: '#fff',
            }}
          >
            {datasets.map((ds) => (
              <option key={ds.id} value={ds.name}>
                {ds.name}
              </option>
            ))}
          </select>
        </div>
        <div
          style={{
            marginTop: '18px',
            display: 'flex',
            flexDirection: isMobile ? 'column' : 'row',
            justifyContent: 'flex-end',
            gap: '10px',
          }}
        >
          <button
            type="button"
            onClick={closeImportDialog}
            disabled={importLoading}
            data-testid="nas-import-cancel"
            style={{
              ...BUTTON_STYLES.neutral,
              cursor: importLoading ? 'not-allowed' : 'pointer',
              width: isMobile ? '100%' : 'auto',
            }}
          >
            取消
          </button>
          <button
            type="button"
            onClick={handleImport}
            disabled={importLoading || !selectedKb}
            data-testid="nas-import-confirm"
            style={{
              ...BUTTON_STYLES.primary,
              border: 'none',
              background: importLoading || !selectedKb ? '#94a3b8' : '#2563eb',
              color: '#fff',
              cursor:
                importLoading || !selectedKb ? 'not-allowed' : 'pointer',
              width: isMobile ? '100%' : 'auto',
            }}
          >
            {importLoading ? '处理中...' : '开始上传'}
          </button>
        </div>
      </div>
    </div>
  );
}
