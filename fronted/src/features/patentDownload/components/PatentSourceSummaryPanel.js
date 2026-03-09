import React from 'react';

export default function PatentSourceSummaryPanel({
  sourceStats,
  error,
  info,
  frontendLogs,
  sourceLabelMap,
}) {
  return (
    <>
      {Object.keys(sourceStats || {}).length > 0 ? (
        <div style={{ marginTop: '8px', color: '#6b7280', fontSize: '0.82rem' }}>
          {Object.entries(sourceStats).map(([key, stat]) => (
            <div key={key}>
              <div>
                {sourceLabelMap[key] || key}: candidates {stat?.candidates || 0}, downloaded{' '}
                {stat?.downloaded || 0}, reused {stat?.reused || 0}, failed {stat?.failed || 0}
              </div>
              {stat?.query ? (
                <div style={{ marginTop: '2px' }}>
                  {key === 'uspto' ? 'USPTO query' : 'Search query'}: {stat.query}
                </div>
              ) : null}
            </div>
          ))}
        </div>
      ) : null}

      {error ? <div style={{ marginTop: '10px', color: '#b91c1c', fontSize: '0.9rem' }}>{error}</div> : null}
      {info ? <div style={{ marginTop: '10px', color: '#065f46', fontSize: '0.9rem' }}>{info}</div> : null}

      {frontendLogs?.length ? (
        <div
          style={{
            marginTop: '10px',
            color: '#92400e',
            fontSize: '0.86rem',
            borderTop: '1px dashed #e5e7eb',
            paddingTop: '8px',
          }}
        >
          <div style={{ fontWeight: 800, marginBottom: '4px' }}>Logs</div>
          {frontendLogs.map((line, index) => (
            <div key={`${index}-${line}`}>{line}</div>
          ))}
        </div>
      ) : null}
    </>
  );
}
