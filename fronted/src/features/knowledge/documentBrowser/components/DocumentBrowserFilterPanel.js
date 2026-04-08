import React from 'react';

import { TEXT } from '../constants';
import { toolbarButtonStyle } from '../styles';

export default function DocumentBrowserFilterPanel({
  isMobile,
  datasetFilterKeyword,
  recentDatasetKeywords,
  setDatasetFilterKeyword,
  commitKeyword,
}) {
  return (
    <div
      style={{
        background: '#fff',
        padding: isMobile ? 14 : 16,
        borderRadius: 8,
        border: '1px solid #e5e7eb',
        marginBottom: 16,
      }}
    >
      <div style={{ marginBottom: 6, color: '#6b7280', fontSize: '0.85rem' }}>{TEXT.filter}</div>
      <div
        style={{
          display: 'flex',
          gap: 12,
          alignItems: isMobile ? 'stretch' : 'center',
          flexDirection: isMobile ? 'column' : 'row',
        }}
      >
        <input
          value={datasetFilterKeyword}
          onChange={(event) => setDatasetFilterKeyword(event.target.value)}
          onBlur={() => commitKeyword(datasetFilterKeyword)}
          onKeyDown={(event) => {
            if (event.key === 'Enter') {
              commitKeyword(datasetFilterKeyword);
            }
          }}
          placeholder={TEXT.filterPlaceholder}
          data-testid="browser-dataset-filter"
          list="browser-dataset-filter-recent"
          style={{
            flex: 1,
            width: '100%',
            padding: '10px 12px',
            borderRadius: 6,
            border: '1px solid #d1d5db',
            boxSizing: 'border-box',
          }}
        />
        <button
          type="button"
          onClick={() => setDatasetFilterKeyword('')}
          data-testid="browser-dataset-filter-clear"
          style={{
            ...toolbarButtonStyle('neutral'),
            width: isMobile ? '100%' : 'auto',
          }}
        >
          {TEXT.clear}
        </button>
      </div>
      <datalist id="browser-dataset-filter-recent">
        {recentDatasetKeywords.map((value) => (
          <option key={value} value={value} />
        ))}
      </datalist>
      {recentDatasetKeywords.length ? (
        <div
          style={{
            marginTop: 10,
            display: 'flex',
            gap: 8,
            flexWrap: 'wrap',
            alignItems: 'center',
          }}
        >
          <div style={{ color: '#6b7280', fontSize: '0.85rem' }}>{TEXT.recent}</div>
          {recentDatasetKeywords.map((value) => (
            <button
              key={value}
              type="button"
              onClick={() => setDatasetFilterKeyword(value)}
              style={toolbarButtonStyle('neutral')}
            >
              {value}
            </button>
          ))}
        </div>
      ) : null}
    </div>
  );
}
