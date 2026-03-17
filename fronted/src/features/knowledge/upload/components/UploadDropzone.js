import React, { useEffect, useRef, useState } from 'react';

const MOBILE_BREAKPOINT = 768;

export default function UploadDropzone({
  uploading,
  dragActive,
  selectedFilesLength,
  uploadProgress,
  acceptAttr,
  onDragOver,
  onDragLeave,
  onDrop,
  onFileSelect,
  onFolderSelect,
}) {
  const [isMobile, setIsMobile] = useState(() => {
    if (typeof window === 'undefined') return false;
    return window.innerWidth <= MOBILE_BREAKPOINT;
  });
  const fileInputRef = useRef(null);
  const folderInputRef = useRef(null);

  useEffect(() => {
    if (typeof window === 'undefined') return undefined;
    const handleResize = () => setIsMobile(window.innerWidth <= MOBILE_BREAKPOINT);
    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const openFileInput = () => {
    if (uploading) return;
    fileInputRef.current?.click();
  };

  const openFolderInput = () => {
    if (uploading) return;
    folderInputRef.current?.click();
  };

  return (
    <div style={{ marginBottom: '24px' }}>
      <label style={{ display: 'block', marginBottom: '8px', fontWeight: '500', color: '#374151' }}>选择文件</label>
      <div style={{ display: 'flex', gap: '10px', marginBottom: '12px', flexWrap: 'wrap', flexDirection: isMobile ? 'column' : 'row' }}>
        <button type="button" disabled={uploading} onClick={openFileInput} style={{ padding: '10px 14px', backgroundColor: uploading ? '#9ca3af' : '#2563eb', color: 'white', border: 'none', borderRadius: '6px', cursor: uploading ? 'not-allowed' : 'pointer', fontSize: '0.9rem', fontWeight: 500, width: isMobile ? '100%' : 'auto' }}>
          选择文件
        </button>
        <button type="button" disabled={uploading} onClick={openFolderInput} style={{ padding: '10px 14px', backgroundColor: uploading ? '#9ca3af' : '#0f766e', color: 'white', border: 'none', borderRadius: '6px', cursor: uploading ? 'not-allowed' : 'pointer', fontSize: '0.9rem', fontWeight: 500, width: isMobile ? '100%' : 'auto' }}>
          选择文件夹
        </button>
      </div>

      <div data-testid="upload-file-dropzone" style={{ border: `2px dashed ${dragActive ? '#3b82f6' : '#d1d5db'}`, borderRadius: '4px', padding: isMobile ? '24px 16px' : '40px', textAlign: 'center', cursor: 'pointer', transition: 'border-color 0.2s', backgroundColor: dragActive ? '#eff6ff' : 'transparent' }} onDragOver={onDragOver} onDragLeave={onDragLeave} onDrop={onDrop} onClick={openFileInput}>
        <input ref={fileInputRef} type="file" onChange={onFileSelect} accept={acceptAttr} multiple style={{ display: 'none' }} data-testid="upload-file-input" />
        <input ref={folderInputRef} type="file" onChange={onFolderSelect} accept={acceptAttr} multiple webkitdirectory="" directory="" style={{ display: 'none' }} data-testid="upload-folder-input" />
        <div style={{ fontSize: isMobile ? '1.5rem' : '2rem', marginBottom: '12px' }}>文件</div>
        <div style={{ color: '#6b7280', marginBottom: '8px', lineHeight: 1.6 }}>
          {selectedFilesLength > 0 ? `已选择 ${selectedFilesLength} 个文件` : '拖动文件到此处，或点击选择文件/文件夹（支持子文件夹）'}
        </div>
        {uploadProgress ? <div style={{ fontSize: '0.9rem', color: '#6b7280', wordBreak: 'break-all' }} data-testid="upload-progress">正在上传 {uploadProgress.current}/{uploadProgress.total}：{uploadProgress.filename}</div> : null}
      </div>
    </div>
  );
}
