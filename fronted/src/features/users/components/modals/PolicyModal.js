import React, { useEffect, useMemo, useState } from 'react';
import KnowledgeRootNodeSelector from '../KnowledgeRootNodeSelector';

const MOBILE_BREAKPOINT = 768;

const TEXT = {
  titlePrefix: '\u7528\u6237\u914d\u7f6e',
  baseInfo: '\u57fa\u7840\u4fe1\u606f',
  fullName: '\u59d3\u540d',
  company: '\u516c\u53f8',
  companyPlaceholder: '\u8bf7\u9009\u62e9\u516c\u53f8',
  department: '\u90e8\u95e8',
  departmentPlaceholder: '\u8bf7\u9009\u62e9\u90e8\u95e8',
  userType: '\u7528\u6237\u7c7b\u578b',
  admin: '\u7ba1\u7406\u5458',
  normalUser: '\u666e\u901a\u7528\u6237',
  subAdmin: '\u5b50\u7ba1\u7406\u5458',
  ownerSubAdmin: '\u5f52\u5c5e\u5b50\u7ba1\u7406\u5458',
  ownerSubAdminPlaceholder: '\u8bf7\u9009\u62e9\u5f52\u5c5e\u5b50\u7ba1\u7406\u5458',
  kbRoot: '\u77e5\u8bc6\u5e93\u8d1f\u8d23\u76ee\u5f55',
  kbRootHint:
    '\u8be5\u7528\u6237\u62e5\u6709\u6240\u9009\u76ee\u5f55\u53ca\u5176\u540e\u4ee3\u7684\u5168\u90e8\u77e5\u8bc6\u5e93\u7ba1\u7406\u6743\u9650\u3002',
  kbRootInvalid:
    '\u5f53\u524d\u8d1f\u8d23\u76ee\u5f55\u5df2\u5931\u6548\uff0c\u9700\u91cd\u65b0\u5728\u8be5\u516c\u53f8\u7684\u77e5\u8bc6\u5e93\u76ee\u5f55\u6811\u4e2d\u7ed1\u5b9a\u4e00\u4e2a\u6709\u6548\u76ee\u5f55\u3002',
  permissionGroup: '\u6743\u9650\u7ec4',
  permissionHint:
    '\u666e\u901a\u7528\u6237\u7684\u6743\u9650\u7ec4\u7531\u5f52\u5c5e\u5b50\u7ba1\u7406\u5458\u5206\u914d\uff0c\u7ba1\u7406\u5458\u5728\u6b64\u4e0d\u76f4\u63a5\u914d\u7f6e\u3002',
  subAdminPermissionHint:
    '\u53ef\u4e3a\u5b50\u7ba1\u7406\u5458\u914d\u7f6e\u53ef\u4f7f\u7528\u7684\u6743\u9650\u7ec4\uff0c\u5176\u4e2d\u7684\u5b9e\u7528\u5de5\u5177\u529f\u80fd\u4f1a\u6210\u4e3a\u5176\u5411\u4e0b\u5206\u914d\u7684\u4e0a\u9650\u3002',
  noPermissionGroups: '\u6682\u65e0\u53ef\u5206\u914d\u7684\u6743\u9650\u7ec4',
  selectedPermissionGroups: '\u5df2\u9009\u62e9',
  loginPolicy: '\u767b\u5f55\u7b56\u7565',
  maxSessions: '\u6700\u5927\u767b\u5f55\u4f1a\u8bdd\u6570 (1-1000)',
  idleTimeout: '\u7a7a\u95f2\u8d85\u65f6 (\u5206\u949f, 1-43200)',
  disablePasswordChange: '\u4e0d\u5141\u8bb8\u6b64\u7528\u6237\u4fee\u6539\u5bc6\u7801',
  disableAccount: '\u505c\u7528\u6b64\u8d26\u53f7',
  disableImmediate: '\u7acb\u5373',
  disableUntil: '\u5230\u671f\u65e5',
  cancel: '\u53d6\u6d88',
  save: '\u4fdd\u5b58',
  saving: '\u63d0\u4ea4\u4e2d...',
};

