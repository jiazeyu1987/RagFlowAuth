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
    <div data-testid="users-group-modal" className="medui-modal-backdrop">
      <div className="medui-modal users-med-modal">
        <div className="medui-modal__head">
          <div className="medui-modal__title">{`分配权限组 - ${editingGroupUser.username}`}</div>
        </div>
        <div className="medui-modal__body">
          <div className="users-med-field">
            <label>选择权限组（可多选）</label>
            <div className="users-med-group-list" style={{ maxHeight: 300 }}>
              {availableGroups.length === 0 ? <div className="medui-empty" style={{ padding: '12px 0' }}>暂无可用权限组</div> : availableGroups.map((group) => <label key={group.group_id} style={{ display: 'flex', alignItems: 'center', padding: '8px 0', cursor: 'pointer' }}><input type="checkbox" checked={selectedGroupIds?.includes(group.group_id) || false} data-testid={`users-group-checkbox-${group.group_id}`} onChange={(e) => onToggleGroup(group.group_id, e.target.checked)} style={{ marginRight: 8 }} /><div><div style={{ fontWeight: 700, color: '#173d60' }}>{group.group_name}</div>{group.description && <div className="users-med-note">{group.description}</div>}</div></label>)}
            </div>
            {selectedGroupIds && selectedGroupIds.length > 0 && <div className="users-med-note" style={{ marginTop: 8 }}>{`已选择 ${selectedGroupIds.length} 个权限组`}</div>}
          </div>
        </div>
        <div className="medui-modal__foot">
          <button type="button" onClick={onCancel} data-testid="users-group-cancel" className="medui-btn medui-btn--neutral">取消</button>
          <button type="button" onClick={onSave} data-testid="users-group-save" className="medui-btn medui-btn--primary">保存</button>
        </div>
      </div>
    </div>
  );
}
