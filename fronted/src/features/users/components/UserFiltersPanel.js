import React from 'react';
import useMobileBreakpoint from '../../../shared/hooks/useMobileBreakpoint';

const TEXT = {
  searchUser: '\u641c\u7d22\u7528\u6237',
  searchPlaceholder: '\u652f\u6301\u6a21\u7cca\u641c\u7d22',
  company: '\u516c\u53f8',
  department: '\u90e8\u95e8',
  status: '\u72b6\u6001',
  all: '\u5168\u90e8',
  active: '\u6fc0\u6d3b',
  inactive: '\u505c\u7528',
  permissionGroup: '\u6743\u9650\u7ec4',
  permissionAssignment: '\u6743\u9650\u5206\u914d',
  unassigned: '\u5f85\u5206\u914d',
  assigned: '\u5df2\u5206\u914d',
  createdFrom: '\u521b\u5efa\u65f6\u95f4(\u4ece)',
  createdTo: '\u521b\u5efa\u65f6\u95f4(\u81f3)',
  reset: '\u91cd\u7f6e',
  loading: '\u52a0\u8f7d\u4e2d...',
};

export default function UserFiltersPanel({
  filters,
  setFilters,
  companies,
  departments,
  availableGroups,
  permissionGroupsLoading = false,
  permissionGroupsError = null,
  isSubAdminUser,
  onGroupFilterFocus,
  onResetFilters,
}) {
  const isMobile = useMobileBreakpoint(768);
  const groupFilterPlaceholder =
    permissionGroupsLoading && availableGroups.length === 0
      ? TEXT.loading
      : TEXT.all;

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
      : departments.filter(
          (department) => department.company_id == null || department.company_id === selectedCompanyId
        );

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
          <label style={{ display: 'block', marginBottom: '6px', fontWeight: 500 }}>
            {TEXT.searchUser}
          </label>
          <input
            value={filters.q}
            onChange={(e) => setFilters({ ...filters, q: e.target.value })}
            placeholder={TEXT.searchPlaceholder}
            data-testid="users-filter-q"
            style={inputStyle}
          />
        </div>

        {isSubAdminUser ? null : (
          <div style={fieldWrapStyle('180px')}>
            <label style={{ display: 'block', marginBottom: '6px', fontWeight: 500 }}>
              {TEXT.company}
            </label>
            <select
              value={filters.company_id}
              onChange={(e) => setFilters({ ...filters, company_id: e.target.value })}
              data-testid="users-filter-company"
              style={inputStyle}
            >
              <option value="">{TEXT.all}</option>
              {companies.map((company) => (
                <option key={company.id} value={String(company.id)}>
                  {company.name}
                </option>
              ))}
            </select>
          </div>
        )}

        {isSubAdminUser ? null : (
          <div style={fieldWrapStyle('180px')}>
            <label style={{ display: 'block', marginBottom: '6px', fontWeight: 500 }}>
              {TEXT.department}
            </label>
            <select
              value={filters.department_id}
              onChange={(e) => setFilters({ ...filters, department_id: e.target.value })}
              data-testid="users-filter-department"
              style={inputStyle}
            >
              <option value="">{TEXT.all}</option>
              {visibleDepartments.map((department) => (
                <option key={department.id} value={String(department.id)}>
                  {department.path_name || department.name}
                </option>
              ))}
            </select>
          </div>
        )}

        <div style={fieldWrapStyle('140px')}>
          <label style={{ display: 'block', marginBottom: '6px', fontWeight: 500 }}>
            {TEXT.status}
          </label>
          <select
            value={filters.status}
            onChange={(e) => setFilters({ ...filters, status: e.target.value })}
            data-testid="users-filter-status"
            style={inputStyle}
          >
            <option value="">{TEXT.all}</option>
            <option value="active">{TEXT.active}</option>
            <option value="inactive">{TEXT.inactive}</option>
          </select>
        </div>

        <div style={fieldWrapStyle('180px')}>
          <label style={{ display: 'block', marginBottom: '6px', fontWeight: 500 }}>
            {TEXT.permissionGroup}
          </label>
          <select
            value={filters.group_id}
            onChange={(e) => setFilters({ ...filters, group_id: e.target.value })}
            onFocus={onGroupFilterFocus}
            data-testid="users-filter-group"
            aria-busy={permissionGroupsLoading && availableGroups.length === 0}
            style={inputStyle}
          >
            <option value="">{groupFilterPlaceholder}</option>
            {availableGroups.map((group) => (
              <option key={group.group_id} value={String(group.group_id)}>
                {group.group_name}
              </option>
            ))}
          </select>
          {permissionGroupsError ? (
            <div
              style={{ marginTop: '6px', color: '#ef4444', fontSize: '0.85rem' }}
              data-testid="users-filter-group-error"
            >
              {permissionGroupsError}
            </div>
          ) : null}
        </div>

        <div style={fieldWrapStyle('180px')}>
          <label style={{ display: 'block', marginBottom: '6px', fontWeight: 500 }}>
            {TEXT.permissionAssignment}
          </label>
          <select
            value={filters.assignment_status || ''}
            onChange={(e) => setFilters({ ...filters, assignment_status: e.target.value })}
            data-testid="users-filter-assignment-status"
            style={inputStyle}
          >
            <option value="">{TEXT.all}</option>
            <option value="unassigned">{TEXT.unassigned}</option>
            <option value="assigned">{TEXT.assigned}</option>
          </select>
        </div>

        {isSubAdminUser ? null : (
          <div style={fieldWrapStyle('180px')}>
            <label style={{ display: 'block', marginBottom: '6px', fontWeight: 500 }}>
              {TEXT.createdFrom}
            </label>
            <input
              type="date"
              value={filters.created_from}
              onChange={(e) => setFilters({ ...filters, created_from: e.target.value })}
              data-testid="users-filter-created-from"
              style={inputStyle}
            />
          </div>
        )}

        {isSubAdminUser ? null : (
          <div style={fieldWrapStyle('180px')}>
            <label style={{ display: 'block', marginBottom: '6px', fontWeight: 500 }}>
              {TEXT.createdTo}
            </label>
            <input
              type="date"
              value={filters.created_to}
              onChange={(e) => setFilters({ ...filters, created_to: e.target.value })}
              data-testid="users-filter-created-to"
              style={inputStyle}
            />
          </div>
        )}

        <button
          type="button"
          onClick={onResetFilters}
          data-testid="users-filter-reset"
          style={{
            padding: '10px 14px',
            backgroundColor: '#dc2626',
            color: 'white',
            border: 'none',
            borderRadius: '6px',
            cursor: 'pointer',
            width: isMobile ? '100%' : 'auto',
          }}
        >
          {TEXT.reset}
        </button>
      </div>
    </div>
  );
}
