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
    <div className="users-med-section">
      <div className="users-med-filter-grid" style={{ alignItems: 'end' }}>
        <div className="users-med-field" style={{ minWidth: 220 }}>
          <label>搜索用户</label>
          <input
            value={filters.q}
            onChange={(e) => setFilters({ ...filters, q: e.target.value })}
            placeholder="支持模糊检索"
            data-testid="users-filter-q"
            className="medui-input"
          />
        </div>

        <div className="users-med-field">
          <label>公司</label>
          <select
            value={filters.company_id}
            onChange={(e) => setFilters({ ...filters, company_id: e.target.value })}
            data-testid="users-filter-company"
            className="medui-select"
          >
            <option value="">全部</option>
            {companies.map((c) => (
              <option key={c.id} value={String(c.id)}>
                {c.name}
              </option>
            ))}
          </select>
        </div>

        <div className="users-med-field">
          <label>部门</label>
          <select
            value={filters.department_id}
            onChange={(e) => setFilters({ ...filters, department_id: e.target.value })}
            data-testid="users-filter-department"
            className="medui-select"
          >
            <option value="">全部</option>
            {departments.map((d) => (
              <option key={d.id} value={String(d.id)}>
                {d.name}
              </option>
            ))}
          </select>
        </div>

        <div className="users-med-field">
          <label>状态</label>
          <select
            value={filters.status}
            onChange={(e) => setFilters({ ...filters, status: e.target.value })}
            data-testid="users-filter-status"
            className="medui-select"
          >
            <option value="">全部</option>
            <option value="active">启用</option>
            <option value="inactive">停用</option>
          </select>
        </div>

        <div className="users-med-field">
          <label>权限组</label>
          <select
            value={filters.group_id}
            onChange={(e) => setFilters({ ...filters, group_id: e.target.value })}
            data-testid="users-filter-group"
            className="medui-select"
          >
            <option value="">全部</option>
            {availableGroups.map((g) => (
              <option key={g.group_id} value={String(g.group_id)}>
                {g.group_name}
              </option>
            ))}
          </select>
        </div>

        <div className="users-med-field">
          <label>创建时间（从）</label>
          <input
            type="date"
            value={filters.created_from}
            onChange={(e) => setFilters({ ...filters, created_from: e.target.value })}
            data-testid="users-filter-created-from"
            className="medui-input"
          />
        </div>

        <div className="users-med-field">
          <label>创建时间（到）</label>
          <input
            type="date"
            value={filters.created_to}
            onChange={(e) => setFilters({ ...filters, created_to: e.target.value })}
            data-testid="users-filter-created-to"
            className="medui-input"
          />
        </div>

        <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
          <button type="button" onClick={onResetFilters} data-testid="users-filter-reset" className="medui-btn medui-btn--neutral">
            重置
          </button>
        </div>
      </div>
    </div>
  );
}
