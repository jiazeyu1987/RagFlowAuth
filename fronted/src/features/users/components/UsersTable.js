import React from 'react';

const formatRole = (role) => {
  const value = String(role || '').trim();
  if (value === 'admin') return '管理员';
  if (value === 'sub_admin') return '子管理员';
  return '普通用户';
};

const formatStatus = (user) => {
  if (user?.login_disabled) return '已停用';
  return String(user?.status || '').toLowerCase() === 'active' ? '正常' : '已停用';
};

const roleBadgeStyle = (role) => {
  if (role === 'sub_admin') {
    return {
      backgroundColor: '#ecfeff',
      border: '1px solid #67e8f9',
      color: '#155e75',
    };
  }
  if (role === 'admin') {
    return {
      backgroundColor: '#eff6ff',
      border: '1px solid #93c5fd',
      color: '#1d4ed8',
    };
  }
  return {
    backgroundColor: '#f3f4f6',
    border: '1px solid #d1d5db',
    color: '#374151',
  };
};

const getPermissionGroupNames = (user) => {
  const rawGroups = Array.isArray(user?.permission_groups) ? user.permission_groups : [];
  return Array.from(
    new Set(
      rawGroups
        .map((group) => String(group?.group_name || '').trim())
        .filter(Boolean)
    )
  );
};

const permissionGroupTagStyle = {
  display: 'inline-flex',
  alignItems: 'center',
  padding: '4px 8px',
  borderRadius: '999px',
  border: '1px solid #bfdbfe',
  backgroundColor: '#eff6ff',
  color: '#1d4ed8',
  fontSize: '0.78rem',
  fontWeight: 700,
  lineHeight: 1.2,
};

const pendingGroupTagStyle = {
  display: 'inline-flex',
  alignItems: 'center',
  padding: '4px 8px',
  borderRadius: '999px',
  border: '1px solid #fecaca',
  backgroundColor: '#fef2f2',
  color: '#b91c1c',
  fontSize: '0.78rem',
  fontWeight: 700,
  lineHeight: 1.2,
};

