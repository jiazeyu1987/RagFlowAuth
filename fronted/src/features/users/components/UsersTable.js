import React from 'react';

export default function UsersTable({
  filteredUsers,
  canManageUsers,
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
      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead style={{ backgroundColor: '#f9fafb' }}>
          <tr>
            <th style={{ padding: '12px 16px', textAlign: 'left', borderBottom: '1px solid #e5e7eb' }}>{'用户名'}</th>
            <th style={{ padding: '12px 16px', textAlign: 'left', borderBottom: '1px solid #e5e7eb' }}>{'公司'}</th>
            <th style={{ padding: '12px 16px', textAlign: 'left', borderBottom: '1px solid #e5e7eb' }}>{'部门'}</th>
            <th style={{ padding: '12px 16px', textAlign: 'left', borderBottom: '1px solid #e5e7eb' }}>{'状态'}</th>
            <th style={{ padding: '12px 16px', textAlign: 'left', borderBottom: '1px solid #e5e7eb' }}>{'登录策略'}</th>
            <th style={{ padding: '12px 16px', textAlign: 'left', borderBottom: '1px solid #e5e7eb' }}>{'权限组'}</th>
            <th style={{ padding: '12px 16px', textAlign: 'left', borderBottom: '1px solid #e5e7eb' }}>{'创建时间'}</th>
            <th style={{ padding: '12px 16px', textAlign: 'right', borderBottom: '1px solid #e5e7eb' }}>{'操作'}</th>
          </tr>
        </thead>
        <tbody>
          {filteredUsers.map((user) => {
            const isProtectedAdmin = String(user?.username || '').toLowerCase() === 'admin';
            return (
              <tr key={user.user_id} data-testid={`users-row-${user.user_id}`} style={{ borderBottom: '1px solid #e5e7eb' }}>
              <td style={{ padding: '12px 16px' }}>{user.username}</td>
              <td style={{ padding: '12px 16px', color: '#6b7280' }}>{user.company_name || '-'}</td>
              <td style={{ padding: '12px 16px', color: '#6b7280' }}>{user.department_name || '-'}</td>
              <td style={{ padding: '12px 16px' }}>
                <span
                  style={{
                    color: user.status === 'active' ? '#10b981' : '#ef4444',
                  }}
                >
                  {user.status === 'active' ? '激活' : '停用'}
                </span>
              </td>
              <td style={{ padding: '12px 16px', color: '#4b5563', fontSize: '0.9rem' }}>
                <div>{'最多登录: '} {Number(user.max_login_sessions || 3)}</div>
                <div>{'闲置超时: '} {Number(user.idle_timeout_minutes || 120)} {'分钟'}</div>
                <div>{'当前在线: '} {Number(user.active_session_count || 0)}</div>
                <div>
                  {'最近活跃: '}
                  {user.active_session_last_activity_at_ms ? new Date(user.active_session_last_activity_at_ms).toLocaleString('zh-CN') : '-'}
                </div>
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
                  <span style={{ color: '#9ca3af', fontSize: '0.85rem' }}>{'未分配'}</span>
                )}
              </td>
              <td style={{ padding: '12px 16px', color: '#6b7280', fontSize: '0.9rem' }}>
                {new Date(user.created_at_ms).toLocaleString('zh-CN')}
              </td>
              <td style={{ padding: '12px 16px', textAlign: 'right' }}>
                {canManageUsers && !isProtectedAdmin && (
                  <button
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
                    {'登录策略'}
                  </button>
                )}
                {canManageUsers && !isProtectedAdmin && (
                  <button
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
                    {'权限组'}
                  </button>
                )}
                {canManageUsers && (
                  <button
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
                    {'修改密码'}
                  </button>
                )}
                {canManageUsers && !isProtectedAdmin && (
                  <button
                    onClick={() => onToggleUserStatus(user)}
                    data-testid={`users-toggle-status-${user.user_id}`}
                    disabled={statusUpdatingUserId === user.user_id}
                    style={{
                      padding: '6px 12px',
                      backgroundColor: user.status === 'active' ? '#f59e0b' : '#10b981',
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
                      ? (user.status === 'active' ? '禁用中…' : '解禁中…')
                      : (user.status === 'active' ? '禁用' : '解禁')}
                  </button>
                )}
                {canManageUsers && !isProtectedAdmin && (
                  <button
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
                    {'删除'}
                  </button>
                )}
              </td>
              </tr>
            );
          })}
        </tbody>
      </table>

      {filteredUsers.length === 0 && <div style={{ padding: '48px', textAlign: 'center', color: '#6b7280' }}>{'暂无用户'}</div>}
    </div>
  );
}
