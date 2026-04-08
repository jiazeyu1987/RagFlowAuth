import React from 'react';

import { BUTTON_STYLES, CARD_STYLE, formatFileSize, formatTime } from '../utils';

export default function NasBrowserItemsTable({
  isMobile,
  loading,
  items,
  loadPath,
  openImportDialog,
}) {
  return (
    <div style={{ ...CARD_STYLE, marginTop: '16px', overflow: 'hidden' }}>
      {loading ? (
        <div style={{ padding: '32px', color: '#6b7280' }}>正在加载 NAS 内容...</div>
      ) : items.length === 0 ? (
        <div style={{ padding: '32px', color: '#6b7280' }}>当前目录为空</div>
      ) : (
        <div style={{ width: '100%', overflowX: 'auto' }}>
          <table
            style={{
              width: '100%',
              minWidth: isMobile ? '760px' : '100%',
              borderCollapse: 'collapse',
            }}
          >
            <thead style={{ background: '#f8fafc' }}>
              <tr>
                <th
                  style={{
                    padding: '14px 16px',
                    textAlign: 'left',
                    borderBottom: '1px solid #e5e7eb',
                  }}
                >
                  名称
                </th>
                <th
                  style={{
                    padding: '14px 16px',
                    textAlign: 'left',
                    borderBottom: '1px solid #e5e7eb',
                    width: isMobile ? '96px' : '120px',
                  }}
                >
                  类型
                </th>
                <th
                  style={{
                    padding: '14px 16px',
                    textAlign: 'right',
                    borderBottom: '1px solid #e5e7eb',
                    width: isMobile ? '110px' : '140px',
                  }}
                >
                  大小
                </th>
                <th
                  style={{
                    padding: '14px 16px',
                    textAlign: 'left',
                    borderBottom: '1px solid #e5e7eb',
                    width: isMobile ? '180px' : '220px',
                  }}
                >
                  修改时间
                </th>
                <th
                  style={{
                    padding: '14px 16px',
                    textAlign: 'right',
                    borderBottom: '1px solid #e5e7eb',
                    width: isMobile ? '220px' : '280px',
                  }}
                >
                  操作
                </th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.path} style={{ borderBottom: '1px solid #f1f5f9' }}>
                  <td style={{ padding: '14px 16px', wordBreak: 'break-word' }}>
                    {item.is_dir ? (
                      <button
                        type="button"
                        onClick={() => loadPath(item.path)}
                        style={{
                          border: 'none',
                          background: 'transparent',
                          padding: 0,
                          cursor: 'pointer',
                          color: '#1d4ed8',
                          fontWeight: 700,
                          textAlign: 'left',
                        }}
                      >
                        {`[目录] ${item.name}`}
                      </button>
                    ) : (
                      <span style={{ color: '#111827', wordBreak: 'break-word' }}>
                        {`[文件] ${item.name}`}
                      </span>
                    )}
                  </td>
                  <td style={{ padding: '14px 16px', color: '#475569' }}>
                    {item.is_dir ? '文件夹' : '文件'}
                  </td>
                  <td
                    style={{
                      padding: '14px 16px',
                      textAlign: 'right',
                      color: '#475569',
                    }}
                  >
                    {item.is_dir ? '-' : formatFileSize(item.size)}
                  </td>
                  <td
                    style={{
                      padding: '14px 16px',
                      color: '#475569',
                      whiteSpace: 'nowrap',
                    }}
                  >
                    {formatTime(item.modified_at)}
                  </td>
                  <td
                    style={{
                      padding: '14px 16px',
                      textAlign: isMobile ? 'left' : 'right',
                    }}
                  >
                    <div
                      style={{
                        display: 'flex',
                        justifyContent: isMobile ? 'flex-start' : 'flex-end',
                        flexWrap: 'wrap',
                        gap: '8px',
                      }}
                    >
                      <button
                        type="button"
                        onClick={() => openImportDialog(item)}
                        data-testid={`nas-import-btn-${String(
                          item.path || item.name || 'item'
                        ).replace(/[^a-zA-Z0-9_-]/g, '_')}`}
                        style={{
                          ...(item.is_dir
                            ? BUTTON_STYLES.primary
                            : BUTTON_STYLES.success),
                          maxWidth: '100%',
                        }}
                      >
                        {item.is_dir
                          ? '上传文件夹到知识库'
                          : '上传文件到知识库'}
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
