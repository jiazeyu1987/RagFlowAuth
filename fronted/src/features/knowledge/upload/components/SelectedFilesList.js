import React, { useEffect, useState } from 'react';
import { formatBytes, getDisplayPath, getFileUniqueKey } from '../utils';

const MOBILE_BREAKPOINT = 768;

export default function SelectedFilesList({
  selectedFiles,
  uploading,
  onClear,
  onRemove,
}) {
  const [isMobile, setIsMobile] = useState(() => {
    if (typeof window === 'undefined') return false;
    return window.innerWidth <= MOBILE_BREAKPOINT;
  });

  useEffect(() => {
    if (typeof window === 'undefined') return undefined;
    const handleResize = () => setIsMobile(window.innerWidth <= MOBILE_BREAKPOINT);
    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  if (!selectedFiles.length) return null;

  return (
    <div style={{ marginTop: 12 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: isMobile ? 'stretch' : 'center', marginBottom: 8, gap: '8px', flexDirection: isMobile ? 'column' : 'row' }}>
        <div style={{ fontSize: '0.9rem', color: '#374151', fontWeight: 500 }}>已选择文件</div>
        <button type="button" disabled={uploading} onClick={onClear} data-testid="upload-files-clear" style={{ padding: '6px 10px', backgroundColor: '#6b7280', color: 'white', border: 'none', borderRadius: 6, cursor: uploading ? 'not-allowed' : 'pointer', fontSize: '0.85rem', width: isMobile ? '100%' : 'auto' }}>
          清空
        </button>
      </div>
      <div style={{ border: '1px solid #e5e7eb', borderRadius: 8, overflow: 'hidden' }}>
        {selectedFiles.map((file) => {
          const key = getFileUniqueKey(file);
          const displayPath = getDisplayPath(file);
          return (
            <div key={key} data-testid={`upload-file-item-${key}`} style={{ display: 'flex', justifyContent: 'space-between', alignItems: isMobile ? 'stretch' : 'center', flexDirection: isMobile ? 'column' : 'row', padding: '10px 12px', borderBottom: '1px solid #f3f4f6', backgroundColor: 'white', gap: 12 }}>
              <div style={{ minWidth: 0, width: '100%' }}>
                <div style={{ fontSize: '0.95rem', color: '#111827', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: isMobile ? 'normal' : 'nowrap', wordBreak: 'break-all' }}>{file.name}</div>
                <div style={{ fontSize: '0.82rem', color: '#6b7280', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: isMobile ? 'normal' : 'nowrap', wordBreak: 'break-all' }}>{displayPath}</div>
                <div style={{ fontSize: '0.85rem', color: '#6b7280' }}>{formatBytes(file.size)}</div>
              </div>
              <button type="button" disabled={uploading} onClick={() => onRemove && onRemove(key)} data-testid={`upload-file-remove-${key}`} style={{ padding: '6px 10px', backgroundColor: '#ef4444', color: 'white', border: 'none', borderRadius: 6, cursor: uploading ? 'not-allowed' : 'pointer', fontSize: '0.85rem', flexShrink: 0, width: isMobile ? '100%' : 'auto' }}>
                移除
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
}
