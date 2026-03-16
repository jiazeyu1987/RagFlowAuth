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
    <div data-testid="agents-dataset-sidebar" className="agents-med-sidebar">
      <div className="medui-surface medui-card-pad medui-scroll" style={{ height: '100%' }}>
        <div className="medui-header-row" style={{ marginBottom: 12 }}>
          <div className="medui-title">检索知识库</div>
          <span className="medui-pill">已选 {selectedSet.size}</span>
        </div>

        <div style={{ marginBottom: 12, display: 'flex', gap: 8 }}>
          <button type="button" onClick={onSelectAll} className="medui-btn medui-btn--primary" style={{ flex: 1 }}>
            全选
          </button>
          <button type="button" onClick={onClearSelection} className="medui-btn medui-btn--neutral" style={{ flex: 1 }}>
            清空
          </button>
        </div>

        {!datasets?.length ? (
          <div className="medui-empty">暂无可用知识库。</div>
        ) : (
          <div className="chat-med-list">
            {datasets.map((dataset) => {
              const selected = selectedSet.has(dataset.id);
              return (
                <div
                  key={dataset.id}
                  data-testid={`agents-dataset-item-${String(dataset.id)}`}
                  onClick={() => onToggleDataset && onToggleDataset(dataset.id)}
                  className={`chat-med-item ${selected ? 'is-active' : ''}`}
                  role="button"
                  tabIndex={0}
                >
                  <div style={{ fontWeight: 700, marginBottom: 4 }}>{dataset.name || dataset.id}</div>
                  {dataset.description ? (
                    <div style={{ fontSize: '0.8rem', color: selected ? '#18486f' : '#5b738a' }}>{dataset.description}</div>
                  ) : null}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
