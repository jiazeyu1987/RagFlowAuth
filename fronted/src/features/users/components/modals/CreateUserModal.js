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
    <div
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
          maxWidth: '400px',
        }}
      >
        <h3 style={{ margin: '0 0 24px 0' }}>{'新建用户'}</h3>
        <form onSubmit={onSubmit} data-testid="users-create-form">
          <div style={{ marginBottom: '16px' }}>
            <label style={{ display: 'block', marginBottom: '8px', fontWeight: '500' }}>{'用户名'}</label>
            <input
              type="text"
              required
              value={newUser.username}
              onChange={(e) => onFieldChange('username', e.target.value)}
              data-testid="users-create-username"
              style={{
                width: '100%',
                padding: '8px',
                border: '1px solid #d1d5db',
                borderRadius: '4px',
                boxSizing: 'border-box',
              }}
            />
          </div>

          <div style={{ marginBottom: '16px' }}>
            <label style={{ display: 'block', marginBottom: '8px', fontWeight: '500' }}>{'密码'}</label>
            <input
              type="password"
              required
              value={newUser.password}
              onChange={(e) => onFieldChange('password', e.target.value)}
              data-testid="users-create-password"
              style={{
                width: '100%',
                padding: '8px',
                border: '1px solid #d1d5db',
                borderRadius: '4px',
                boxSizing: 'border-box',
              }}
            />
          </div>

          <div style={{ marginBottom: '16px' }}>
            <label style={{ display: 'block', marginBottom: '8px', fontWeight: '500' }}>{'姓名'}</label>
            <input
              type="text"
              value={newUser.email}
              onChange={(e) => onFieldChange('email', e.target.value)}
              data-testid="users-create-email"
              style={{
                width: '100%',
                padding: '8px',
                border: '1px solid #d1d5db',
                borderRadius: '4px',
                boxSizing: 'border-box',
              }}
            />
          </div>

          <div style={{ marginBottom: '16px' }}>
            <label style={{ display: 'block', marginBottom: '8px', fontWeight: '500' }}>{'公司'}</label>
            <select
              required
              value={newUser.company_id}
              onChange={(e) => onFieldChange('company_id', e.target.value)}
              data-testid="users-create-company"
              style={{
                width: '100%',
                padding: '8px',
                border: '1px solid #d1d5db',
                borderRadius: '4px',
                boxSizing: 'border-box',
                backgroundColor: 'white',
              }}
            >
              <option value="" disabled>
                {'请选择公司'}
              </option>
              {companies.map((c) => (
                <option key={c.id} value={String(c.id)}>
                  {c.name}
                </option>
              ))}
            </select>
          </div>

          <div style={{ marginBottom: '16px' }}>
            <label style={{ display: 'block', marginBottom: '8px', fontWeight: '500' }}>{'部门'}</label>
            <select
              required
              value={newUser.department_id}
              onChange={(e) => onFieldChange('department_id', e.target.value)}
              data-testid="users-create-department"
              style={{
                width: '100%',
                padding: '8px',
                border: '1px solid #d1d5db',
                borderRadius: '4px',
                boxSizing: 'border-box',
                backgroundColor: 'white',
              }}
            >
              <option value="" disabled>
                {'请选择部门'}
              </option>
              {departments.map((d) => (
                <option key={d.id} value={String(d.id)}>
                  {d.name}
                </option>
              ))}
            </select>
          </div>

          <div style={{ marginBottom: '16px' }}>
            <label style={{ display: 'block', marginBottom: '8px', fontWeight: '500' }}>{'可登录个数'}</label>
            <input
              type="number"
              min={1}
              max={1000}
              required
              value={newUser.max_login_sessions}
              onChange={(e) => onFieldChange('max_login_sessions', e.target.value)}
              data-testid="users-create-max-login-sessions"
              style={{
                width: '100%',
                padding: '8px',
                border: '1px solid #d1d5db',
                borderRadius: '4px',
                boxSizing: 'border-box',
              }}
            />
          </div>

          <div style={{ marginBottom: '16px' }}>
            <label style={{ display: 'block', marginBottom: '8px', fontWeight: '500' }}>{'闲置超时(分钟)'}</label>
            <input
              type="number"
              min={1}
              max={43200}
              required
              value={newUser.idle_timeout_minutes}
              onChange={(e) => onFieldChange('idle_timeout_minutes', e.target.value)}
              data-testid="users-create-idle-timeout"
              style={{
                width: '100%',
                padding: '8px',
                border: '1px solid #d1d5db',
                borderRadius: '4px',
                boxSizing: 'border-box',
              }}
            />
          </div>

          <div style={{ marginBottom: '24px' }}>
            <label style={{ display: 'block', marginBottom: '8px', fontWeight: '500' }}>{'权限组(可多选)'}</label>
            <div
              style={{
                border: '1px solid #d1d5db',
                borderRadius: '4px',
                padding: '12px',
                maxHeight: '200px',
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
                      checked={newUser.group_ids?.includes(group.group_id) || false}
                      onChange={(e) => onToggleGroup(group.group_id, e.target.checked)}
                      data-testid={`users-create-group-${group.group_id}`}
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
            {newUser.group_ids && newUser.group_ids.length > 0 && (
              <div style={{ marginTop: '8px', fontSize: '0.85rem', color: '#6b7280' }}>
                {'已选择'} {newUser.group_ids.length} {'个权限组'}
              </div>
            )}
          </div>

          <div style={{ display: 'flex', gap: '12px' }}>
            <button
              type="submit"
              data-testid="users-create-submit"
              style={{
                flex: 1,
                padding: '10px',
                backgroundColor: '#3b82f6',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer',
              }}
            >
              {'创建'}
            </button>
            <button
              type="button"
              onClick={onCancel}
              data-testid="users-create-cancel"
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
          </div>
        </form>
      </div>
    </div>
  );
}
