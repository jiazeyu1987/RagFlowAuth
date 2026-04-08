import React from 'react';

import { BUTTON_STYLES, CARD_STYLE } from '../utils';

export default function NasBrowserProgressPanel({
  isMobile,
  folderImportProgress,
  skippedDetails,
  failedDetails,
  closeProgressPanel,
  formatImportReason,
}) {
  if (!folderImportProgress) {
    return null;
  }

  const progressLocked =
    folderImportProgress.status === 'running' ||
    folderImportProgress.status === 'pending';

  return (
    <div
      style={{
        ...CARD_STYLE,
        marginTop: '16px',
        padding: isMobile ? '14px' : '16px 18px',
      }}
    >
      <div
        style={{
          display: 'flex',
          flexDirection: isMobile ? 'column' : 'row',
          justifyContent: 'space-between',
          gap: '12px',
          alignItems: isMobile ? 'stretch' : 'center',
        }}
      >
        <div>
          <div style={{ fontSize: '1rem', fontWeight: 800, color: '#111827' }}>
            文件夹上传进度
          </div>
          <div style={{ marginTop: '4px', color: '#475569' }}>
            路径: {folderImportProgress.folder_path}
          </div>
          <div style={{ marginTop: '4px', color: '#475569' }}>
            知识库: {folderImportProgress.kb_ref}
          </div>
        </div>
        <button
          type="button"
          onClick={closeProgressPanel}
          disabled={progressLocked}
          style={{
            ...BUTTON_STYLES.neutral,
            cursor: progressLocked ? 'not-allowed' : 'pointer',
            width: isMobile ? '100%' : 'auto',
          }}
        >
          关闭
        </button>
      </div>
      <div style={{ marginTop: '14px', color: '#111827', fontWeight: 700 }}>
        待上传文件数: {folderImportProgress.total_files}
      </div>
      <div style={{ marginTop: '8px', color: '#475569' }}>
        当前进度: {folderImportProgress.processed_files} /{' '}
        {folderImportProgress.total_files} ({folderImportProgress.progress_percent}%)
      </div>
      <div
        style={{
          marginTop: '10px',
          height: '10px',
          background: '#e5e7eb',
          borderRadius: '999px',
          overflow: 'hidden',
        }}
      >
        <div
          style={{
            width: `${folderImportProgress.progress_percent}%`,
            height: '100%',
            background:
              folderImportProgress.status === 'failed' ? '#dc2626' : '#2563eb',
            transition: 'width 0.3s ease',
          }}
        />
      </div>
      <div
        style={{
          marginTop: '10px',
          display: 'flex',
          gap: '16px',
          flexWrap: 'wrap',
          color: '#475569',
        }}
      >
        <span>已导入: {folderImportProgress.imported_count}</span>
        <span>跳过: {folderImportProgress.skipped_count}</span>
        <span>失败: {folderImportProgress.failed_count}</span>
        <span>状态: {folderImportProgress.status}</span>
      </div>
      {folderImportProgress.current_file && (
        <div style={{ marginTop: '10px', color: '#1f2937' }}>
          当前文件: {folderImportProgress.current_file}
        </div>
      )}
      {folderImportProgress.error && (
        <div style={{ marginTop: '10px', color: '#b91c1c' }}>
          错误: {folderImportProgress.error}
        </div>
      )}
      {(skippedDetails.length > 0 || failedDetails.length > 0) && (
        <div
          style={{
            marginTop: '14px',
            borderTop: '1px solid #e5e7eb',
            paddingTop: '12px',
          }}
        >
          {skippedDetails.length > 0 && (
            <div style={{ marginBottom: '12px' }}>
              <div style={{ fontWeight: 700, color: '#92400e' }}>
                跳过明细（最多显示 50 条）
              </div>
              <div
                style={{
                  marginTop: '6px',
                  maxHeight: '180px',
                  overflowY: 'auto',
                  border: '1px solid #fcd34d',
                  borderRadius: '8px',
                  background: '#fffbeb',
                }}
              >
                {skippedDetails.map((item, index) => (
                  <div
                    key={`skipped_${item.path}_${index}`}
                    style={{
                      padding: '8px 10px',
                      borderBottom:
                        index === skippedDetails.length - 1
                          ? 'none'
                          : '1px solid #fde68a',
                      color: '#78350f',
                      fontSize: '13px',
                    }}
                  >
                    <div>路径: {item.path}</div>
                    <div>原因: {formatImportReason(item.reason, item.detail)}</div>
                  </div>
                ))}
              </div>
            </div>
          )}
          {failedDetails.length > 0 && (
            <div>
              <div style={{ fontWeight: 700, color: '#991b1b' }}>
                失败明细（最多显示 50 条）
              </div>
              <div
                style={{
                  marginTop: '6px',
                  maxHeight: '220px',
                  overflowY: 'auto',
                  border: '1px solid #fca5a5',
                  borderRadius: '8px',
                  background: '#fef2f2',
                }}
              >
                {failedDetails.map((item, index) => (
                  <div
                    key={`failed_${item.path}_${index}`}
                    style={{
                      padding: '8px 10px',
                      borderBottom:
                        index === failedDetails.length - 1
                          ? 'none'
                          : '1px solid #fecaca',
                      color: '#7f1d1d',
                      fontSize: '13px',
                    }}
                  >
                    <div>路径: {item.path}</div>
                    <div>原因: {formatImportReason(item.reason, item.detail)}</div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
