import React from 'react';

export default function PaperSourceSummaryPanel({
  sourceStats,
  sourceErrors,
  error,
  info,
  sourceLabelMap,
}) {
  return (
    <>
      {Object.keys(sourceStats || {}).length > 0 ? (
        <div style={{ marginTop: '8px', color: '#6b7280', fontSize: '0.82rem' }}>
          {Object.entries(sourceStats).map(([key, stat]) => (
            <div key={key}>
              <div>
                {sourceLabelMap[key] || key}：候选 {stat?.candidates || 0}，已下载 {stat?.downloaded || 0}，已复用 {stat?.reused || 0}，失败 {stat?.failed || 0}
              </div>
              {stat?.query ? (
                <div style={{ marginTop: '2px' }}>检索词：{stat.query}</div>
              ) : null}
            </div>
          ))}
        </div>
      ) : null}

      {Object.keys(sourceErrors || {}).length > 0 ? (
        <div
          style={{
            marginTop: '8px',
            color: '#92400e',
            fontSize: '0.86rem',
            borderTop: '1px dashed #e5e7eb',
            paddingTop: '8px',
          }}
        >
          <div style={{ fontWeight: 800, marginBottom: '4px' }}>日志</div>
          {Object.entries(sourceErrors).map(([key, value]) => (
            <div key={key}>
              {sourceLabelMap[key] || key}: {String(value || '-')}
            </div>
          ))}
        </div>
      ) : null}

      {error ? (
        <div style={{ marginTop: '10px', color: '#b91c1c', fontSize: '0.9rem' }}>{error}</div>
      ) : null}
      {info ? (
        <div style={{ marginTop: '10px', color: '#065f46', fontSize: '0.9rem' }}>{info}</div>
      ) : null}
    </>
  );
}
