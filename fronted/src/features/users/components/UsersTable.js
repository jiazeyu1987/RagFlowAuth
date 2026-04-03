import React from 'react';

const isUserDisabled = (user) => {
  if (!user) return false;
  if (user.login_disabled === true) return true;
  const status = String(user.status || '').toLowerCase();
  if (status && status !== 'active') return true;
  const disableEnabled = user.disable_login_enabled === true;
  if (!disableEnabled) return false;
  const untilMs = Number(user.disable_login_until_ms || 0);
  if (!Number.isFinite(untilMs) || untilMs <= 0) return true;
  return Date.now() < untilMs;
};

export default function UsersTable({
  filteredUsers,
  canManageUsers,
  canEditUserPolicy,
  canAssignGroups,
  canResetPasswords,
  canToggleUserStatus,
  canDeleteUsers,
  onOpenPolicyModal,
  onAssignGroup,
  onOpenResetPassword,
  onDeleteUser,
  onToggleUserStatus,
  statusUpdatingUserId,
}) {
  return (
    <div
      style={{
        backgroundColor: 'white',
        borderRadius: '8px',
        boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
        overflow: 'hidden',
      }}
    >
      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', minWidth: '1100px', borderCollapse: 'collapse' }}>
          <thead style={{ backgroundColor: '#f9fafb' }}>
            <tr>
              <th style={{ padding: '12px 16px', textAlign: 'left', borderBottom: '1px solid #e5e7eb' }}>
                姓名 / 账号
              </th>
              <th style={{ padding: '12px 16px', textAlign: 'left', borderBottom: '1px solid #e5e7eb' }}>
                公司
              </th>
              <th style={{ padding: '12px 16px', textAlign: 'left', borderBottom: '1px solid #e5e7eb' }}>
                部门
              </th>
              <th style={{ padding: '12px 16px', textAlign: 'left', borderBottom: '1px solid #e5e7eb' }}>
                状态
              </th>
              <th style={{ padding: '12px 16px', textAlign: 'left', borderBottom: '1px solid #e5e7eb' }}>
                登录策略
              </th>
              <th style={{ padding: '12px 16px', textAlign: 'left', borderBottom: '1px solid #e5e7eb' }}>
                权限组
              </th>
              <th style={{ padding: '12px 16px', textAlign: 'left', borderBottom: '1px solid #e5e7eb' }}>
                创建时间
              </th>
              <th style={{ padding: '12px 16px', textAlign: 'right', borderBottom: '1px solid #e5e7eb' }}>
                操作
              </th>
            </tr>
          </thead>
          <tbody>
            {filteredUsers.map((user) => {
              const isProtectedAdmin = String(user?.username || '').toLowerCase() === 'admin';
              const fullName = String(user?.full_name || '').trim();
              const fallbackName = String(user?.email || '').trim();
              const displayName = fullName || fallbackName;
              const disabledNow = isUserDisabled(user);

              return (
                <tr
                  key={user.user_id}
                  data-testid={`users-row-${user.user_id}`}
                  style={{ borderBottom: '1px solid #e5e7eb' }}
                >
                  <td style={{ padding: '12px 16px' }}>
                    <div style={{ color: '#111827', fontWeight: 500 }}>{displayName || user.username}</div>
                    {displayName ? (
                      <div style={{ color: '#6b7280', fontSize: '0.85rem' }}>{`账号: ${user.username}`}</div>
                    ) : null}
                  </td>
                  <td style={{ padding: '12px 16px', color: '#6b7280' }}>{user.company_name || '-'}</td>
                  <td style={{ padding: '12px 16px', color: '#6b7280' }}>{user.department_name || '-'}</td>
                  <td style={{ padding: '12px 16px' }}>
                    <span style={{ color: disabledNow ? '#ef4444' : '#10b981' }}>
                      {disabledNow ? '停用' : '激活'}
                    </span>
                  </td>
                  <td style={{ padding: '12px 16px', color: '#4b5563', fontSize: '0.9rem' }}>
                    <div>最大登录数: {Number(user.max_login_sessions || 3)}</div>
                    <div>空闲超时: {Number(user.idle_timeout_minutes || 120)} 分钟</div>
                    <div>当前在线: {Number(user.active_session_count || 0)}</div>
                    {user.disable_login_enabled && user.disable_login_until_ms ? (
                      <div>
                        禁用到期: {new Date(user.disable_login_until_ms).toLocaleString('zh-CN')}
                      </div>
                    ) : null}
                  </td>
                  <td style={{ padding: '12px 16px' }}>
                    {user.permission_groups && user.permission_groups.length > 0 ? (
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
                        {user.permission_groups.map((pg) => (
                          <span
                            key={pg.group_id}
                            style={{
                              display: 'inline-block',
                              padding: '4px 8px',
                              borderRadius: '4px',
                              backgroundColor: '#e0e7ff',
                              color: '#4338ca',
                              fontSize: '0.85rem',
                            }}
                          >
                            {pg.group_name}
                          </span>
                        ))}
                      </div>
                    ) : (
                      <span style={{ color: '#9ca3af', fontSize: '0.85rem' }}>未分配</span>
                    )}
                  </td>
                  <td style={{ padding: '12px 16px', color: '#6b7280', fontSize: '0.9rem' }}>
                    {new Date(user.created_at_ms).toLocaleString('zh-CN')}
                  </td>
                  <td style={{ padding: '12px 16px', textAlign: 'right' }}>
                    {canEditUserPolicy && !isProtectedAdmin ? (
                      <button
                        type="button"
                        onClick={() => onOpenPolicyModal(user)}
                        data-testid={`users-edit-policy-${user.user_id}`}
                        style={{
                          padding: '6px 12px',
                          backgroundColor: '#0ea5e9',
                          color: 'white',
                          border: 'none',
                          borderRadius: '4px',
                          cursor: 'pointer',
                          fontSize: '0.9rem',
                          marginRight: '8px',
                        }}
                      >
                        登录策略
                      </button>
                    ) : null}

                    {canAssignGroups && !isProtectedAdmin ? (
                      <button
                        type="button"
                        onClick={() => onAssignGroup(user)}
                        data-testid={`users-edit-groups-${user.user_id}`}
                        style={{
                          padding: '6px 12px',
                          backgroundColor: '#8b5cf6',
                          color: 'white',
                          border: 'none',
                          borderRadius: '4px',
                          cursor: 'pointer',
                          fontSize: '0.9rem',
                          marginRight: '8px',
                        }}
                      >
                        权限组
                      </button>
                    ) : null}

                    {canResetPasswords ? (
                      <button
                        type="button"
                        onClick={() => onOpenResetPassword(user)}
                        data-testid={`users-reset-password-${user.user_id}`}
                        style={{
                          padding: '6px 12px',
                          backgroundColor: '#3b82f6',
                          color: 'white',
                          border: 'none',
                          borderRadius: '4px',
                          cursor: 'pointer',
                          fontSize: '0.9rem',
                          marginRight: '8px',
                        }}
                      >
                        修改密码
                      </button>
                    ) : null}

                    {canToggleUserStatus && !isProtectedAdmin ? (
                      <button
                        type="button"
                        onClick={() => onToggleUserStatus(user)}
                        data-testid={`users-toggle-status-${user.user_id}`}
                        disabled={statusUpdatingUserId === user.user_id}
                        style={{
                          padding: '6px 12px',
                          backgroundColor: disabledNow ? '#10b981' : '#f59e0b',
                          color: 'white',
                          border: 'none',
                          borderRadius: '4px',
                          cursor: statusUpdatingUserId === user.user_id ? 'not-allowed' : 'pointer',
                          opacity: statusUpdatingUserId === user.user_id ? 0.7 : 1,
                          fontSize: '0.9rem',
                          marginRight: '8px',
                        }}
                      >
                        {statusUpdatingUserId === user.user_id
                          ? disabledNow
                            ? '解禁中...'
                            : '禁用中...'
                          : disabledNow
                            ? '解禁'
                            : '禁用'}
                      </button>
                    ) : null}

                    {canDeleteUsers && !isProtectedAdmin ? (
                      <button
                        type="button"
                        onClick={() => onDeleteUser(user.user_id)}
                        data-testid={`users-delete-${user.user_id}`}
                        style={{
                          padding: '6px 12px',
                          backgroundColor: '#ef4444',
                          color: 'white',
                          border: 'none',
                          borderRadius: '4px',
                          cursor: 'pointer',
                          fontSize: '0.9rem',
                        }}
                      >
                        删除
                      </button>
                    ) : null}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {filteredUsers.length === 0 ? (
        <div style={{ padding: '48px', textAlign: 'center', color: '#6b7280' }}>暂无用户</div>
      ) : null}
    </div>
  );
}