export default function PolicyModal({
  open,
  user,
  policyForm,
  companies,
  departments,
  policySubAdminOptions,
  availableGroups,
  kbDirectoryNodes,
  kbDirectoryLoading,
  kbDirectoryError,
  kbDirectoryCreateError,
  kbDirectoryCreatingRoot,
  managedKbRootInvalid,
  orgDirectoryError,
  policyError,
  policySubmitting,
  onChangePolicyForm,
  onToggleGroup,
  onCancel,
  onSave,
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
    padding: '10px 12px',
    border: '1px solid #d1d5db',
    borderRadius: '4px',
    boxSizing: 'border-box',
    backgroundColor: 'white',
  };

  const companyId = policyForm.company_id ? Number(policyForm.company_id) : null;
  const visibleDepartments = useMemo(() => {
    const items = Array.isArray(departments) ? departments : [];
    if (companyId == null) return items;
    return items.filter(
      (department) => department.company_id == null || Number(department.company_id) === companyId
    );
  }, [companyId, departments]);

  if (!open || !user) return null;

  const isBuiltInAdmin = String(user?.role || '') === 'admin';
  const isSubAdmin = String(policyForm.user_type || 'normal') === 'sub_admin';

  return (
    <div
      data-testid="users-policy-modal"
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
          maxWidth: '680px',
          maxHeight: isMobile ? '100%' : '90vh',
          overflowY: 'auto',
          margin: isMobile ? 'auto 0' : 0,
        }}
      >
        <h3 style={{ margin: '0 0 24px 0' }}>
          {TEXT.titlePrefix} - {user.full_name || user.username}
        </h3>

        <div style={{ marginBottom: 24 }}>
          <div style={{ fontWeight: 700, marginBottom: 12, color: '#111827' }}>{TEXT.baseInfo}</div>

          <div style={{ marginBottom: 16 }}>
            <label style={{ display: 'block', marginBottom: 8, fontWeight: 500 }}>{TEXT.fullName}</label>
            <input
              type="text"
              value={policyForm.full_name || ''}
              onChange={(event) => onChangePolicyForm({ ...policyForm, full_name: event.target.value })}
              data-testid="users-policy-full-name"
              style={inputStyle}
            />
          </div>

          <div style={{ marginBottom: 16 }}>
            <label style={{ display: 'block', marginBottom: 8, fontWeight: 500 }}>{TEXT.company}</label>
            <select
              value={policyForm.company_id || ''}
              onChange={(event) =>
                onChangePolicyForm({ ...policyForm, company_id: event.target.value, department_id: '' })
              }
              data-testid="users-policy-company"
              style={inputStyle}
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

          <div style={{ marginBottom: 16 }}>
            <label style={{ display: 'block', marginBottom: 8, fontWeight: 500 }}>{TEXT.department}</label>
            <select
              value={policyForm.department_id || ''}
              onChange={(event) => onChangePolicyForm({ ...policyForm, department_id: event.target.value })}
              data-testid="users-policy-department"
              style={inputStyle}
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

          <div style={{ marginBottom: 16 }}>
            <label style={{ display: 'block', marginBottom: 8, fontWeight: 500 }}>{TEXT.userType}</label>
            {isBuiltInAdmin ? (
              <div
                data-testid="users-policy-role-admin-readonly"
                style={{
                  ...inputStyle,
                  color: '#6b7280',
                  backgroundColor: '#f9fafb',
                }}
              >
                {TEXT.admin}
              </div>
            ) : (
              <select
                value={policyForm.user_type || 'normal'}
                onChange={(event) => onChangePolicyForm({ ...policyForm, user_type: event.target.value })}
                data-testid="users-policy-user-type"
                style={inputStyle}
              >
                <option value="normal">{TEXT.normalUser}</option>
                <option value="sub_admin">{TEXT.subAdmin}</option>
              </select>
            )}
          </div>

          {!isSubAdmin && !isBuiltInAdmin ? (
            <div style={{ marginBottom: 16 }}>
              <label style={{ display: 'block', marginBottom: 8, fontWeight: 500 }}>{TEXT.ownerSubAdmin}</label>
              <select
                value={policyForm.manager_user_id || ''}
                onChange={(event) => onChangePolicyForm({ ...policyForm, manager_user_id: event.target.value })}
                data-testid="users-policy-sub-admin"
                style={inputStyle}
              >
                <option value="" disabled>
                  {TEXT.ownerSubAdminPlaceholder}
                </option>
                {(Array.isArray(policySubAdminOptions) ? policySubAdminOptions : []).map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </div>
          ) : null}

          {isSubAdmin ? (
            <div style={{ marginBottom: 16 }}>
              <label style={{ display: 'block', marginBottom: 8, fontWeight: 500 }}>{TEXT.kbRoot}</label>
              <div style={{ marginBottom: '8px', color: '#6b7280', fontSize: '0.85rem' }}>{TEXT.kbRootHint}</div>
              {managedKbRootInvalid ? (
                <div
                  style={{
                    marginBottom: 10,
                    padding: '10px 12px',
                    borderRadius: 8,
                    backgroundColor: '#fff7ed',
                    color: '#c2410c',
                    fontSize: '0.85rem',
                    border: '1px solid #fdba74',
                  }}
                  data-testid="users-policy-invalid-kb-root"
                >
                  {TEXT.kbRootInvalid}
                </div>
              ) : null}
              <KnowledgeRootNodeSelector
                nodes={kbDirectoryNodes}
                selectedNodeId={policyForm.managed_kb_root_node_id || ''}
                onSelect={(nodeId) => onChangePolicyForm({ ...policyForm, managed_kb_root_node_id: nodeId })}
                disabled={false}
                loading={kbDirectoryLoading}
                error={kbDirectoryError}
                canCreateRoot={Boolean(policyForm.company_id && onCreateRootDirectory)}
                creatingRoot={kbDirectoryCreatingRoot}
                createRootError={kbDirectoryCreateError}
                onCreateRoot={onCreateRootDirectory}
              />
            </div>
          ) : null}

          {isSubAdmin && !isBuiltInAdmin ? (
            <div style={{ marginBottom: 16 }}>
              <label style={{ display: 'block', marginBottom: 8, fontWeight: 500 }}>{TEXT.permissionGroup}</label>
              <div style={{ marginBottom: '8px', color: '#6b7280', fontSize: '0.85rem' }}>{TEXT.subAdminPermissionHint}</div>
              <div
                style={{
                  border: '1px solid #d1d5db',
                  borderRadius: 8,
                  padding: 12,
                  backgroundColor: '#f9fafb',
                  maxHeight: isMobile ? '220px' : '260px',
                  overflowY: 'auto',
                }}
              >
                {(Array.isArray(availableGroups) ? availableGroups : []).length === 0 ? (
                  <div style={{ color: '#6b7280', textAlign: 'center', padding: '8px 0' }}>{TEXT.noPermissionGroups}</div>
                ) : (
                  (Array.isArray(availableGroups) ? availableGroups : []).map((group) => (
                    <label
                      key={group.group_id}
                      style={{ display: 'flex', alignItems: 'flex-start', gap: 8, padding: '8px 0', cursor: 'pointer' }}
                    >
                      <input
                        type="checkbox"
                        data-testid={`users-policy-group-${group.group_id}`}
                        checked={(policyForm.group_ids || []).includes(group.group_id)}
                        onChange={(event) => onToggleGroup?.(group.group_id, event.target.checked)}
                      />
                      <div>
                        <div style={{ fontWeight: 500, color: '#111827' }}>{group.group_name}</div>
                        {group.description ? (
                          <div style={{ fontSize: '0.85rem', color: '#6b7280' }}>{group.description}</div>
                        ) : null}
                      </div>
                    </label>
                  ))
                )}
              </div>
              {(policyForm.group_ids || []).length > 0 ? (
                <div style={{ marginTop: '8px', color: '#6b7280', fontSize: '0.85rem' }}>
                  {TEXT.selectedPermissionGroups} {(policyForm.group_ids || []).length} 个权限组
                </div>
              ) : null}
            </div>
          ) : null}

          {!isSubAdmin && !isBuiltInAdmin ? (
            <div style={{ marginBottom: 8 }}>
              <label style={{ display: 'block', marginBottom: 8, fontWeight: 500 }}>{TEXT.permissionGroup}</label>
              <div
                style={{
                  border: '1px solid #d1d5db',
                  borderRadius: 8,
                  padding: 12,
                  backgroundColor: '#f9fafb',
                  color: '#6b7280',
                }}
              >
                {TEXT.permissionHint}
              </div>
            </div>
          ) : null}
        </div>

        <div style={{ marginBottom: 24 }}>
          <div style={{ fontWeight: 700, marginBottom: 12, color: '#111827' }}>{TEXT.loginPolicy}</div>

          <div style={{ marginBottom: 16 }}>
            <label style={{ display: 'block', marginBottom: 8, fontWeight: 500 }}>{TEXT.maxSessions}</label>
            <input
              type="number"
              min={1}
              max={1000}
              value={policyForm.max_login_sessions}
              onChange={(event) => onChangePolicyForm({ ...policyForm, max_login_sessions: event.target.value })}
              data-testid="users-policy-max-login-sessions"
              style={inputStyle}
            />
          </div>

          <div style={{ marginBottom: 16 }}>
            <label style={{ display: 'block', marginBottom: 8, fontWeight: 500 }}>{TEXT.idleTimeout}</label>
            <input
              type="number"
              min={1}
              max={43200}
              value={policyForm.idle_timeout_minutes}
              onChange={(event) => onChangePolicyForm({ ...policyForm, idle_timeout_minutes: event.target.value })}
              data-testid="users-policy-idle-timeout"
              style={inputStyle}
            />
          </div>

          <div style={{ marginBottom: 12 }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer' }}>
              <input
                type="checkbox"
                data-testid="users-policy-can-change-password"
                checked={policyForm.can_change_password === false}
                onChange={(event) =>
                  onChangePolicyForm({ ...policyForm, can_change_password: !event.target.checked })
                }
              />
              {TEXT.disablePasswordChange}
            </label>
          </div>

          <div style={{ marginBottom: 16, padding: 12, border: '1px solid #e5e7eb', borderRadius: 8 }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer', marginBottom: 10 }}>
              <input
                type="checkbox"
                data-testid="users-policy-disable-account-enabled"
                checked={!!policyForm.disable_account}
                onChange={(event) =>
                  onChangePolicyForm({ ...policyForm, disable_account: event.target.checked })
                }
              />
              {TEXT.disableAccount}
            </label>

            {policyForm.disable_account ? (
              <>
                <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 10 }}>
                  <label style={{ display: 'flex', alignItems: 'center', gap: 6, cursor: 'pointer' }}>
                    <input
                      type="radio"
                      name="users-policy-disable-mode"
                      value="immediate"
                      data-testid="users-policy-disable-mode-immediate"
                      checked={policyForm.disable_mode !== 'until'}
                      onChange={() => onChangePolicyForm({ ...policyForm, disable_mode: 'immediate' })}
                    />
                    {TEXT.disableImmediate}
                  </label>
                  <label style={{ display: 'flex', alignItems: 'center', gap: 6, cursor: 'pointer' }}>
                    <input
                      type="radio"
                      name="users-policy-disable-mode"
                      value="until"
                      data-testid="users-policy-disable-mode-until"
                      checked={policyForm.disable_mode === 'until'}
                      onChange={() => onChangePolicyForm({ ...policyForm, disable_mode: 'until' })}
                    />
                    {TEXT.disableUntil}
                  </label>
                </div>

                {policyForm.disable_mode === 'until' ? (
                  <input
                    type="date"
                    data-testid="users-policy-disable-until-date"
                    value={policyForm.disable_until_date || ''}
                    onChange={(event) =>
                      onChangePolicyForm({ ...policyForm, disable_until_date: event.target.value })
                    }
                    style={inputStyle}
                  />
                ) : null}
              </>
            ) : null}
          </div>
        </div>

        {orgDirectoryError ? (
          <div style={{ marginBottom: 16, color: '#ef4444' }} data-testid="users-policy-org-error">
            {orgDirectoryError}
          </div>
        ) : null}

        {policyError ? (
          <div style={{ marginBottom: 16, color: '#ef4444' }} data-testid="users-policy-error">
            {policyError}
          </div>
        ) : null}

        <div style={{ display: 'flex', gap: 12, flexDirection: isMobile ? 'column' : 'row' }}>
          <button
            type="button"
            onClick={onCancel}
            disabled={policySubmitting}
            data-testid="users-policy-cancel"
            style={{
              flex: 1,
              padding: '10px',
              backgroundColor: '#6b7280',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: policySubmitting ? 'not-allowed' : 'pointer',
            }}
          >
            {TEXT.cancel}
          </button>
          <button
            type="button"
            onClick={onSave}
            disabled={policySubmitting}
            data-testid="users-policy-save"
            style={{
              flex: 1,
              padding: '10px',
              backgroundColor: policySubmitting ? '#7dd3fc' : '#0ea5e9',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: policySubmitting ? 'not-allowed' : 'pointer',
            }}
          >
            {policySubmitting ? TEXT.saving : TEXT.save}
          </button>
        </div>
      </div>
    </div>
  );
}
