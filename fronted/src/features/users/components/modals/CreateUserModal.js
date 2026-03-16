import React from 'react';

export default function CreateUserModal({
  open,
  newUser,
  availableGroups,
  companies,
  departments,
  onSubmit,
  onCancel,
  onFieldChange,
  onToggleGroup,
}) {
  if (!open) return null;

  return (
    <div className="medui-modal-backdrop">
      <div className="medui-modal users-med-modal" style={{ maxHeight: 'calc(100vh - 60px)', display: 'flex', flexDirection: 'column' }}>
        <div className="medui-modal__head">
          <div className="medui-modal__title">新建用户</div>
        </div>
        <form onSubmit={onSubmit} data-testid="users-create-form" style={{ display: 'flex', flexDirection: 'column', minHeight: 0 }}>
          <div className="medui-modal__body" style={{ overflowY: 'auto', display: 'grid', gap: 12 }}>
            <div className="users-med-field">
              <label>用户名</label>
              <input type="text" required value={newUser.username} onChange={(e) => onFieldChange('username', e.target.value)} data-testid="users-create-username" className="medui-input" />
            </div>
            <div className="users-med-field">
              <label>密码</label>
              <input type="password" required value={newUser.password} onChange={(e) => onFieldChange('password', e.target.value)} data-testid="users-create-password" className="medui-input" />
            </div>
            <div className="users-med-field">
              <label>姓名</label>
              <input type="text" value={newUser.email} onChange={(e) => onFieldChange('email', e.target.value)} data-testid="users-create-email" className="medui-input" />
            </div>
            <div className="users-med-field">
              <label>公司</label>
              <select required value={newUser.company_id} onChange={(e) => onFieldChange('company_id', e.target.value)} data-testid="users-create-company" className="medui-select"><option value="" disabled>请选择公司</option>{companies.map((c) => <option key={c.id} value={String(c.id)}>{c.name}</option>)}</select>
            </div>
            <div className="users-med-field">
              <label>部门</label>
              <select required value={newUser.department_id} onChange={(e) => onFieldChange('department_id', e.target.value)} data-testid="users-create-department" className="medui-select"><option value="" disabled>请选择部门</option>{departments.map((d) => <option key={d.id} value={String(d.id)}>{d.name}</option>)}</select>
            </div>
            <div className="users-med-field">
              <label>可登录会话数</label>
              <input type="number" min={1} max={1000} required value={newUser.max_login_sessions} onChange={(e) => onFieldChange('max_login_sessions', e.target.value)} data-testid="users-create-max-login-sessions" className="medui-input" />
            </div>
            <div className="users-med-field">
              <label>空闲超时（分钟）</label>
              <input type="number" min={1} max={43200} required value={newUser.idle_timeout_minutes} onChange={(e) => onFieldChange('idle_timeout_minutes', e.target.value)} data-testid="users-create-idle-timeout" className="medui-input" />
            </div>
            <div className="users-med-field">
              <label>权限组（可多选）</label>
              <div className="users-med-group-list">
                {availableGroups.length === 0 ? <div className="medui-empty" style={{ padding: '12px 0' }}>暂无可用权限组</div> : availableGroups.map((group) => <label key={group.group_id} style={{ display: 'flex', alignItems: 'center', padding: '7px 0', cursor: 'pointer' }}><input type="checkbox" checked={newUser.group_ids?.includes(group.group_id) || false} onChange={(e) => onToggleGroup(group.group_id, e.target.checked)} data-testid={`users-create-group-${group.group_id}`} style={{ marginRight: 8 }} /><div><div style={{ fontWeight: 700, color: '#173d60' }}>{group.group_name}</div>{group.description ? <div className="users-med-note">{group.description}</div> : null}</div></label>)}
              </div>
              {newUser.group_ids && newUser.group_ids.length > 0 && <div className="users-med-note" style={{ marginTop: 8 }}>{`已选择 ${newUser.group_ids.length} 个权限组`}</div>}
            </div>
          </div>
          <div className="medui-modal__foot">
            <button type="submit" data-testid="users-create-submit" className="medui-btn medui-btn--primary">创建</button>
            <button type="button" onClick={onCancel} data-testid="users-create-cancel" className="medui-btn medui-btn--neutral">取消</button>
          </div>
        </form>
      </div>
    </div>
  );
}
