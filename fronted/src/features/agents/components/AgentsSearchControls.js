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
    <div className="agents-med-control">
      <div style={{ marginBottom: 12 }}>
        <input
          type="text"
          data-testid="agents-search-input"
          value={searchQuery}
          onChange={(event) => onSearchQueryChange && onSearchQueryChange(event.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="输入检索关键词或问题"
          disabled={loading}
          className="medui-input"
        />
      </div>

      <div style={{ marginBottom: 12 }}>
        <div className="medui-header-row" style={{ marginBottom: 8 }}>
          <span className="medui-subtitle" style={{ fontWeight: 700 }}>
            最近检索
          </span>
          <button
            type="button"
            onClick={onClearHistory}
            disabled={!searchHistory?.length}
            className="medui-btn medui-btn--neutral"
            style={{ height: 30, padding: '0 10px', fontSize: '0.8rem' }}
          >
            清空
          </button>
        </div>

        {searchHistory?.length ? (
          <div className="agents-med-history">
            {searchHistory.map((item) => (
              <div key={item} className="agents-med-history-item">
                <button type="button" onClick={() => onHistorySearch && onHistorySearch(item)} title={`搜索: ${item}`}>
                  {item}
                </button>
                <button type="button" onClick={() => onRemoveHistoryItem && onRemoveHistoryItem(item)} title={`删除历史: ${item}`}>
                  删
                </button>
              </div>
            ))}
          </div>
        ) : (
          <div className="medui-muted" style={{ fontSize: '0.84rem' }}>
            暂无检索历史
          </div>
        )}
      </div>

      <div className="agents-med-filters" style={{ marginBottom: 12 }}>
        <div>
          <label className="medui-subtitle" style={{ display: 'block', marginBottom: 4 }}>
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
          <label className="medui-subtitle" style={{ display: 'block', marginBottom: 4 }}>
            Top-K: {topK}
          </label>
          <input
            type="number"
            min="1"
            max="1024"
            value={topK}
            onChange={(event) => onTopKChange && onTopKChange(parseInt(event.target.value, 10) || 30)}
            className="medui-input"
          />
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 18, flexWrap: 'wrap' }}>
          <label style={{ display: 'flex', alignItems: 'center', fontSize: '0.88rem', cursor: 'pointer' }}>
            <input
              type="checkbox"
              checked={keyword}
              onChange={(event) => onKeywordChange && onKeywordChange(event.target.checked)}
              style={{ marginRight: 6 }}
            />
            关键词匹配
          </label>

          <label style={{ display: 'flex', alignItems: 'center', fontSize: '0.88rem', cursor: 'pointer' }}>
            <input
              type="checkbox"
              checked={highlight}
              onChange={(event) => onHighlightChange && onHighlightChange(event.target.checked)}
              style={{ marginRight: 6 }}
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
        className="medui-btn medui-btn--primary"
        style={{ width: '100%', height: 40 }}
      >
        {loading ? '检索中...' : '开始检索'}
      </button>
    </div>
  );
}
