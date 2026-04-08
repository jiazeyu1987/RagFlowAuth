import React from 'react';

import { BUTTON_STYLES } from '../utils';

export default function NasBrowserHeader({
  isMobile,
  currentPath,
  onBackToTools,
  loadPath,
}) {
  return (
    <div
      style={{
        display: 'flex',
        flexDirection: isMobile ? 'column' : 'row',
        justifyContent: 'space-between',
        alignItems: isMobile ? 'stretch' : 'center',
        gap: '12px',
      }}
    >
      <div>
        <h2 style={{ margin: 0, fontSize: '1.4rem', color: '#111827' }}>NAS 云盘</h2>
        <div style={{ marginTop: '6px', color: '#6b7280', fontSize: '0.95rem' }}>
          NAS: `172.30.30.4` / 共享目录: `it共享`
        </div>
      </div>
      <div
        style={{
          display: 'flex',
          flexDirection: isMobile ? 'column' : 'row',
          gap: '8px',
          width: isMobile ? '100%' : 'auto',
        }}
      >
        <button
          type="button"
          onClick={onBackToTools}
          style={{ ...BUTTON_STYLES.neutral, width: isMobile ? '100%' : 'auto' }}
        >
          返回实用工具
        </button>
        <button
          type="button"
          onClick={() => loadPath(currentPath)}
          style={{ ...BUTTON_STYLES.primary, width: isMobile ? '100%' : 'auto' }}
        >
          刷新
        </button>
      </div>
    </div>
  );
}
