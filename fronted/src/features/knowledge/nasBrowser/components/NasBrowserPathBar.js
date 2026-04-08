import React from 'react';

import { BUTTON_STYLES, CARD_STYLE } from '../utils';

export default function NasBrowserPathBar({
  isMobile,
  breadcrumbs,
  currentPath,
  parentPath,
  loadPath,
}) {
  return (
    <div
      style={{
        ...CARD_STYLE,
        marginTop: '16px',
        padding: isMobile ? '14px' : '14px 16px',
      }}
    >
      <div style={{ display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap' }}>
        {breadcrumbs.map((segment, index) => (
          <React.Fragment key={segment.path || 'root'}>
            {index > 0 && <span style={{ color: '#9ca3af' }}>/</span>}
            <button
              type="button"
              onClick={() => loadPath(segment.path)}
              style={{
                border: 'none',
                background: 'transparent',
                padding: 0,
                color: segment.path === currentPath ? '#111827' : '#2563eb',
                cursor: 'pointer',
                fontWeight: segment.path === currentPath ? 800 : 600,
              }}
            >
              {segment.label}
            </button>
          </React.Fragment>
        ))}
      </div>
      <div
        style={{
          marginTop: '12px',
          display: 'flex',
          flexDirection: isMobile ? 'column' : 'row',
          gap: '8px',
        }}
      >
        <button
          type="button"
          onClick={() => loadPath(parentPath || '')}
          disabled={parentPath === null}
          style={{
            ...BUTTON_STYLES.neutral,
            background: parentPath === null ? '#f3f4f6' : '#fff',
            color: parentPath === null ? '#9ca3af' : '#111827',
            cursor: parentPath === null ? 'not-allowed' : 'pointer',
            width: isMobile ? '100%' : 'auto',
          }}
        >
          上一级
        </button>
      </div>
    </div>
  );
}
