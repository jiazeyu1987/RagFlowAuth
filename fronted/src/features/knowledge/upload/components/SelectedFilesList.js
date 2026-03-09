import React from 'react';
import { formatBytes, getDisplayPath, getFileUniqueKey } from '../utils';

export default function SelectedFilesList({
  selectedFiles,
  uploading,
  onClear,
  onRemove,
}) {
  if (!selectedFiles.length) return null;

  return (
    <div style={{ marginTop: 12 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
        <div style={{ fontSize: '0.9rem', color: '#374151', fontWeight: 500 }}>已选择文件</div>
        <button
          type="button"
          disabled={uploading}
          onClick={onClear}
          data-testid="upload-files-clear"
          style={{
            padding: '6px 10px',
            backgroundColor: '#6b7280',
            color: 'white',
            border: 'none',
            borderRadius: 6,
            cursor: uploading ? 'not-allowed' : 'pointer',
            fontSize: '0.85rem',
          }}
        >
          清空
        </button>
      </div>
      <div style={{ border: '1px solid #e5e7eb', borderRadius: 8, overflow: 'hidden' }}>
        {selectedFiles.map((file) => {
          const key = getFileUniqueKey(file);
          const displayPath = getDisplayPath(file);
          return (
            <div
              key={key}
              data-testid={`upload-file-item-${key}`}
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                padding: '10px 12px',
                borderBottom: '1px solid #f3f4f6',
                backgroundColor: 'white',
                gap: 12,
              }}
            >
              <div style={{ minWidth: 0 }}>
                <div style={{ fontSize: '0.95rem', color: '#111827', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {file.name}
                </div>
                <div style={{ fontSize: '0.82rem', color: '#6b7280', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {displayPath}
                </div>
                <div style={{ fontSize: '0.85rem', color: '#6b7280' }}>{formatBytes(file.size)}</div>
              </div>
              <button
                type="button"
                disabled={uploading}
                onClick={() => onRemove && onRemove(key)}
                data-testid={`upload-file-remove-${key}`}
                style={{
                  padding: '6px 10px',
                  backgroundColor: '#ef4444',
                  color: 'white',
                  border: 'none',
                  borderRadius: 6,
                  cursor: uploading ? 'not-allowed' : 'pointer',
                  fontSize: '0.85rem',
                  flexShrink: 0,
                }}
              >
                移除
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
}
