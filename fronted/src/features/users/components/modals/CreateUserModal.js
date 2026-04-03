import React, { useEffect, useMemo, useState } from 'react';
import KnowledgeRootNodeSelector from '../KnowledgeRootNodeSelector';

const MOBILE_BREAKPOINT = 768;

const TEXT = {
  title: '\u65b0\u5efa\u7528\u6237',
  fullName: '\u59d3\u540d',
  username: '\u7528\u6237\u8d26\u53f7',
  password: '\u5bc6\u7801',
  userType: '\u7528\u6237\u7c7b\u578b',
  normalUser: '\u666e\u901a\u7528\u6237',
  subAdmin: '\u5b50\u7ba1\u7406\u5458',
  company: '\u516c\u53f8',
  companyPlaceholder: '\u8bf7\u9009\u62e9\u516c\u53f8',
  department: '\u90e8\u95e8',
  departmentPlaceholder: '\u8bf7\u9009\u62e9\u90e8\u95e8',
  ownerSubAdmin: '\u5f52\u5c5e\u5b50\u7ba1\u7406\u5458',
  ownerSubAdminPlaceholder: '\u8bf7\u9009\u62e9\u5f52\u5c5e\u5b50\u7ba1\u7406\u5458',
  maxSessions: '\u6700\u5927\u767b\u5f55\u4f1a\u8bdd\u6570',
  idleTimeout: '\u7a7a\u95f2\u8d85\u65f6(\u5206\u949f)',
  permissionGroup: '\u6743\u9650\u7ec4',
  normalUserHint:
    '\u521b\u5efa\u666e\u901a\u7528\u6237\u65f6\u4e0d\u76f4\u63a5\u914d\u7f6e\u6743\u9650\u7ec4\uff0c\u540e\u7eed\u7531\u5f52\u5c5e\u5b50\u7ba1\u7406\u5458\u8d1f\u8d23\u5206\u914d\u3002',
  kbRoot: '\u77e5\u8bc6\u5e93\u8d1f\u8d23\u76ee\u5f55',
  kbRootHint:
    '\u8be5\u7528\u6237\u62e5\u6709\u6240\u9009\u76ee\u5f55\u53ca\u5176\u540e\u4ee3\u7684\u5168\u90e8\u77e5\u8bc6\u5e93\u7ba1\u7406\u6743\u9650\u3002',
  submit: '\u521b\u5efa',
  cancel: '\u53d6\u6d88',
};

