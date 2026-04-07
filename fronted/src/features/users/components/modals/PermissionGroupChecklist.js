import React from 'react';

const GROUP_COUNT_SUFFIX = '\u4e2a\u6743\u9650\u7ec4';

export default function PermissionGroupChecklist({
  label,
  hint,
  groups,
  loading = false,
  error = null,
  selectedGroupIds,
  onToggleGroup,
  testIdPrefix,
  emptyText,
  selectedText,
  loadingTestId,
  errorTestId,
  marginBottom = 16,
  maxHeight = '260px',
  panelBorderRadius = '8px',
  itemAlign = 'flex-start',
  emptyPadding = '8px 0',
}) {
  const availableGroups = Array.isArray(groups) ? groups : [];
  const checkedGroupIds = Array.isArray(selectedGroupIds) ? selectedGroupIds : [];

  return (
    <div style={{ marginBottom }}>
      <label style={{ display: 'block', marginBottom: '8px', fontWeight: '500' }}>{label}</label>
      {hint ? <div style={{ marginBottom: '8px', color: '#6b7280', fontSize: '0.85rem' }}>{hint}</div> : null}
      <div
        style={{
          border: '1px solid #d1d5db',
          borderRadius: panelBorderRadius,
          padding: '12px',
          backgroundColor: '#f9fafb',
          maxHeight,
          overflowY: 'auto',
        }}
      >
        {availableGroups.length === 0 && loading ? (
          <div
            style={{ color: '#6b7280', textAlign: 'center', padding: emptyPadding }}
            data-testid={loadingTestId}
          >
            {'\u52a0\u8f7d\u4e2d...'}
          </div>
        ) : availableGroups.length === 0 && error ? (
          <div
            style={{ color: '#ef4444', textAlign: 'center', padding: emptyPadding }}
            data-testid={errorTestId}
          >
            {error}
          </div>
        ) : availableGroups.length === 0 ? (
          <div style={{ color: '#6b7280', textAlign: 'center', padding: emptyPadding }}>{emptyText}</div>
        ) : (
          availableGroups.map((group) => (
            <label
              key={group.group_id}
              style={{ display: 'flex', alignItems: itemAlign, gap: 8, padding: '8px 0', cursor: 'pointer' }}
            >
              <input
                type="checkbox"
                data-testid={`${testIdPrefix}-${group.group_id}`}
                checked={checkedGroupIds.includes(group.group_id)}
                onChange={(event) => onToggleGroup?.(group.group_id, event.target.checked)}
              />
              <div>
                <div style={{ fontWeight: 500, color: '#111827' }}>{group.group_name}</div>
                {group.description ? (
                  <div style={{ fontSize: '0.85rem', color: '#6b7280' }}>{group.description}</div>
                ) : null}
              </div>
            </label>
          ))
        )}
      </div>
      {checkedGroupIds.length > 0 ? (
        <div style={{ marginTop: '8px', color: '#6b7280', fontSize: '0.85rem' }}>
          {selectedText} {checkedGroupIds.length} {GROUP_COUNT_SUFFIX}
        </div>
      ) : null}
    </div>
  );
}
