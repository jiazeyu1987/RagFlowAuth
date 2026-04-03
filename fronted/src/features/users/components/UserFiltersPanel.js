import React, { useEffect, useState } from 'react';

export default function UserFiltersPanel({
  filters,
  setFilters,
  companies,
  departments,
  availableGroups,
  onResetFilters,
}) {
  const [isMobile, setIsMobile] = useState(() => {
    if (typeof window === 'undefined') return false;
    return window.innerWidth <= 768;
  });

  useEffect(() => {
    if (typeof window === 'undefined') return undefined;

    const handleResize = () => setIsMobile(window.innerWidth <= 768);
    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const fieldWrapStyle = (minWidth) => ({
    minWidth: isMobile ? '100%' : minWidth,
    width: isMobile ? '100%' : 'auto',
  });

  const inputStyle = {
    width: '100%',
    padding: '8px',
    border: '1px solid #d1d5db',
    borderRadius: '6px',
    boxSizing: 'border-box',
  };

  const selectedCompanyId = filters.company_id ? Number(filters.company_id) : null;
  const visibleDepartments =
    selectedCompanyId == null
      ? departments
      : departments.filter((department) => department.company_id == null || department.company_id === selectedCompanyId);

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
          flexWrap: 'wrap',
          gap: '12px',
          alignItems: isMobile ? 'stretch' : 'flex-end',
          flexDirection: isMobile ? 'column' : 'row',
        }}
      >
        <div style={fieldWrapStyle('220px')}>
          <label style={{ display: 'block', marginBottom: '6px', fontWeight: 500 }}>{'搜索用户名'}</label>
          <input
            value={filters.q}
            onChange={(e) => setFilters({ ...filters, q: e.target.value })}
            placeholder={'支持模糊搜索'}
            data-testid="users-filter-q"
            style={inputStyle}
          />
        </div>

        <div style={fieldWrapStyle('180px')}>
          <label style={{ display: 'block', marginBottom: '6px', fontWeight: 500 }}>{'公司'}</label>
          <select
            value={filters.company_id}
            onChange={(e) => setFilters({ ...filters, company_id: e.target.value })}
            data-testid="users-filter-company"
            style={inputStyle}
          >
            <option value="">{'全部'}</option>
            {companies.map((c) => (
              <option key={c.id} value={String(c.id)}>
                {c.name}
              </option>
            ))}
          </select>
        </div>

        <div style={fieldWrapStyle('180px')}>
          <label style={{ display: 'block', marginBottom: '6px', fontWeight: 500 }}>{'部门'}</label>
          <select
            value={filters.department_id}
            onChange={(e) => setFilters({ ...filters, department_id: e.target.value })}
            data-testid="users-filter-department"
            style={inputStyle}
          >
            <option value="">{'全部'}</option>
            {visibleDepartments.map((d) => (
              <option key={d.id} value={String(d.id)}>
                {d.path_name || d.name}
              </option>
            ))}
          </select>
        </div>

        <div style={fieldWrapStyle('140px')}>
          <label style={{ display: 'block', marginBottom: '6px', fontWeight: 500 }}>{'状态'}</label>
          <select
            value={filters.status}
            onChange={(e) => setFilters({ ...filters, status: e.target.value })}
            data-testid="users-filter-status"
            style={inputStyle}
          >
            <option value="">{'全部'}</option>
            <option value="active">{'激活'}</option>
            <option value="inactive">{'停用'}</option>
          </select>
        </div>

        <div style={fieldWrapStyle('180px')}>
          <label style={{ display: 'block', marginBottom: '6px', fontWeight: 500 }}>{'权限组'}</label>
          <select
            value={filters.group_id}
            onChange={(e) => setFilters({ ...filters, group_id: e.target.value })}
            data-testid="users-filter-group"
            style={inputStyle}
          >
            <option value="">{'全部'}</option>
            {availableGroups.map((g) => (
              <option key={g.group_id} value={String(g.group_id)}>
                {g.group_name}
              </option>
            ))}
          </select>
        </div>

        <div style={fieldWrapStyle('180px')}>
          <label style={{ display: 'block', marginBottom: '6px', fontWeight: 500 }}>{'创建时间(从)'}</label>
          <input
            type="date"
            value={filters.created_from}
            onChange={(e) => setFilters({ ...filters, created_from: e.target.value })}
            data-testid="users-filter-created-from"
            style={inputStyle}
          />
        </div>

        <div style={fieldWrapStyle('180px')}>
          <label style={{ display: 'block', marginBottom: '6px', fontWeight: 500 }}>{'创建时间(到)'}</label>
          <input
            type="date"
            value={filters.created_to}
            onChange={(e) => setFilters({ ...filters, created_to: e.target.value })}
            data-testid="users-filter-created-to"
            style={inputStyle}
          />
        </div>

        <button
          type="button"
          onClick={onResetFilters}
          data-testid="users-filter-reset"
          style={{
            padding: '10px 14px',
            backgroundColor: '#6b7280',
            color: 'white',
            border: 'none',
            borderRadius: '6px',
            cursor: 'pointer',
            width: isMobile ? '100%' : 'auto',
          }}
        >
          {'重置'}
        </button>
      </div>
    </div>
  );
}