export default function CreateUserModal({
  open,
  newUser,
  error,
  companies,
  departments,
  subAdminOptions,
  kbDirectoryNodes,
  kbDirectoryLoading,
  kbDirectoryError,
  kbDirectoryCreateError,
  kbDirectoryCreatingRoot,
  orgDirectoryError,
  onSubmit,
  onCancel,
  onFieldChange,
  onCreateRootDirectory,
}) {
  const [isMobile, setIsMobile] = useState(() => {
    if (typeof window === 'undefined') return false;
    return window.innerWidth <= MOBILE_BREAKPOINT;
  });

  useEffect(() => {
    if (typeof window === 'undefined') return undefined;
    const handleResize = () => setIsMobile(window.innerWidth <= MOBILE_BREAKPOINT);
    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const inputStyle = {
    width: '100%',
    padding: '8px',
    border: '1px solid #d1d5db',
    borderRadius: '4px',
    boxSizing: 'border-box',
  };

  const selectedCompanyId = newUser.company_id ? Number(newUser.company_id) : null;
  const visibleDepartments = useMemo(() => {
    const items = Array.isArray(departments) ? departments : [];
    if (selectedCompanyId == null) return items;
    return items.filter(
      (department) => department.company_id == null || Number(department.company_id) === selectedCompanyId
    );
  }, [departments, selectedCompanyId]);

  const isSubAdmin = String(newUser.user_type || 'normal') === 'sub_admin';

  if (!open) return null;

  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.5)',
        display: 'flex',
        justifyContent: 'center',
        alignItems: isMobile ? 'stretch' : 'center',
        padding: isMobile ? '16px 12px' : '24px',
        zIndex: 1000,
      }}
    >
      <div
        style={{
          backgroundColor: 'white',
          padding: isMobile ? '20px 16px' : '32px',
          borderRadius: '8px',
          width: '100%',
          maxWidth: '420px',
          maxHeight: isMobile ? '100%' : '90vh',
          overflowY: 'auto',
          margin: isMobile ? 'auto 0' : 0,
        }}
      >
        <h3 style={{ margin: '0 0 24px 0' }}>{TEXT.title}</h3>
        <form onSubmit={onSubmit} data-testid="users-create-form">
          <div style={{ marginBottom: '16px' }}>
            <label style={{ display: 'block', marginBottom: '8px', fontWeight: '500' }}>{TEXT.fullName}</label>
            <input
              type="text"
              value={newUser.full_name || ''}
              onChange={(event) => onFieldChange('full_name', event.target.value)}
              data-testid="users-create-full-name"
              style={inputStyle}
            />
          </div>

          <div style={{ marginBottom: '16px' }}>
            <label style={{ display: 'block', marginBottom: '8px', fontWeight: '500' }}>{TEXT.username}</label>
            <input
              type="text"
              required
              value={newUser.username || ''}
              onChange={(event) => onFieldChange('username', event.target.value)}
              data-testid="users-create-username"
              style={inputStyle}
            />
          </div>

          <div style={{ marginBottom: '16px' }}>
            <label style={{ display: 'block', marginBottom: '8px', fontWeight: '500' }}>{TEXT.password}</label>
            <input
              type="password"
              required
              value={newUser.password || ''}
              onChange={(event) => onFieldChange('password', event.target.value)}
              data-testid="users-create-password"
              style={inputStyle}
            />
          </div>

          <div style={{ marginBottom: '16px' }}>
            <label style={{ display: 'block', marginBottom: '8px', fontWeight: '500' }}>{TEXT.userType}</label>
            <select
              value={newUser.user_type || 'normal'}
              onChange={(event) => onFieldChange('user_type', event.target.value)}
              data-testid="users-create-user-type"
              style={{ ...inputStyle, backgroundColor: 'white' }}
            >
              <option value="normal">{TEXT.normalUser}</option>
              <option value="sub_admin">{TEXT.subAdmin}</option>
            </select>
          </div>

          <div style={{ marginBottom: '16px' }}>
            <label style={{ display: 'block', marginBottom: '8px', fontWeight: '500' }}>{TEXT.company}</label>
            <select
              required
              value={newUser.company_id || ''}
              onChange={(event) => onFieldChange('company_id', event.target.value)}
              data-testid="users-create-company"
              style={{ ...inputStyle, backgroundColor: 'white' }}
            >
              <option value="" disabled>
                {TEXT.companyPlaceholder}
              </option>
              {(Array.isArray(companies) ? companies : []).map((company) => (
                <option key={company.id} value={String(company.id)}>
                  {company.name}
                </option>
              ))}
            </select>
          </div>

          <div style={{ marginBottom: '16px' }}>
            <label style={{ display: 'block', marginBottom: '8px', fontWeight: '500' }}>{TEXT.department}</label>
            <select
              required
              value={newUser.department_id || ''}
              onChange={(event) => onFieldChange('department_id', event.target.value)}
              data-testid="users-create-department"
              style={{ ...inputStyle, backgroundColor: 'white' }}
            >
              <option value="" disabled>
                {TEXT.departmentPlaceholder}
              </option>
              {visibleDepartments.map((department) => (
                <option key={department.id} value={String(department.id)}>
                  {department.path_name || department.name}
                </option>
              ))}
            </select>
          </div>

          {!isSubAdmin ? (
            <div style={{ marginBottom: '16px' }}>
              <label style={{ display: 'block', marginBottom: '8px', fontWeight: '500' }}>{TEXT.ownerSubAdmin}</label>
              <select
                required
                value={newUser.manager_user_id || ''}
                onChange={(event) => onFieldChange('manager_user_id', event.target.value)}
                data-testid="users-create-sub-admin"
                style={{ ...inputStyle, backgroundColor: 'white' }}
              >
                <option value="" disabled>
                  {TEXT.ownerSubAdminPlaceholder}
                </option>
                {(Array.isArray(subAdminOptions) ? subAdminOptions : []).map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </div>
          ) : null}

          <div style={{ marginBottom: '16px' }}>
            <label style={{ display: 'block', marginBottom: '8px', fontWeight: '500' }}>{TEXT.maxSessions}</label>
            <input
              type="number"
              min={1}
              max={1000}
              required
              value={newUser.max_login_sessions}
              onChange={(event) => onFieldChange('max_login_sessions', event.target.value)}
              data-testid="users-create-max-login-sessions"
              style={inputStyle}
            />
          </div>

          <div style={{ marginBottom: '16px' }}>
            <label style={{ display: 'block', marginBottom: '8px', fontWeight: '500' }}>{TEXT.idleTimeout}</label>
            <input
              type="number"
              min={1}
              max={43200}
              required
              value={newUser.idle_timeout_minutes}
              onChange={(event) => onFieldChange('idle_timeout_minutes', event.target.value)}
              data-testid="users-create-idle-timeout"
              style={inputStyle}
            />
          </div>

          {!isSubAdmin ? (
            <div style={{ marginBottom: '24px' }}>
              <label style={{ display: 'block', marginBottom: '8px', fontWeight: '500' }}>{TEXT.permissionGroup}</label>
              <div
                style={{
                  border: '1px solid #d1d5db',
                  borderRadius: '4px',
                  padding: '12px',
                  backgroundColor: '#f9fafb',
                  color: '#6b7280',
                  fontSize: '0.9rem',
                }}
              >
                {TEXT.normalUserHint}
              </div>
            </div>
          ) : null}

          {isSubAdmin ? (
            <div style={{ marginBottom: '24px' }}>
              <label style={{ display: 'block', marginBottom: '8px', fontWeight: '500' }}>{TEXT.kbRoot}</label>
              <div style={{ marginBottom: '8px', color: '#6b7280', fontSize: '0.85rem' }}>{TEXT.kbRootHint}</div>
              <KnowledgeRootNodeSelector
                nodes={kbDirectoryNodes}
                selectedNodeId={newUser.managed_kb_root_node_id || ''}
                onSelect={(nodeId) => onFieldChange('managed_kb_root_node_id', nodeId)}
                disabled={false}
                loading={kbDirectoryLoading}
                error={kbDirectoryError}
                canCreateRoot={Boolean(newUser.company_id && onCreateRootDirectory)}
                creatingRoot={kbDirectoryCreatingRoot}
                createRootError={kbDirectoryCreateError}
                onCreateRoot={onCreateRootDirectory}
              />
            </div>
          ) : null}

          {orgDirectoryError ? (
            <div style={{ marginBottom: '16px', color: '#ef4444' }} data-testid="users-create-org-error">
              {orgDirectoryError}
            </div>
          ) : null}

          {error ? (
            <div style={{ marginBottom: '16px', color: '#ef4444' }} data-testid="users-create-error">
              {error}
            </div>
          ) : null}

          <div style={{ display: 'flex', gap: '12px', flexDirection: isMobile ? 'column' : 'row' }}>
            <button
              type="submit"
              data-testid="users-create-submit"
              style={{
                flex: 1,
                padding: '10px',
                backgroundColor: '#3b82f6',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer',
                width: isMobile ? '100%' : 'auto',
              }}
            >
              {TEXT.submit}
            </button>
            <button
              type="button"
              onClick={onCancel}
              data-testid="users-create-cancel"
              style={{
                flex: 1,
                padding: '10px',
                backgroundColor: '#6b7280',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer',
                width: isMobile ? '100%' : 'auto',
              }}
            >
              {TEXT.cancel}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
