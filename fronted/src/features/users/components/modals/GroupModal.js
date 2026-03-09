import React from 'react';

export default function GroupModal({
  open,
  editingGroupUser,
  availableGroups,
  selectedGroupIds,
  onToggleGroup,
  onCancel,
  onSave,
}) {
  if (!open || !editingGroupUser) return null;

  return (
    <div
      data-testid="users-group-modal"
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.5)',
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        zIndex: 1000,
      }}
    >
      <div
        style={{
          backgroundColor: 'white',
          padding: '32px',
          borderRadius: '8px',
          width: '100%',
          maxWidth: '500px',
        }}
      >
        <h3 style={{ margin: '0 0 24px 0' }}>
          {'分配权限组 - '} {editingGroupUser.username}
        </h3>
        <div style={{ marginBottom: '24px' }}>
          <label style={{ display: 'block', marginBottom: '8px', fontWeight: '500' }}>{'选择权限组(可多选)'}</label>
          <div
            style={{
              border: '1px solid #d1d5db',
              borderRadius: '4px',
              padding: '12px',
              maxHeight: '300px',
              overflowY: 'auto',
              backgroundColor: '#f9fafb',
            }}
          >
            {availableGroups.length === 0 ? (
              <div style={{ color: '#6b7280', textAlign: 'center', padding: '8px' }}>{'暂无可用权限组'}</div>
            ) : (
              availableGroups.map((group) => (
                <label
                  key={group.group_id}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    padding: '8px 0',
                    cursor: 'pointer',
                  }}
                >
                  <input
                    type="checkbox"
                    checked={selectedGroupIds?.includes(group.group_id) || false}
                    data-testid={`users-group-checkbox-${group.group_id}`}
                    onChange={(e) => onToggleGroup(group.group_id, e.target.checked)}
                    style={{ marginRight: '8px' }}
                  />
                  <div>
                    <div style={{ fontWeight: '500' }}>{group.group_name}</div>
                    {group.description && <div style={{ fontSize: '0.85rem', color: '#6b7280' }}>{group.description}</div>}
                  </div>
                </label>
              ))
            )}
          </div>
          {selectedGroupIds && selectedGroupIds.length > 0 && (
            <div style={{ marginTop: '8px', fontSize: '0.85rem', color: '#6b7280' }}>
              {'已选择'} {selectedGroupIds.length} {'个权限组'}
            </div>
          )}
        </div>
        <div style={{ display: 'flex', gap: '12px' }}>
          <button
            type="button"
            onClick={onCancel}
            data-testid="users-group-cancel"
            style={{
              flex: 1,
              padding: '10px',
              backgroundColor: '#6b7280',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
            }}
          >
            {'取消'}
          </button>
          <button
            type="button"
            onClick={onSave}
            data-testid="users-group-save"
            style={{
              flex: 1,
              padding: '10px',
              backgroundColor: '#8b5cf6',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
            }}
          >
            {'保存'}
          </button>
        </div>
      </div>
    </div>
  );
}
