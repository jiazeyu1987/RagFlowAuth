import React from 'react';

import { TEXT } from '../constants';

const getQuickDatasetTestId = (dataset) =>
  `browser-quick-dataset-${String(dataset.id || dataset.name).replace(/[^a-zA-Z0-9_-]/g, '_')}`;

export default function DocumentBrowserQuickDatasets({
  isMobile,
  quickDatasets,
  onOpenQuickDataset,
}) {
  return (
    <div style={{ marginBottom: 24 }}>
      <div
        style={{
          background: '#fff',
          border: '1px solid #e5e7eb',
          borderRadius: 12,
          padding: isMobile ? 14 : 18,
        }}
      >
        <div
          data-testid="browser-quick-datasets"
          style={{
            display: 'grid',
            gridTemplateColumns: isMobile
              ? 'repeat(2, minmax(0, 1fr))'
              : 'repeat(5, minmax(0, 1fr))',
            gap: 12,
          }}
        >
          {quickDatasets.map((dataset) => (
            <button
              key={dataset.id || dataset.name}
              type="button"
              onClick={() => onOpenQuickDataset(dataset)}
              data-testid={getQuickDatasetTestId(dataset)}
              style={{
                border: '1px solid #dbeafe',
                background: 'linear-gradient(180deg, #eff6ff 0%, #ffffff 100%)',
                borderRadius: 12,
                padding: '12px 14px',
                textAlign: 'left',
                cursor: 'pointer',
                minHeight: 84,
              }}
            >
              <div
                style={{
                  fontWeight: 700,
                  color: '#1f2937',
                  marginBottom: 6,
                  wordBreak: 'break-all',
                }}
              >
                {dataset.name}
              </div>
              <div
                style={{
                  fontSize: '0.8rem',
                  color: '#6b7280',
                  marginBottom: 8,
                  wordBreak: 'break-all',
                }}
              >
                {dataset.node_path && dataset.node_path !== '/'
                  ? `${TEXT.root} > ${dataset.node_path.split('/').filter(Boolean).join(' > ')}`
                  : TEXT.root}
              </div>
              <div style={{ fontSize: '0.78rem', color: '#2563eb', fontWeight: 700 }}>
                打开知识库
              </div>
            </button>
          ))}
          {quickDatasets.length === 0 ? (
            <div
              style={{
                gridColumn: '1 / -1',
                padding: '20px 0',
                textAlign: 'center',
                color: '#6b7280',
              }}
            >
              {TEXT.shortcutEmpty}
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}
