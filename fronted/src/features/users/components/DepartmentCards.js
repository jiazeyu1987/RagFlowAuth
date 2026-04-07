import React from 'react';
import useMobileBreakpoint from '../../../shared/hooks/useMobileBreakpoint';

export default function DepartmentCards({ filteredUsers, groupedUsers, filters, setFilters }) {
  const isMobile = useMobileBreakpoint(768);

  return (
    <div
      style={{
        backgroundColor: 'white',
        borderRadius: '8px',
        boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
        padding: isMobile ? '12px' : '16px',
        marginBottom: '16px',
      }}
    >
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: isMobile ? 'stretch' : 'center',
          flexDirection: isMobile ? 'column' : 'row',
          marginBottom: '12px',
          gap: '12px',
          flexWrap: 'wrap',
        }}
      >
        <div>
          <div style={{ fontSize: '1rem', fontWeight: 600, color: '#111827' }}>{'按部门划分'}</div>
          <div style={{ fontSize: '0.9rem', color: '#6b7280' }}>
            {'当前筛选结果共'} {filteredUsers.length} {'个用户，分布在'} {groupedUsers.length} {'个部门中'}
          </div>
        </div>
        {filters.department_id && (
          <button
            type="button"
            onClick={() => setFilters({ ...filters, department_id: '' })}
            style={{
              padding: '8px 12px',
              backgroundColor: '#6b7280',
              color: 'white',
              border: 'none',
              borderRadius: '6px',
              cursor: 'pointer',
              width: isMobile ? '100%' : 'auto',
            }}
          >
            {'清除部门筛选'}
          </button>
        )}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: isMobile ? '1fr' : 'repeat(auto-fit, minmax(240px, 1fr))', gap: '12px' }}>
        {groupedUsers.map((group) => (
          <div
            key={group.key}
            data-testid={`users-department-group-${group.key}`}
            style={{
              border: '1px solid #e5e7eb',
              borderRadius: '8px',
              padding: '14px',
              backgroundColor:
                group.departmentId != null && String(filters.department_id || '') === String(group.departmentId)
                  ? '#eff6ff'
                  : '#f9fafb',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: isMobile ? 'flex-start' : 'center', flexDirection: isMobile ? 'column' : 'row', gap: '8px', marginBottom: '8px' }}>
              <div style={{ fontWeight: 600, color: '#111827' }}>{group.departmentName}</div>
              <div style={{ fontSize: '0.85rem', color: '#6b7280' }}>{`${group.users.length} 人`}</div>
            </div>

            <div style={{ fontSize: '0.9rem', color: '#4b5563', marginBottom: '10px', minHeight: '40px' }}>
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
                style={{
                  padding: '8px 12px',
                  backgroundColor: '#2563eb',
                  color: 'white',
                  border: 'none',
                  borderRadius: '6px',
                  cursor: 'pointer',
                  width: '100%',
                }}
              >
                {'只看本部门'}
              </button>
            ) : (
              <div style={{ fontSize: '0.85rem', color: '#9ca3af' }}>{'这些用户尚未分配部门'}</div>
            )}
          </div>
        ))}
      </div>

      {groupedUsers.length === 0 && <div style={{ marginTop: '12px', color: '#6b7280', textAlign: 'center' }}>{'暂无用户分组'}</div>}
    </div>
  );
}
