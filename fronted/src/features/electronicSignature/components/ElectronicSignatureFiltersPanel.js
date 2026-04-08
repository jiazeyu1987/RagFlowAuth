import React from 'react';

import {
  ACTION_OPTIONS,
  RECORD_TYPE_OPTIONS,
  TEXT,
  buttonStyle,
  cardStyle,
  inputStyle,
  primaryButtonStyle,
} from '../electronicSignatureManagementView';

export default function ElectronicSignatureFiltersPanel({
  filters,
  setFilterValue,
  handleSearch,
  handleReset,
  total,
}) {
  return (
    <div style={cardStyle}>
      <h3 style={{ marginTop: 0 }}>{TEXT.filters}</h3>
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
          gap: '12px',
        }}
      >
        <label style={{ display: 'grid', gap: '6px' }}>
          <span>{TEXT.recordType}</span>
          <select
            value={filters.record_type}
            onChange={(event) => setFilterValue('record_type', event.target.value)}
            style={inputStyle}
          >
            {RECORD_TYPE_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
        <label style={{ display: 'grid', gap: '6px' }}>
          <span>{TEXT.action}</span>
          <select
            value={filters.action}
            onChange={(event) => setFilterValue('action', event.target.value)}
            style={inputStyle}
          >
            {ACTION_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
        <label style={{ display: 'grid', gap: '6px' }}>
          <span>{TEXT.signer}</span>
          <input
            value={filters.signed_by}
            onChange={(event) => setFilterValue('signed_by', event.target.value)}
            style={inputStyle}
          />
        </label>
        <label style={{ display: 'grid', gap: '6px' }}>
          <span>{`${TEXT.signedAt}起`}</span>
          <input
            type="datetime-local"
            value={filters.signed_at_from}
            onChange={(event) => setFilterValue('signed_at_from', event.target.value)}
            style={inputStyle}
          />
        </label>
        <label style={{ display: 'grid', gap: '6px' }}>
          <span>{`${TEXT.signedAt}止`}</span>
          <input
            type="datetime-local"
            value={filters.signed_at_to}
            onChange={(event) => setFilterValue('signed_at_to', event.target.value)}
            style={inputStyle}
          />
        </label>
      </div>
      <div style={{ display: 'flex', gap: '8px', marginTop: '12px', flexWrap: 'wrap' }}>
        <button
          type="button"
          data-testid="electronic-signature-search"
          onClick={handleSearch}
          style={primaryButtonStyle}
        >
          {TEXT.search}
        </button>
        <button
          type="button"
          data-testid="electronic-signature-reset"
          onClick={handleReset}
          style={buttonStyle}
        >
          {TEXT.reset}
        </button>
        <div style={{ marginLeft: 'auto', color: '#6b7280', alignSelf: 'center' }}>
          {TEXT.total}: {total}
        </div>
      </div>
    </div>
  );
}
