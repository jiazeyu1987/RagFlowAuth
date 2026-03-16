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
    <div className="users-med-section" style={{ padding: 0 }}>
      <div className="users-med-table-scroll">
        <table className="medui-table" style={{ minWidth: 1120 }}>
          <thead>
            <tr>
              <th>姓名 / 账号</th>
              <th>公司</th>
              <th>部门</th>
              <th>状态</th>
              <th>登录策略</th>
              <th>权限组</th>
              <th>创建时间</th>
              <th style={{ textAlign: 'right' }}>操作</th>
            </tr>
          </thead>
          <tbody>
            {filteredUsers.map((user) => {
              const isProtectedAdmin = String(user?.username || '').toLowerCase() === 'admin';
              const displayName = String(user?.email || '').trim();
              return (
                <tr key={user.user_id} data-testid={`users-row-${user.user_id}`}>
                  <td>
                    <div style={{ color: '#17324d', fontWeight: 700 }}>{displayName || user.username}</div>
                    {displayName ? <div className="users-med-note">{`账号: ${user.username}`}</div> : null}
                  </td>
                  <td className="users-med-table-cell-muted">{user.company_name || '-'}</td>
                  <td className="users-med-table-cell-muted">{user.department_name || '-'}</td>
                  <td>
                    <span className={`medui-badge ${user.status === 'active' ? 'medui-badge--success' : 'medui-badge--danger'}`}>
                      {user.status === 'active' ? '启用' : '停用'}
                    </span>
                  </td>
                  <td className="users-med-table-cell-muted">
                    <div>{`最多登录 ${Number(user.max_login_sessions || 3)}`}</div>
                    <div>{`空闲超时: ${Number(user.idle_timeout_minutes || 120)} 分钟`}</div>
                    <div>{`当前在线: ${Number(user.active_session_count || 0)}`}</div>
                    <div>
                      {`最近活跃: ${user.active_session_last_activity_at_ms ? new Date(user.active_session_last_activity_at_ms).toLocaleString('zh-CN') : '-'}`}
                    </div>
                  </td>
                  <td>
                    {user.permission_groups && user.permission_groups.length > 0 ? (
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                        {user.permission_groups.map((pg) => (
                          <span key={pg.group_id} className="medui-chip">
                            {pg.group_name}
                          </span>
                        ))}
                      </div>
                    ) : (
                      <span className="users-med-note">未分配</span>
                    )}
                  </td>
                  <td className="users-med-table-cell-muted">{new Date(user.created_at_ms).toLocaleString('zh-CN')}</td>
                  <td>
                    <div className="users-med-action-wrap">
                      {canManageUsers && !isProtectedAdmin && (
                        <button onClick={() => onOpenPolicyModal(user)} data-testid={`users-edit-policy-${user.user_id}`} type="button" className="medui-btn medui-btn--secondary">
                          登录策略
                        </button>
                      )}
                      {canManageUsers && !isProtectedAdmin && (
                        <button onClick={() => onAssignGroup(user)} data-testid={`users-edit-groups-${user.user_id}`} type="button" className="medui-btn medui-btn--secondary">
                          权限组
                        </button>
                      )}
                      {canManageUsers && (
                        <button onClick={() => onOpenResetPassword(user)} data-testid={`users-reset-password-${user.user_id}`} type="button" className="medui-btn medui-btn--primary">
                          修改密码
                        </button>
                      )}
                      {canManageUsers && !isProtectedAdmin && (
                        <button
                          onClick={() => onToggleUserStatus(user)}
                          data-testid={`users-toggle-status-${user.user_id}`}
                          disabled={statusUpdatingUserId === user.user_id}
                          type="button"
                          className={`medui-btn ${user.status === 'active' ? 'medui-btn--warn' : 'medui-btn--success'}`}
                        >
                          {statusUpdatingUserId === user.user_id ? (user.status === 'active' ? '停用中...' : '解禁中...') : user.status === 'active' ? '停用' : '解禁'}
                        </button>
                      )}
                      {canManageUsers && !isProtectedAdmin && (
                        <button onClick={() => onDeleteUser(user.user_id)} data-testid={`users-delete-${user.user_id}`} type="button" className="medui-btn medui-btn--danger">
                          删除
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {filteredUsers.length === 0 && <div className="medui-empty">暂无用户。</div>}
    </div>
  );
}
