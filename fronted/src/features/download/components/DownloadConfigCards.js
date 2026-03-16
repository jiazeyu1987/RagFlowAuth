import React from 'react';

const defaultSectionTitleStyle = {
  margin: '0 0 8px 0',
  fontSize: '1.03rem',
  fontWeight: 900,
  color: '#111827',
};

const defaultLabelStyle = {
  display: 'block',
  marginBottom: '6px',
  color: '#374151',
  fontWeight: 700,
  fontSize: '0.9rem',
};

const defaultTagStyle = {
  display: 'inline-flex',
  alignItems: 'center',
  padding: '4px 10px',
  borderRadius: '999px',
  border: '1px solid #bbf7d0',
  background: '#f0fdf4',
  color: '#166534',
  fontSize: '0.85rem',
  fontWeight: 700,
};

export function DownloadKeywordConfigCard({
  boxStyle,
  title = '关键词设置',
  keywordLabel = '关键词',
  keywordText = '',
  onKeywordChange,
  placeholder = '',
  rows = 6,
  useAnd = true,
  onUseAndChange,
  useAndId = 'download-use-and',
  useAndLabel = '使用“且”关系',
  parsedTitle = '解析后的关键词',
  parsedKeywords = [],
  emptyParsedText = '暂无',
  titleStyle,
  labelStyle,
  tagStyle,
}) {
  return (
    <section style={boxStyle}>
      <h2 style={{ ...defaultSectionTitleStyle, ...(titleStyle || {}) }}>{title}</h2>
      <label style={{ ...defaultLabelStyle, ...(labelStyle || {}) }}>{keywordLabel}</label>
      <textarea
        value={keywordText}
        onChange={(e) => onKeywordChange && onKeywordChange(e.target.value)}
        rows={rows}
        placeholder={placeholder}
        style={{
          width: '100%',
          resize: 'vertical',
          borderRadius: '10px',
          border: '1px solid #d1d5db',
          padding: '10px 12px',
          outline: 'none',
          lineHeight: 1.55,
          fontSize: '0.92rem',
          boxSizing: 'border-box',
        }}
      />
      <div style={{ marginTop: '10px', display: 'flex', alignItems: 'center', gap: '8px' }}>
        <input id={useAndId} type="checkbox" checked={Boolean(useAnd)} onChange={(e) => onUseAndChange && onUseAndChange(Boolean(e.target.checked))} />
        <label htmlFor={useAndId} style={{ color: '#111827', fontWeight: 700 }}>
          {useAndLabel}
        </label>
      </div>
      <div style={{ marginTop: '10px' }}>
        <div style={{ color: '#6b7280', fontSize: '0.85rem', marginBottom: '6px' }}>{parsedTitle}</div>
        {Array.isArray(parsedKeywords) && parsedKeywords.length ? (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
            {parsedKeywords.map((kw) => (
              <span key={kw} style={{ ...defaultTagStyle, ...(tagStyle || {}) }}>
                {kw}
              </span>
            ))}
          </div>
        ) : (
          <div style={{ color: '#9ca3af', fontSize: '0.85rem' }}>{emptyParsedText}</div>
        )}
      </div>
    </section>
  );
}

export function DownloadSourceConfigCard({
  boxStyle,
  title = '来源设置',
  sourceLabelMap = {},
  sources = {},
  onUpdateSource,
  clampLimit,
  autoAnalyze = false,
  onAutoAnalyzeChange,
  onRunDownload,
  loading = false,
  autoAnalyzeLabel = '自动分析',
  runText = '开始下载',
  runLoadingText = '下载中...',
  limitLabel = '数量上限',
  titleStyle,
  children,
}) {
  return (
    <section style={boxStyle}>
      <h2 style={{ ...defaultSectionTitleStyle, ...(titleStyle || {}) }}>{title}</h2>
      <div style={{ display: 'grid', gap: '8px' }}>
        {Object.keys(sourceLabelMap).map((key) => {
          const cfg = sources[key] || { enabled: false, limit: 10 };
          return (
            <div
              key={key}
              style={{
                border: '1px solid #e5e7eb',
                borderRadius: '10px',
                padding: '10px',
                display: 'grid',
                gridTemplateColumns: '1fr auto',
                alignItems: 'center',
                gap: '10px',
              }}
            >
              <label style={{ display: 'flex', alignItems: 'center', gap: '8px', fontWeight: 700, color: '#111827' }}>
                <input type="checkbox" checked={Boolean(cfg.enabled)} onChange={(e) => onUpdateSource && onUpdateSource(key, { enabled: Boolean(e.target.checked) })} />
                {sourceLabelMap[key]}
              </label>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span style={{ color: '#6b7280', fontSize: '0.85rem' }}>{limitLabel}</span>
                <input
                  type="number"
                  min={1}
                  max={1000}
                  value={cfg.limit}
                  onChange={(e) => onUpdateSource && onUpdateSource(key, { limit: clampLimit ? clampLimit(e.target.value) : Number(e.target.value) })}
                  style={{ width: '90px', border: '1px solid #d1d5db', borderRadius: '8px', padding: '6px 8px' }}
                />
              </div>
            </div>
          );
        })}
      </div>

      <div style={{ marginTop: '12px', display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
        <label
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '6px',
            padding: '8px 10px',
            border: '1px solid #e5e7eb',
            borderRadius: '10px',
            color: '#111827',
            fontWeight: 700,
            background: '#fff',
          }}
        >
          <input type="checkbox" checked={Boolean(autoAnalyze)} onChange={(e) => onAutoAnalyzeChange && onAutoAnalyzeChange(Boolean(e.target.checked))} />
          {autoAnalyzeLabel}
        </label>
        <button
          type="button"
          onClick={onRunDownload}
          disabled={Boolean(loading)}
          style={{
            padding: '10px 14px',
            borderRadius: '10px',
            border: '1px solid #2563eb',
            background: loading ? '#93c5fd' : '#2563eb',
            color: '#fff',
            cursor: loading ? 'not-allowed' : 'pointer',
            fontWeight: 800,
          }}
        >
          {loading ? runLoadingText : runText}
        </button>
      </div>

      {children}
    </section>
  );
}
