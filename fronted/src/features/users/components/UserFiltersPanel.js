import React from 'react';

export default function UserFiltersPanel({
  filters,
  setFilters,
  companies,
  departments,
  availableGroups,
  onResetFilters,
}) {
  return (
    <div
      style={{
        backgroundColor: 'white',
        borderRadius: '8px',
        boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
        padding: '16px',
        marginBottom: '16px',
      }}
    >
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '12px', alignItems: 'flex-end' }}>
        <div style={{ minWidth: '220px' }}>
          <label style={{ display: 'block', marginBottom: '6px', fontWeight: 500 }}>{'搜索用户名'}</label>
          <input
            value={filters.q}
            onChange={(e) => setFilters({ ...filters, q: e.target.value })}
            placeholder={'支持模糊搜索'}
            data-testid="users-filter-q"
            style={{
              width: '100%',
              padding: '8px',
              border: '1px solid #d1d5db',
              borderRadius: '6px',
              boxSizing: 'border-box',
            }}
          />
        </div>

        <div style={{ minWidth: '180px' }}>
          <label style={{ display: 'block', marginBottom: '6px', fontWeight: 500 }}>{'公司'}</label>
          <select
            value={filters.company_id}
            onChange={(e) => setFilters({ ...filters, company_id: e.target.value })}
            data-testid="users-filter-company"
            style={{ width: '100%', padding: '8px', border: '1px solid #d1d5db', borderRadius: '6px' }}
          >
            <option value="">{'全部'}</option>
            {companies.map((c) => (
              <option key={c.id} value={String(c.id)}>
                {c.name}
              </option>
            ))}
          </select>
        </div>

        <div style={{ minWidth: '180px' }}>
          <label style={{ display: 'block', marginBottom: '6px', fontWeight: 500 }}>{'部门'}</label>
          <select
            value={filters.department_id}
            onChange={(e) => setFilters({ ...filters, department_id: e.target.value })}
            data-testid="users-filter-department"
            style={{ width: '100%', padding: '8px', border: '1px solid #d1d5db', borderRadius: '6px' }}
          >
            <option value="">{'全部'}</option>
            {departments.map((d) => (
              <option key={d.id} value={String(d.id)}>
                {d.name}
              </option>
            ))}
          </select>
        </div>

        <div style={{ minWidth: '140px' }}>
          <label style={{ display: 'block', marginBottom: '6px', fontWeight: 500 }}>{'状态'}</label>
          <select
            value={filters.status}
            onChange={(e) => setFilters({ ...filters, status: e.target.value })}
            data-testid="users-filter-status"
            style={{ width: '100%', padding: '8px', border: '1px solid #d1d5db', borderRadius: '6px' }}
          >
            <option value="">{'全部'}</option>
            <option value="active">{'激活'}</option>
            <option value="inactive">{'停用'}</option>
          </select>
        </div>

        <div style={{ minWidth: '180px' }}>
          <label style={{ display: 'block', marginBottom: '6px', fontWeight: 500 }}>{'权限组'}</label>
          <select
            value={filters.group_id}
            onChange={(e) => setFilters({ ...filters, group_id: e.target.value })}
            data-testid="users-filter-group"
            style={{ width: '100%', padding: '8px', border: '1px solid #d1d5db', borderRadius: '6px' }}
          >
            <option value="">{'全部'}</option>
            {availableGroups.map((g) => (
              <option key={g.group_id} value={String(g.group_id)}>
                {g.group_name}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label style={{ display: 'block', marginBottom: '6px', fontWeight: 500 }}>{'创建时间(从)'}</label>
          <input
            type="date"
            value={filters.created_from}
            onChange={(e) => setFilters({ ...filters, created_from: e.target.value })}
            data-testid="users-filter-created-from"
            style={{ padding: '8px', border: '1px solid #d1d5db', borderRadius: '6px' }}
          />
        </div>

        <div>
          <label style={{ display: 'block', marginBottom: '6px', fontWeight: 500 }}>{'创建时间(到)'}</label>
          <input
            type="date"
            value={filters.created_to}
            onChange={(e) => setFilters({ ...filters, created_to: e.target.value })}
            data-testid="users-filter-created-to"
            style={{ padding: '8px', border: '1px solid #d1d5db', borderRadius: '6px' }}
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
          }}
        >
          {'重置'}
        </button>
      </div>
    </div>
  );
}
