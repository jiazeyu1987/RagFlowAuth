import React from 'react';

export default function DepartmentCards({ filteredUsers, groupedUsers, filters, setFilters }) {
  return (
    <div className="users-med-section">
      <div className="medui-header-row" style={{ marginBottom: 12 }}>
        <div>
          <div className="medui-title">按部门分布</div>
          <div className="medui-subtitle">
            {`当前筛选结果共 ${filteredUsers.length} 个用户，分布在 ${groupedUsers.length} 个部门中`}
          </div>
        </div>
        {filters.department_id && (
          <button
            type="button"
            onClick={() => setFilters({ ...filters, department_id: '' })}
            className="medui-btn medui-btn--neutral"
          >
            清除部门筛选
          </button>
        )}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: 12 }}>
        {groupedUsers.map((group) => (
          <div
            key={group.key}
            data-testid={`users-department-group-${group.key}`}
            className="medui-surface--soft"
            style={{
              border: '1px solid #d8e5f3',
              borderRadius: 12,
              padding: 12,
              background:
                group.departmentId != null && String(filters.department_id || '') === String(group.departmentId)
                  ? '#eaf4ff'
                  : '#f9fcff',
            }}
          >
            <div className="medui-header-row" style={{ marginBottom: 8 }}>
              <div style={{ fontWeight: 700, color: '#173d60' }}>{group.departmentName}</div>
              <div className="medui-subtitle">{`${group.users.length} 人`}</div>
            </div>

            <div style={{ fontSize: '0.88rem', color: '#4b6781', marginBottom: 10, minHeight: 40 }}>
              {group.users
                .slice(0, 6)
                .map((user) => String(user?.email || '').trim() || user.username)
                .join('、')}
              {group.users.length > 6 ? ` 等 ${group.users.length} 人` : ''}
            </div>

            {group.departmentId != null ? (
              <button
                type="button"
                onClick={() => setFilters({ ...filters, department_id: String(group.departmentId) })}
                className="medui-btn medui-btn--secondary"
                style={{ width: '100%' }}
              >
                仅看本部门
              </button>
            ) : (
              <div className="users-med-note">这些用户尚未分配部门。</div>
            )}
          </div>
        ))}
      </div>

      {groupedUsers.length === 0 && <div className="medui-empty">暂无用户分组。</div>}
    </div>
  );
}
