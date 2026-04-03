import React, { useEffect, useMemo, useState } from 'react';
import KnowledgeRootNodeSelector from '../KnowledgeRootNodeSelector';

const MOBILE_BREAKPOINT = 768;

export default function PolicyModal({
  open,
  user,
  policyForm,
  managerOptions,
  availableGroups,
  companies,
  departments,
  kbDirectoryNodes,
  kbDirectoryLoading,
  kbDirectoryError,
  policyError,
  policySubmitting,
  onChangePolicyForm,
  onTogglePolicyGroup,
  onCancel,
  onSave,
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

  const filteredManagerOptions = useMemo(() => {
    return (Array.isArray(managerOptions) ? managerOptions : []).filter((item) => {
      if (String(item.value || '') === String(user?.user_id || '')) return false;
      if (companyId === null) return true;
      return item.company_id === companyId;
    });
  }, [companyId, managerOptions, user?.user_id]);

  const visibleDepartments = useMemo(() => {
    return companyId == null
      ? departments
      : (Array.isArray(departments) ? departments : []).filter(
          (department) => department.company_id == null || department.company_id === companyId
        );
  }, [companyId, departments]);

  if (!open || !user) return null;

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
        <h3 style={{ margin: '0 0 24px 0' }}>用户配置 - {user.username}</h3>

        <div style={{ marginBottom: 24 }}>
          <div style={{ fontWeight: 700, marginBottom: 12, color: '#111827' }}>基础信息</div>

          <div style={{ marginBottom: 16 }}>
            <label style={{ display: 'block', marginBottom: 8, fontWeight: 500 }}>姓名</label>
            <input
              type="text"
              value={policyForm.full_name || ''}
              onChange={(e) => onChangePolicyForm({ ...policyForm, full_name: e.target.value })}
              data-testid="users-policy-full-name"
              style={inputStyle}
            />
          </div>

          <div style={{ marginBottom: 16 }}>
            <label style={{ display: 'block', marginBottom: 8, fontWeight: 500 }}>邮箱</label>
            <input
              type="text"
              value={policyForm.email || ''}
              onChange={(e) => onChangePolicyForm({ ...policyForm, email: e.target.value })}
              data-testid="users-policy-email"
              style={inputStyle}
            />
          </div>

          <div style={{ marginBottom: 16 }}>
            <label style={{ display: 'block', marginBottom: 8, fontWeight: 500 }}>公司</label>
            <select
              value={policyForm.company_id || ''}
              onChange={(e) => onChangePolicyForm({ ...policyForm, company_id: e.target.value, department_id: '' })}
              data-testid="users-policy-company"
              style={inputStyle}
            >
              <option value="" disabled>
                请选择公司
              </option>
              {(Array.isArray(companies) ? companies : []).map((company) => (
                <option key={company.id} value={String(company.id)}>
                  {company.name}
                </option>
              ))}
            </select>
          </div>

          <div style={{ marginBottom: 16 }}>
            <label style={{ display: 'block', marginBottom: 8, fontWeight: 500 }}>部门</label>
            <select
              value={policyForm.department_id || ''}
              onChange={(e) => onChangePolicyForm({ ...policyForm, department_id: e.target.value })}
              data-testid="users-policy-department"
              style={inputStyle}
            >
              <option value="" disabled>
                请选择部门
              </option>
              {visibleDepartments.map((department) => (
                <option key={department.id} value={String(department.id)}>
                  {department.path_name || department.name}
                </option>
              ))}
            </select>
          </div>

          <div style={{ marginBottom: 16 }}>
            <label style={{ display: 'block', marginBottom: 8, fontWeight: 500 }}>直属主管</label>
            <select
              value={policyForm.manager_user_id || ''}
              onChange={(e) => onChangePolicyForm({ ...policyForm, manager_user_id: e.target.value })}
              data-testid="users-policy-manager"
              style={inputStyle}
            >
              <option value="">无</option>
              {filteredManagerOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>

          <div style={{ marginBottom: 16 }}>
            <label style={{ display: 'block', marginBottom: 8, fontWeight: 500 }}>角色</label>
            <select
              value={policyForm.role || 'viewer'}
              onChange={(e) => onChangePolicyForm({ ...policyForm, role: e.target.value, managed_kb_root_node_id: '' })}
              data-testid="users-policy-role"
              style={inputStyle}
            >
              <option value="viewer">普通查看者</option>
              <option value="operator">操作员</option>
              <option value="reviewer">审核员</option>
              <option value="guest">访客</option>
              <option value="sub_admin">子管理员</option>
              <option value="admin">管理员</option>
            </select>
          </div>

          {String(policyForm.role || '') === 'sub_admin' ? (
            <div style={{ marginBottom: 16 }}>
              <label style={{ display: 'block', marginBottom: 8, fontWeight: 500 }}>知识库负责目录</label>
              <div style={{ marginBottom: '8px', color: '#6b7280', fontSize: '0.85rem' }}>
                子管理员只能管理该目录及其后代。
              </div>
              <KnowledgeRootNodeSelector
                nodes={kbDirectoryNodes}
                selectedNodeId={policyForm.managed_kb_root_node_id || ''}
                onSelect={(nodeId) => onChangePolicyForm({ ...policyForm, managed_kb_root_node_id: nodeId })}
                disabled={false}
                loading={kbDirectoryLoading}
                error={kbDirectoryError}
              />
            </div>
          ) : null}

          <div style={{ marginBottom: 8 }}>
            <label style={{ display: 'block', marginBottom: 8, fontWeight: 500 }}>权限组</label>
            <div
              style={{
                border: '1px solid #d1d5db',
                borderRadius: 8,
                padding: 12,
                maxHeight: 220,
                overflowY: 'auto',
                backgroundColor: '#f9fafb',
              }}
            >
              {(Array.isArray(availableGroups) ? availableGroups : []).length === 0 ? (
                <div style={{ color: '#6b7280', textAlign: 'center' }}>暂无可用权限组</div>
              ) : (
                availableGroups.map((group) => (
                  <label
                    key={group.group_id}
                    style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '8px 0', cursor: 'pointer' }}
                  >
                    <input
                      type="checkbox"
                      checked={policyForm.group_ids?.includes(group.group_id) || false}
                      onChange={(e) => onTogglePolicyGroup(group.group_id, e.target.checked)}
                      data-testid={`users-policy-group-${group.group_id}`}
                    />
                    <div>
                      <div style={{ fontWeight: 500 }}>{group.group_name}</div>
                      {group.description ? (
                        <div style={{ color: '#6b7280', fontSize: '0.84rem' }}>{group.description}</div>
                      ) : null}
                    </div>
                  </label>
                ))
              )}
            </div>
          </div>
        </div>

        <div style={{ marginBottom: 24 }}>
          <div style={{ fontWeight: 700, marginBottom: 12, color: '#111827' }}>登录策略</div>

          <div style={{ marginBottom: 16 }}>
            <label style={{ display: 'block', marginBottom: 8, fontWeight: 500 }}>最大登录会话数 (1-1000)</label>
            <input
              type="number"
              min={1}
              max={1000}
              value={policyForm.max_login_sessions}
              onChange={(e) => onChangePolicyForm({ ...policyForm, max_login_sessions: e.target.value })}
              data-testid="users-policy-max-login-sessions"
              style={inputStyle}
            />
          </div>

          <div style={{ marginBottom: 16 }}>
            <label style={{ display: 'block', marginBottom: 8, fontWeight: 500 }}>空闲超时 (分钟, 1-43200)</label>
            <input
              type="number"
              min={1}
              max={43200}
              value={policyForm.idle_timeout_minutes}
              onChange={(e) => onChangePolicyForm({ ...policyForm, idle_timeout_minutes: e.target.value })}
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
                onChange={(e) => onChangePolicyForm({ ...policyForm, can_change_password: !e.target.checked })}
              />
              不允许此用户修改密码
            </label>
          </div>

          <div style={{ marginBottom: 16, padding: 12, border: '1px solid #e5e7eb', borderRadius: 8 }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer', marginBottom: 10 }}>
              <input
                type="checkbox"
                data-testid="users-policy-disable-account-enabled"
                checked={!!policyForm.disable_account}
                onChange={(e) => onChangePolicyForm({ ...policyForm, disable_account: e.target.checked })}
              />
              停用此账户
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
                    立即
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
                    到期日
                  </label>
                </div>

                {policyForm.disable_mode === 'until' ? (
                  <input
                    type="date"
                    data-testid="users-policy-disable-until-date"
                    value={policyForm.disable_until_date || ''}
                    onChange={(e) => onChangePolicyForm({ ...policyForm, disable_until_date: e.target.value })}
                    style={inputStyle}
                  />
                ) : null}
              </>
            ) : null}
          </div>
        </div>

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
            取消
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
            {policySubmitting ? '提交中...' : '保存'}
          </button>
        </div>
      </div>
    </div>
  );
}