export default function UsersTable({
  filteredUsers,
  canEditUserPolicy,
  canAssignGroups,
  canAssignTools,
  canResetPasswords,
  canResetPasswordForUser,
  canToggleUserStatus,
  canDeleteUsers,
  onOpenPolicyModal,
  onAssignGroup,
  onAssignTool,
  onOpenResetPassword,
  onDeleteUser,
  onToggleUserStatus,
  statusUpdatingUserId,
}) {
  const users = Array.isArray(filteredUsers) ? filteredUsers : [];

  return (
    <div
      data-testid="users-table"
      style={{
        backgroundColor: 'white',
        borderRadius: '8px',
        boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
        overflow: 'hidden',
      }}
    >
      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ backgroundColor: '#f9fafb', textAlign: 'left' }}>
              <th style={{ padding: '12px 16px', fontWeight: 600 }}>用户</th>
              <th style={{ padding: '12px 16px', fontWeight: 600 }}>角色</th>
              <th style={{ padding: '12px 16px', fontWeight: 600 }}>公司/部门</th>
              <th style={{ padding: '12px 16px', fontWeight: 600 }}>权限组</th>
              <th style={{ padding: '12px 16px', fontWeight: 600 }}>状态</th>
              <th style={{ padding: '12px 16px', fontWeight: 600 }}>操作</th>
            </tr>
          </thead>
          <tbody>
            {users.map((user) => {
              const safeUserId = String(user?.user_id || '');
              const isBuiltInAdmin = String(user?.username || '').toLowerCase() === 'admin';
              const isActive = String(user?.status || '').toLowerCase() === 'active';
              const permissionGroupNames = getPermissionGroupNames(user);
              const canResetPasswordForRow =
                canResetPasswords &&
                (typeof canResetPasswordForUser === 'function'
                  ? !!canResetPasswordForUser(user)
                  : true);
              const canEditGroupsForUser =
                canAssignGroups &&
                String(user?.role || '') === 'viewer' &&
                !isBuiltInAdmin;
              const canEditToolsForUser =
                canAssignTools &&
                String(user?.role || '') === 'viewer' &&
                !isBuiltInAdmin;

              return (
                <tr
                  key={safeUserId}
                  data-testid={`users-row-${safeUserId}`}
                  style={{ borderTop: '1px solid #e5e7eb' }}
                >
                  <td style={{ padding: '14px 16px', verticalAlign: 'top' }}>
                    <div style={{ fontWeight: 600, color: '#111827' }}>
                      {user?.full_name || user?.username || '-'}
                    </div>
                  </td>
                  <td style={{ padding: '14px 16px', verticalAlign: 'top' }}>
                    <span
                      data-testid={`users-role-${safeUserId}`}
                      style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        padding: '4px 10px',
                        borderRadius: '999px',
                        fontSize: '0.82rem',
                        fontWeight: 700,
                        ...roleBadgeStyle(String(user?.role || '')),
                      }}
                    >
                      {formatRole(user?.role)}
                    </span>
                  </td>
                  <td style={{ padding: '14px 16px', verticalAlign: 'top' }}>
                    <div>{user?.company_name || '-'}</div>
                    <div style={{ fontSize: '0.85rem', color: '#6b7280' }}>
                      {user?.department_name || '-'}
                    </div>
                  </td>
                  <td style={{ padding: '14px 16px', verticalAlign: 'top' }}>
                    <div
                      data-testid={`users-permission-groups-${safeUserId}`}
                      style={{
                        display: 'flex',
                        flexWrap: 'wrap',
                        gap: 8,
                        alignItems: 'flex-start',
                      }}
                    >
                      {permissionGroupNames.length > 0 ? (
                        permissionGroupNames.map((groupName) => (
                          <span
                            key={`${safeUserId}-${groupName}`}
                            style={permissionGroupTagStyle}
                          >
                            {groupName}
                          </span>
                        ))
                      ) : (
                        <span
                          data-testid={`users-permission-groups-empty-${safeUserId}`}
                          style={pendingGroupTagStyle}
                        >
                          待分配
                        </span>
                      )}
                    </div>
                  </td>
                  <td style={{ padding: '14px 16px', verticalAlign: 'top' }}>{formatStatus(user)}</td>
                  <td style={{ padding: '14px 16px', verticalAlign: 'top' }}>
                    <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                      {canEditUserPolicy ? (
                        <button
                          type="button"
                          onClick={() => onOpenPolicyModal?.(user)}
                          data-testid={`users-edit-policy-${safeUserId}`}
                          style={{
                            padding: '6px 10px',
                            border: '1px solid #93c5fd',
                            background: '#eff6ff',
                            borderRadius: 6,
                            cursor: 'pointer',
                          }}
                        >
                          用户配置
                        </button>
                      ) : null}
                      {canEditGroupsForUser ? (
                        <button
                          type="button"
                          onClick={() => onAssignGroup?.(user)}
                          data-testid={`users-edit-groups-${safeUserId}`}
                          style={{
                            padding: '6px 10px',
                            border: '1px solid #cbd5e1',
                            background: '#f8fafc',
                            borderRadius: 6,
                            cursor: 'pointer',
                          }}
                        >
                          权限组
                        </button>
                      ) : null}
                      {canEditToolsForUser ? (
                        <button
                          type="button"
                          onClick={() => onAssignTool?.(user)}
                          data-testid={`users-edit-tools-${safeUserId}`}
                          style={{
                            padding: '6px 10px',
                            border: '1px solid #bfdbfe',
                            background: '#eff6ff',
                            borderRadius: 6,
                            cursor: 'pointer',
                          }}
                        >
                          工具权限
                        </button>
                      ) : null}
                      {canResetPasswordForRow ? (
                        <button
                          type="button"
                          onClick={() => onOpenResetPassword?.(user)}
                          data-testid={`users-reset-password-${safeUserId}`}
                          style={{
                            padding: '6px 10px',
                            border: '1px solid #cbd5e1',
                            background: '#f8fafc',
                            borderRadius: 6,
                            cursor: 'pointer',
                          }}
                        >
                          重置密码
                        </button>
                      ) : null}
                      {canToggleUserStatus ? (
                        <button
                          type="button"
                          onClick={() => onToggleUserStatus?.(user)}
                          disabled={statusUpdatingUserId === safeUserId || isBuiltInAdmin}
                          data-testid={`users-toggle-status-${safeUserId}`}
                          style={{
                            padding: '6px 10px',
                            border: '1px solid #fcd34d',
                            background: '#fffbeb',
                            borderRadius: 6,
                            cursor:
                              statusUpdatingUserId === safeUserId || isBuiltInAdmin
                                ? 'not-allowed'
                                : 'pointer',
                          }}
                        >
                          {isActive ? '停用' : '启用'}
                        </button>
                      ) : null}
                      {canDeleteUsers && !isBuiltInAdmin ? (
                        <button
                          type="button"
                          onClick={() => onDeleteUser?.(safeUserId)}
                          data-testid={`users-delete-${safeUserId}`}
                          style={{
                            padding: '6px 10px',
                            border: '1px solid #fecaca',
                            background: '#fef2f2',
                            borderRadius: 6,
                            cursor: 'pointer',
                            color: '#b91c1c',
                          }}
                        >
                          删除
                        </button>
                      ) : null}
                    </div>
                  </td>
                </tr>
              );
            })}
            {users.length === 0 ? (
              <tr>
                <td colSpan={6} style={{ padding: '24px 16px', textAlign: 'center', color: '#6b7280' }}>
                  暂无用户
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>
    </div>
  );
}
