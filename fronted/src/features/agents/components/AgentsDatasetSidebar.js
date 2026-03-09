import React, { useMemo } from 'react';

export default function AgentsDatasetSidebar({
  datasets,
  selectedDatasetIds,
  onToggleDataset,
  onSelectAll,
  onClearSelection,
}) {
  const selectedSet = useMemo(() => new Set(selectedDatasetIds || []), [selectedDatasetIds]);

  return (
    <div data-testid="agents-dataset-sidebar" style={{ width: '280px', display: 'flex', flexDirection: 'column' }}>
      <div
        style={{
          backgroundColor: 'white',
          borderRadius: '8px',
          padding: '16px',
          boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
          height: '100%',
          overflowY: 'auto',
        }}
      >
        <h3 style={{ margin: '0 0 12px 0', fontSize: '1rem' }}>知识库</h3>

        <div style={{ marginBottom: '12px', display: 'flex', gap: '8px' }}>
          <button
            type="button"
            onClick={onSelectAll}
            style={{
              flex: 1,
              padding: '6px',
              fontSize: '0.75rem',
              backgroundColor: '#3b82f6',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
            }}
          >
            全选
          </button>
          <button
            type="button"
            onClick={onClearSelection}
            style={{
              flex: 1,
              padding: '6px',
              fontSize: '0.75rem',
              backgroundColor: '#9ca3af',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
            }}
          >
            清空
          </button>
        </div>

        {!datasets?.length ? (
          <div style={{ color: '#6b7280', textAlign: 'center', padding: '20px' }}>暂无可用知识库</div>
        ) : (
          datasets.map((dataset) => {
            const selected = selectedSet.has(dataset.id);
            return (
              <div
                key={dataset.id}
                data-testid={`agents-dataset-item-${String(dataset.id)}`}
                onClick={() => onToggleDataset && onToggleDataset(dataset.id)}
                style={{
                  padding: '10px',
                  marginBottom: '8px',
                  borderRadius: '4px',
                  cursor: 'pointer',
                  backgroundColor: selected ? '#3b82f6' : '#f3f4f6',
                  color: selected ? 'white' : '#1f2937',
                  border: selected ? '2px solid #2563eb' : '1px solid #e5e7eb',
                  fontSize: '0.875rem',
                }}
              >
                <div style={{ fontWeight: 'bold', marginBottom: '4px' }}>{dataset.name || dataset.id}</div>
                {dataset.description ? (
                  <div
                    style={{
                      fontSize: '0.75rem',
                      color: selected ? 'rgba(255,255,255,0.8)' : '#6b7280',
                    }}
                  >
                    {dataset.description}
                  </div>
                ) : null}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
