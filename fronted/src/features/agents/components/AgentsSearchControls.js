import React, { useCallback } from 'react';

export default function AgentsSearchControls({
  searchQuery,
  onSearchQueryChange,
  onSearch,
  loading,
  searchHistory,
  onHistorySearch,
  onClearHistory,
  onRemoveHistoryItem,
  similarityThreshold,
  onSimilarityThresholdChange,
  topK,
  onTopKChange,
  keyword,
  onKeywordChange,
  highlight,
  onHighlightChange,
  disableSearch,
}) {
  const handleKeyDown = useCallback(
    (event) => {
      if (event.key !== 'Enter') return;
      event.preventDefault();
      if (onSearch) onSearch();
    },
    [onSearch]
  );

  return (
    <div
      style={{
        padding: '16px',
        borderBottom: '1px solid #e5e7eb',
        backgroundColor: '#f9fafb',
      }}
    >
      <div style={{ marginBottom: '12px' }}>
        <input
          type="text"
          data-testid="agents-search-input"
          value={searchQuery}
          onChange={(event) => onSearchQueryChange && onSearchQueryChange(event.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="输入搜索关键词或问题..."
          disabled={loading}
          style={{
            width: '100%',
            padding: '10px 12px',
            border: '1px solid #d1d5db',
            borderRadius: '4px',
            fontSize: '0.875rem',
            boxSizing: 'border-box',
          }}
        />
      </div>

      <div style={{ marginBottom: '12px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '12px', marginBottom: '8px' }}>
          <span style={{ fontSize: '0.8rem', fontWeight: 600, color: '#4b5563' }}>最近搜索</span>
          <button
            type="button"
            onClick={onClearHistory}
            disabled={!searchHistory?.length}
            style={{
              border: 'none',
              background: 'transparent',
              color: !searchHistory?.length ? '#9ca3af' : '#2563eb',
              cursor: !searchHistory?.length ? 'not-allowed' : 'pointer',
              fontSize: '0.8rem',
              padding: 0,
            }}
          >
            清空
          </button>
        </div>

        {searchHistory?.length ? (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
            {searchHistory.map((item) => (
              <div
                key={item}
                style={{
                  borderRadius: '999px',
                  border: '1px solid #bfdbfe',
                  background: '#eff6ff',
                  display: 'inline-flex',
                  alignItems: 'center',
                  overflow: 'hidden',
                }}
              >
                <button
                  type="button"
                  onClick={() => onHistorySearch && onHistorySearch(item)}
                  style={{
                    padding: '6px 10px',
                    border: 'none',
                    background: 'transparent',
                    color: '#1d4ed8',
                    fontSize: '0.8rem',
                    cursor: 'pointer',
                  }}
                  title={`搜索: ${item}`}
                >
                  {item}
                </button>
                <button
                  type="button"
                  onClick={() => onRemoveHistoryItem && onRemoveHistoryItem(item)}
                  style={{
                    border: 'none',
                    borderLeft: '1px solid #bfdbfe',
                    background: 'transparent',
                    color: '#6b7280',
                    fontSize: '0.8rem',
                    cursor: 'pointer',
                    padding: '6px 8px',
                  }}
                  title={`删除历史: ${item}`}
                >
                  ×
                </button>
              </div>
            ))}
          </div>
        ) : (
          <div style={{ fontSize: '0.8rem', color: '#9ca3af' }}>暂无搜索历史</div>
        )}
      </div>

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))',
          gap: '12px',
          marginBottom: '12px',
        }}
      >
        <div>
          <label style={{ fontSize: '0.75rem', color: '#6b7280', display: 'block', marginBottom: '4px' }}>
            相似度阈值: {similarityThreshold}
          </label>
          <input
            type="range"
            min="0"
            max="1"
            step="0.05"
            value={similarityThreshold}
            onChange={(event) => onSimilarityThresholdChange && onSimilarityThresholdChange(parseFloat(event.target.value))}
            style={{ width: '100%' }}
          />
        </div>

        <div>
          <label style={{ fontSize: '0.75rem', color: '#6b7280', display: 'block', marginBottom: '4px' }}>
            Top-K: {topK}
          </label>
          <input
            type="number"
            min="1"
            max="1024"
            value={topK}
            onChange={(event) => onTopKChange && onTopKChange(parseInt(event.target.value, 10) || 30)}
            style={{
              width: '100%',
              padding: '6px',
              border: '1px solid #d1d5db',
              borderRadius: '4px',
              fontSize: '0.875rem',
            }}
          />
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <label style={{ display: 'flex', alignItems: 'center', fontSize: '0.875rem', cursor: 'pointer' }}>
            <input
              type="checkbox"
              checked={keyword}
              onChange={(event) => onKeywordChange && onKeywordChange(event.target.checked)}
              style={{ marginRight: '6px' }}
            />
            关键词匹配
          </label>

          <label style={{ display: 'flex', alignItems: 'center', fontSize: '0.875rem', cursor: 'pointer' }}>
            <input
              type="checkbox"
              checked={highlight}
              onChange={(event) => onHighlightChange && onHighlightChange(event.target.checked)}
              style={{ marginRight: '6px' }}
            />
            高亮匹配
          </label>
        </div>
      </div>

      <button
        type="button"
        data-testid="agents-search-button"
        onClick={onSearch}
        disabled={disableSearch}
        style={{
          width: '100%',
          padding: '10px',
          backgroundColor: disableSearch ? '#9ca3af' : '#3b82f6',
          color: 'white',
          border: 'none',
          borderRadius: '4px',
          cursor: disableSearch ? 'not-allowed' : 'pointer',
          fontSize: '0.875rem',
          fontWeight: 'bold',
        }}
      >
        {loading ? '搜索中...' : '搜索'}
      </button>
    </div>
  );
}
