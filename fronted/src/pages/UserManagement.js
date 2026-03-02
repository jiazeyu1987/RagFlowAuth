import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useAuth } from '../hooks/useAuth';
import { permissionGroupsApi } from '../features/permissionGroups/api';
import { usersApi } from '../features/users/api';
import { orgDirectoryApi } from '../features/orgDirectory/api';

const DEFAULT_FILTERS = {
  q: '',
  company_id: '',
  department_id: '',
  status: '',
  group_id: '',
  created_from: '',
  created_to: '',
};

const UserManagement = () => {
  const { can } = useAuth();
  const [allUsers, setAllUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [canManageUsers, setCanManageUsers] = useState(false);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newUser, setNewUser] = useState({
    username: '',
    password: '',
    email: '',
    company_id: '',
    department_id: '',
    group_ids: [],
    max_login_sessions: 3,
    idle_timeout_minutes: 120,
  });

  const [filters, setFilters] = useState(DEFAULT_FILTERS);

  const [availableGroups, setAvailableGroups] = useState([]);
  const [editingGroupUser, setEditingGroupUser] = useState(null);
  const [showGroupModal, setShowGroupModal] = useState(false);
  const [selectedGroupIds, setSelectedGroupIds] = useState([]);

  const [showResetPasswordModal, setShowResetPasswordModal] = useState(false);
  const [resetPasswordUser, setResetPasswordUser] = useState(null);
  const [resetPasswordValue, setResetPasswordValue] = useState('');
  const [resetPasswordConfirm, setResetPasswordConfirm] = useState('');
  const [resetPasswordSubmitting, setResetPasswordSubmitting] = useState(false);
  const [resetPasswordError, setResetPasswordError] = useState(null);

  const [showPolicyModal, setShowPolicyModal] = useState(false);
  const [policyUser, setPolicyUser] = useState(null);
  const [policySubmitting, setPolicySubmitting] = useState(false);
  const [policyError, setPolicyError] = useState(null);
  const [policyForm, setPolicyForm] = useState({
    max_login_sessions: 3,
    idle_timeout_minutes: 120,
  });

  const [companies, setCompanies] = useState([]);
  const [departments, setDepartments] = useState([]);

  useEffect(() => {
    setCanManageUsers(can('users', 'manage'));
  }, [can]);

  const buildListParams = useCallback((f) => {
    const params = {};

    if (f.q && f.q.trim()) params.q = f.q.trim();
    if (f.company_id) params.company_id = String(f.company_id);
    if (f.department_id) params.department_id = String(f.department_id);
    if (f.status) params.status = f.status;
    if (f.group_id) params.group_id = String(f.group_id);

    if (f.created_from) {
      const fromMs = new Date(`${f.created_from}T00:00:00`).getTime();
      if (!Number.isNaN(fromMs)) params.created_from_ms = String(fromMs);
    }
    if (f.created_to) {
      const toMs = new Date(`${f.created_to}T23:59:59.999`).getTime();
      if (!Number.isNaN(toMs)) params.created_to_ms = String(toMs);
    }

    params.limit = '2000';

    return params;
  }, []);

  const fetchUsers = useCallback(async () => {
    try {
      setLoading(true);
      const data = await usersApi.list(buildListParams(DEFAULT_FILTERS));
      setAllUsers(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [buildListParams]);

  const fetchPermissionGroups = useCallback(async () => {
    try {
      const data = await permissionGroupsApi.list();
      if (data.ok) {
        setAvailableGroups(data.data || []);
      }
    } catch (err) {
      console.error('Failed to load permission groups:', err);
    }
  }, []);

  const fetchOrgDirectory = useCallback(async () => {
    try {
      const [companyList, deptList] = await Promise.all([
        orgDirectoryApi.listCompanies(),
        orgDirectoryApi.listDepartments(),
      ]);
      setCompanies(Array.isArray(companyList) ? companyList : []);
      setDepartments(Array.isArray(deptList) ? deptList : []);
    } catch (err) {
      console.error('Failed to load org directory:', err);
    }
  }, []);

  useEffect(() => {
    fetchUsers();
    fetchPermissionGroups();
    fetchOrgDirectory();
  }, [fetchOrgDirectory, fetchPermissionGroups, fetchUsers]);

  const filteredUsers = useMemo(() => {
    const q = (filters.q || '').trim();
    const companyId = filters.company_id ? Number(filters.company_id) : null;
    const departmentId = filters.department_id ? Number(filters.department_id) : null;
    const status = filters.status || '';
    const groupId = filters.group_id ? Number(filters.group_id) : null;

    let fromMs = null;
    let toMs = null;
    if (filters.created_from) {
      const ms = new Date(`${filters.created_from}T00:00:00`).getTime();
      fromMs = Number.isNaN(ms) ? null : ms;
    }
    if (filters.created_to) {
      const ms = new Date(`${filters.created_to}T23:59:59.999`).getTime();
      toMs = Number.isNaN(ms) ? null : ms;
    }

    return (allUsers || []).filter((u) => {
      if (q && !(u.username || '').includes(q)) return false;
      if (companyId != null && u.company_id !== companyId) return false;
      if (departmentId != null && u.department_id !== departmentId) return false;
      if (status && u.status !== status) return false;
      if (groupId != null) {
        const gids = u.group_ids || (u.permission_groups || []).map((pg) => pg.group_id);
        if (!Array.isArray(gids) || !gids.includes(groupId)) return false;
      }
      if (fromMs != null && (u.created_at_ms || 0) < fromMs) return false;
      if (toMs != null && (u.created_at_ms || 0) > toMs) return false;
      return true;
    });
  }, [allUsers, filters]);

  const groupedUsers = useMemo(() => {
    const groups = new Map();
    (filteredUsers || []).forEach((user) => {
      const key = user.department_id != null ? String(user.department_id) : '__unassigned__';
      const departmentName = user.department_name || '\u672a\u5206\u914d\u90e8\u95e8';
      if (!groups.has(key)) {
        groups.set(key, {
          key,
          departmentId: user.department_id ?? null,
          departmentName,
          users: [],
        });
      }
      groups.get(key).users.push(user);
    });

    return Array.from(groups.values()).sort((a, b) => {
      if (a.departmentName === '\u672a\u5206\u914d\u90e8\u95e8') return 1;
      if (b.departmentName === '\u672a\u5206\u914d\u90e8\u95e8') return -1;
      return a.departmentName.localeCompare(b.departmentName, 'zh-CN');
    });
  }, [filteredUsers]);

  const handleCreateUser = async (e) => {
    e.preventDefault();
    try {
      const payload = {
        ...newUser,
        company_id: newUser.company_id ? Number(newUser.company_id) : null,
        department_id: newUser.department_id ? Number(newUser.department_id) : null,
        max_login_sessions: Number(newUser.max_login_sessions),
        idle_timeout_minutes: Number(newUser.idle_timeout_minutes),
      };
      await usersApi.create(payload);
      setShowCreateModal(false);
      setNewUser({
        username: '',
        password: '',
        email: '',
        company_id: '',
        department_id: '',
        group_ids: [],
        max_login_sessions: 3,
        idle_timeout_minutes: 120,
      });
      fetchUsers();
    } catch (err) {
      setError(err.message);
    }
  };

  const handleDeleteUser = async (userId) => {
    if (!window.confirm('\u786e\u5b9a\u8981\u5220\u9664\u8be5\u7528\u6237\u5417\uff1f')) return;

    try {
      await usersApi.remove(userId);
      fetchUsers();
    } catch (err) {
      setError(err.message);
    }
  };

  const handleOpenResetPassword = (user) => {
    setResetPasswordUser(user);
    setResetPasswordValue('');
    setResetPasswordConfirm('');
    setResetPasswordError(null);
    setShowResetPasswordModal(true);
  };

  const handleCloseResetPassword = () => {
    setShowResetPasswordModal(false);
    setResetPasswordUser(null);
    setResetPasswordValue('');
    setResetPasswordConfirm('');
    setResetPasswordError(null);
  };

  const handleSubmitResetPassword = async () => {
    if (!resetPasswordUser) return;
    setResetPasswordError(null);

    if (!resetPasswordValue) {
      setResetPasswordError('\u8bf7\u8f93\u5165\u65b0\u5bc6\u7801');
      return;
    }
    if (resetPasswordValue !== resetPasswordConfirm) {
      setResetPasswordError('\u4e24\u6b21\u8f93\u5165\u7684\u65b0\u5bc6\u7801\u4e0d\u4e00\u81f4');
      return;
    }

    try {
      setResetPasswordSubmitting(true);
      await usersApi.resetPassword(resetPasswordUser.user_id, resetPasswordValue);
      handleCloseResetPassword();
    } catch (err) {
      setResetPasswordError(err.message || '\u4fee\u6539\u5bc6\u7801\u5931\u8d25');
    } finally {
      setResetPasswordSubmitting(false);
    }
  };

  const handleOpenPolicyModal = (user) => {
    setPolicyUser(user);
    setPolicyError(null);
    setPolicyForm({
      max_login_sessions: Number(user.max_login_sessions || 3),
      idle_timeout_minutes: Number(user.idle_timeout_minutes || 120),
    });
    setShowPolicyModal(true);
  };

  const handleClosePolicyModal = () => {
    setShowPolicyModal(false);
    setPolicyUser(null);
    setPolicySubmitting(false);
    setPolicyError(null);
    setPolicyForm({
      max_login_sessions: 3,
      idle_timeout_minutes: 120,
    });
  };

  const handleSavePolicy = async () => {
    if (!policyUser) return;
    setPolicyError(null);

    const maxSessions = Number(policyForm.max_login_sessions);
    const idleMinutes = Number(policyForm.idle_timeout_minutes);

    if (!Number.isInteger(maxSessions) || maxSessions < 1 || maxSessions > 1000) {
      setPolicyError('\u53ef\u767b\u5f55\u4e2a\u6570\u9700\u4e3a 1-1000 \u7684\u6574\u6570');
      return;
    }
    if (!Number.isInteger(idleMinutes) || idleMinutes < 1 || idleMinutes > 43200) {
      setPolicyError('\u95f2\u7f6e\u8d85\u65f6\u9700\u4e3a 1-43200 \u5206\u949f\u7684\u6574\u6570');
      return;
    }

    try {
      setPolicySubmitting(true);
      await usersApi.update(policyUser.user_id, {
        max_login_sessions: maxSessions,
        idle_timeout_minutes: idleMinutes,
      });
      handleClosePolicyModal();
      fetchUsers();
    } catch (err) {
      setPolicyError(err.message || '\u4fdd\u5b58\u767b\u5f55\u7b56\u7565\u5931\u8d25');
    } finally {
      setPolicySubmitting(false);
    }
  };

  const handleAssignGroup = async (user) => {
    try {
      setEditingGroupUser(user);
      const groupIds = user.group_ids || (user.permission_groups || []).map(pg => pg.group_id);
      setSelectedGroupIds(groupIds);
      setShowGroupModal(true);
    } catch (err) {
      setError(err.message);
    }
  };

  const handleSaveGroup = async () => {
    try {
      await usersApi.update(editingGroupUser.user_id, {
        group_ids: selectedGroupIds
      });
      setShowGroupModal(false);
      setEditingGroupUser(null);
      setSelectedGroupIds([]);
      fetchUsers();
    } catch (err) {
      setError(err.message);
    }
  };

  const handleCloseGroupModal = () => {
    setShowGroupModal(false);
    setEditingGroupUser(null);
    setSelectedGroupIds([]);
  };

  if (loading) return <div>Loading...</div>;
  if (error) return <div>Error: {error}</div>;

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <h2 style={{ margin: 0 }}>{'\u7528\u6237\u7ba1\u7406'}</h2>
        {canManageUsers && (
          <button
            onClick={() => setShowCreateModal(true)}
            data-testid="users-create-open"
            style={{
              padding: '10px 20px',
              backgroundColor: '#3b82f6',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
            }}
          >
            {'\u65b0\u5efa\u7528\u6237'}
          </button>
        )}
      </div>

      <div style={{
        backgroundColor: 'white',
        borderRadius: '8px',
        boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
        padding: '16px',
        marginBottom: '16px',
      }}>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '12px', alignItems: 'flex-end' }}>
          <div style={{ minWidth: '220px' }}>
            <label style={{ display: 'block', marginBottom: '6px', fontWeight: 500 }}>{'\u641c\u7d22\u7528\u6237\u540d'}</label>
            <input
              value={filters.q}
              placeholder={'\u652f\u6301\u6a21\u7cca\u641c\u7d22'}
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
            <label style={{ display: 'block', marginBottom: '6px', fontWeight: 500 }}>{'\u516c\u53f8'}</label>
            <select
              value={filters.company_id}
              onChange={(e) => setFilters({ ...filters, company_id: e.target.value })}
              data-testid="users-filter-company"
              style={{ width: '100%', padding: '8px', border: '1px solid #d1d5db', borderRadius: '6px' }}
            >
              <option value="">{'\u5168\u90e8'}</option>
              {companies.map((c) => (
                <option key={c.id} value={String(c.id)}>{c.name}</option>
              ))}
            </select>
          </div>

          <div style={{ minWidth: '180px' }}>
            <label style={{ display: 'block', marginBottom: '6px', fontWeight: 500 }}>{'\u90e8\u95e8'}</label>
            <select
              value={filters.department_id}
              onChange={(e) => setFilters({ ...filters, department_id: e.target.value })}
              data-testid="users-filter-department"
              style={{ width: '100%', padding: '8px', border: '1px solid #d1d5db', borderRadius: '6px' }}
            >
              <option value="">{'\u5168\u90e8'}</option>
              {departments.map((d) => (
                <option key={d.id} value={String(d.id)}>{d.name}</option>
              ))}
            </select>
          </div>

          <div style={{ minWidth: '140px' }}>
            <label style={{ display: 'block', marginBottom: '6px', fontWeight: 500 }}>{'\u72b6\u6001'}</label>
            <select
              value={filters.status}
              onChange={(e) => setFilters({ ...filters, status: e.target.value })}
              data-testid="users-filter-status"
              style={{ width: '100%', padding: '8px', border: '1px solid #d1d5db', borderRadius: '6px' }}
            >
              <option value="">{'\u5168\u90e8'}</option>
              <option value="active">{'\u6fc0\u6d3b'}</option>
              <option value="inactive">{'\u505c\u7528'}</option>
            </select>
          </div>

          <div style={{ minWidth: '180px' }}>
            <label style={{ display: 'block', marginBottom: '6px', fontWeight: 500 }}>{'\u6743\u9650\u7ec4'}</label>
            <select
              value={filters.group_id}
              onChange={(e) => setFilters({ ...filters, group_id: e.target.value })}
              data-testid="users-filter-group"
              style={{ width: '100%', padding: '8px', border: '1px solid #d1d5db', borderRadius: '6px' }}
            >
              <option value="">{'\u5168\u90e8'}</option>
              {availableGroups.map((g) => (
                <option key={g.group_id} value={String(g.group_id)}>{g.group_name}</option>
              ))}
            </select>
          </div>

          <div>
            <label style={{ display: 'block', marginBottom: '6px', fontWeight: 500 }}>{'\u521b\u5efa\u65f6\u95f4(\u4ece)'}</label>
            <input
              type="date"
              value={filters.created_from}
              onChange={(e) => setFilters({ ...filters, created_from: e.target.value })}
              data-testid="users-filter-created-from"
              style={{ padding: '8px', border: '1px solid #d1d5db', borderRadius: '6px' }}
            />
          </div>

          <div>
            <label style={{ display: 'block', marginBottom: '6px', fontWeight: 500 }}>{'\u521b\u5efa\u65f6\u95f4(\u5230)'}</label>
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
            onClick={() => {
              setFilters(DEFAULT_FILTERS);
            }}
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
            {'\u91cd\u7f6e'}
          </button>
        </div>
      </div>

      <div style={{
        backgroundColor: 'white',
        borderRadius: '8px',
        boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
        padding: '16px',
        marginBottom: '16px',
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px', gap: '12px', flexWrap: 'wrap' }}>
          <div>
            <div style={{ fontSize: '1rem', fontWeight: 600, color: '#111827' }}>{'\u6309\u90e8\u95e8\u5212\u5206'}</div>
            <div style={{ fontSize: '0.9rem', color: '#6b7280' }}>
              {'\u5f53\u524d\u7b5b\u9009\u7ed3\u679c\u5171'} {filteredUsers.length} {'\u4e2a\u7528\u6237\uff0c\u5206\u5e03\u5728'} {groupedUsers.length} {'\u4e2a\u90e8\u95e8\u4e2d'}
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
              }}
            >
              {'\u6e05\u9664\u90e8\u95e8\u7b5b\u9009'}
            </button>
          )}
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '12px' }}>
          {groupedUsers.map((group) => (
            <div
              key={group.key}
              data-testid={`users-department-group-${group.key}`}
              style={{
                border: '1px solid #e5e7eb',
                borderRadius: '8px',
                padding: '14px',
                backgroundColor: group.departmentId != null && String(filters.department_id || '') === String(group.departmentId)
                  ? '#eff6ff'
                  : '#f9fafb',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                <div style={{ fontWeight: 600, color: '#111827' }}>{group.departmentName}</div>
                <div style={{ fontSize: '0.85rem', color: '#6b7280' }}>{`${group.users.length} \u4eba`}</div>
              </div>

              <div style={{ fontSize: '0.9rem', color: '#4b5563', marginBottom: '10px', minHeight: '40px' }}>
                {group.users.slice(0, 6).map((user) => user.username).join('\u3001')}
                {group.users.length > 6 ? ` \u7b49 ${group.users.length} \u4eba` : ''}
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
                  {'\u53ea\u770b\u672c\u90e8\u95e8'}
                </button>
              ) : (
                <div style={{ fontSize: '0.85rem', color: '#9ca3af' }}>{'\u8fd9\u4e9b\u7528\u6237\u5c1a\u672a\u5206\u914d\u90e8\u95e8'}</div>
              )}
            </div>
          ))}
        </div>

        {groupedUsers.length === 0 && (
          <div style={{ marginTop: '12px', color: '#6b7280', textAlign: 'center' }}>{'\u6682\u65e0\u7528\u6237\u5206\u7ec4'}</div>
        )}
      </div>

      <div style={{
        backgroundColor: 'white',
        borderRadius: '8px',
        boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
        overflow: 'hidden',
      }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead style={{ backgroundColor: '#f9fafb' }}>
            <tr>
              <th style={{ padding: '12px 16px', textAlign: 'left', borderBottom: '1px solid #e5e7eb' }}>{'\u7528\u6237\u540d'}</th>
              <th style={{ padding: '12px 16px', textAlign: 'left', borderBottom: '1px solid #e5e7eb' }}>{'\u516c\u53f8'}</th>
              <th style={{ padding: '12px 16px', textAlign: 'left', borderBottom: '1px solid #e5e7eb' }}>{'\u90e8\u95e8'}</th>
              <th style={{ padding: '12px 16px', textAlign: 'left', borderBottom: '1px solid #e5e7eb' }}>{'\u72b6\u6001'}</th>
              <th style={{ padding: '12px 16px', textAlign: 'left', borderBottom: '1px solid #e5e7eb' }}>{'\u767b\u5f55\u7b56\u7565'}</th>
              <th style={{ padding: '12px 16px', textAlign: 'left', borderBottom: '1px solid #e5e7eb' }}>{'\u6743\u9650\u7ec4'}</th>
              <th style={{ padding: '12px 16px', textAlign: 'left', borderBottom: '1px solid #e5e7eb' }}>{'\u521b\u5efa\u65f6\u95f4'}</th>
              <th style={{ padding: '12px 16px', textAlign: 'right', borderBottom: '1px solid #e5e7eb' }}>{'\u64cd\u4f5c'}</th>
            </tr>
          </thead>
          <tbody>
            {filteredUsers.map((user) => (
              <tr key={user.user_id} data-testid={`users-row-${user.user_id}`} style={{ borderBottom: '1px solid #e5e7eb' }}>
                <td style={{ padding: '12px 16px' }}>{user.username}</td>
                <td style={{ padding: '12px 16px', color: '#6b7280' }}>{user.company_name || '-'}</td>
                <td style={{ padding: '12px 16px', color: '#6b7280' }}>{user.department_name || '-'}</td>
                <td style={{ padding: '12px 16px' }}>
                  <span style={{
                    color: user.status === 'active' ? '#10b981' : '#ef4444',
                  }}>
                    {user.status === 'active' ? '\u6fc0\u6d3b' : '\u505c\u7528'}
                  </span>
                </td>
                <td style={{ padding: '12px 16px', color: '#4b5563', fontSize: '0.9rem' }}>
                  <div>{'\u6700\u591a\u767b\u5f55: '} {Number(user.max_login_sessions || 3)}</div>
                  <div>{'\u95f2\u7f6e\u8d85\u65f6: '} {Number(user.idle_timeout_minutes || 120)} {'\u5206\u949f'}</div>
                  <div>{'\u5f53\u524d\u5728\u7ebf: '} {Number(user.active_session_count || 0)}</div>
                  <div>
                    {'\u6700\u8fd1\u6d3b\u8dc3: '} {user.active_session_last_activity_at_ms
                      ? new Date(user.active_session_last_activity_at_ms).toLocaleString('zh-CN')
                      : '-'}
                  </div>
                </td>
                <td style={{ padding: '12px 16px' }}>
                  {user.permission_groups && user.permission_groups.length > 0 ? (
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
                      {user.permission_groups.map((pg) => (
                        <span
                          key={pg.group_id}
                          style={{
                            display: 'inline-block',
                            padding: '4px 8px',
                            borderRadius: '4px',
                            backgroundColor: '#e0e7ff',
                            color: '#4338ca',
                            fontSize: '0.85rem',
                          }}
                        >
                          {pg.group_name}
                        </span>
                      ))}
                    </div>
                  ) : (
                    <span style={{ color: '#9ca3af', fontSize: '0.85rem' }}>{'\u672a\u5206\u914d'}</span>
                  )}
                </td>
                <td style={{ padding: '12px 16px', color: '#6b7280', fontSize: '0.9rem' }}>
                  {new Date(user.created_at_ms).toLocaleString('zh-CN')}
                </td>
                <td style={{ padding: '12px 16px', textAlign: 'right' }}>
                  {canManageUsers && (
                    <button
                      onClick={() => handleOpenPolicyModal(user)}
                      data-testid={`users-edit-policy-${user.user_id}`}
                      style={{
                        padding: '6px 12px',
                        backgroundColor: '#0ea5e9',
                        color: 'white',
                        border: 'none',
                        borderRadius: '4px',
                        cursor: 'pointer',
                        fontSize: '0.9rem',
                        marginRight: '8px',
                      }}
                    >
                      {'\u767b\u5f55\u7b56\u7565'}
                    </button>
                  )}
                  {canManageUsers && (
                    <button
                    onClick={() => handleAssignGroup(user)}
                    data-testid={`users-edit-groups-${user.user_id}`}
                    style={{
                      padding: '6px 12px',
                      backgroundColor: '#8b5cf6',
                      color: 'white',
                      border: 'none',
                      borderRadius: '4px',
                      cursor: 'pointer',
                      fontSize: '0.9rem',
                      marginRight: '8px',
                    }}
                  >
                    {'\u6743\u9650\u7ec4'}
                  </button>
                  )}
                  {canManageUsers && (
                    <button
                      onClick={() => handleOpenResetPassword(user)}
                      data-testid={`users-reset-password-${user.user_id}`}
                      style={{
                        padding: '6px 12px',
                        backgroundColor: '#3b82f6',
                        color: 'white',
                        border: 'none',
                        borderRadius: '4px',
                        cursor: 'pointer',
                        fontSize: '0.9rem',
                        marginRight: '8px',
                      }}
                    >
                      {'\u4fee\u6539\u5bc6\u7801'}
                    </button>
                  )}
                  {canManageUsers && user.username !== 'admin' && (
                    <button
                      onClick={() => handleDeleteUser(user.user_id)}
                      data-testid={`users-delete-${user.user_id}`}
                      style={{
                        padding: '6px 12px',
                        backgroundColor: '#ef4444',
                        color: 'white',
                        border: 'none',
                        borderRadius: '4px',
                        cursor: 'pointer',
                        fontSize: '0.9rem',
                      }}
                    >
                      {'\u5220\u9664'}
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {filteredUsers.length === 0 && (
          <div style={{ padding: '48px', textAlign: 'center', color: '#6b7280' }}>
            {'\u6682\u65e0\u7528\u6237'}
          </div>
        )}
      </div>

      {showResetPasswordModal && resetPasswordUser && (
        <div data-testid="users-reset-password-modal" style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'rgba(0, 0, 0, 0.5)',
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          zIndex: 1000,
        }}>
          <div style={{
            backgroundColor: 'white',
            padding: '32px',
            borderRadius: '8px',
            width: '100%',
            maxWidth: '500px',
          }}>
            <h3 style={{ margin: '0 0 24px 0' }}>
              {'\u4fee\u6539\u5bc6\u7801 - '} {resetPasswordUser.username}
            </h3>

            <div style={{ marginBottom: 16 }}>
              <label style={{ display: 'block', marginBottom: 8, fontWeight: '500' }}>{'\u65b0\u5bc6\u7801'}</label>
              <input
                type="password"
                value={resetPasswordValue}
                autoComplete="new-password"
                onChange={(e) => setResetPasswordValue(e.target.value)}
                data-testid="users-reset-password-new"
                style={{
                  width: '100%',
                  padding: '10px 12px',
                  border: '1px solid #d1d5db',
                  borderRadius: '4px',
                }}
              />
            </div>

            <div style={{ marginBottom: 16 }}>
              <label style={{ display: 'block', marginBottom: 8, fontWeight: '500' }}>{'\u786e\u8ba4\u65b0\u5bc6\u7801'}</label>
              <input
                type="password"
                value={resetPasswordConfirm}
                autoComplete="new-password"
                onChange={(e) => setResetPasswordConfirm(e.target.value)}
                data-testid="users-reset-password-confirm"
                style={{
                  width: '100%',
                  padding: '10px 12px',
                  border: '1px solid #d1d5db',
                  borderRadius: '4px',
                }}
              />
            </div>

            {resetPasswordError && (
              <div style={{ marginBottom: 16, color: '#ef4444' }} data-testid="users-reset-password-error">
                {resetPasswordError}
              </div>
            )}

            <div style={{ display: 'flex', gap: '12px' }}>
              <button
                type="button"
                onClick={handleCloseResetPassword}
                disabled={resetPasswordSubmitting}
                data-testid="users-reset-password-cancel"
                style={{
                  flex: 1,
                  padding: '10px',
                  backgroundColor: '#6b7280',
                  color: 'white',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: resetPasswordSubmitting ? 'not-allowed' : 'pointer',
                }}
              >
                {'\u53d6\u6d88'}
              </button>
              <button
                type="button"
                onClick={handleSubmitResetPassword}
                disabled={resetPasswordSubmitting}
                data-testid="users-reset-password-save"
                style={{
                  flex: 1,
                  padding: '10px',
                  backgroundColor: resetPasswordSubmitting ? '#93c5fd' : '#3b82f6',
                  color: 'white',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: resetPasswordSubmitting ? 'not-allowed' : 'pointer',
                }}
              >
                {resetPasswordSubmitting ? '\u63d0\u4ea4\u4e2d...' : '\u4fdd\u5b58'}
              </button>
            </div>
          </div>
        </div>
      )}

      {showPolicyModal && policyUser && (
        <div data-testid="users-policy-modal" style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'rgba(0, 0, 0, 0.5)',
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          zIndex: 1000,
        }}>
          <div style={{
            backgroundColor: 'white',
            padding: '32px',
            borderRadius: '8px',
            width: '100%',
            maxWidth: '500px',
          }}>
            <h3 style={{ margin: '0 0 24px 0' }}>
              {'\u767b\u5f55\u7b56\u7565 - '} {policyUser.username}
            </h3>

            <div style={{ marginBottom: 16 }}>
              <label style={{ display: 'block', marginBottom: 8, fontWeight: '500' }}>
                {'\u6700\u5927\u767b\u5f55\u4f1a\u8bdd\u6570 (1-1000)'}
              </label>
              <input
                type="number"
                min={1}
                max={1000}
                value={policyForm.max_login_sessions}
                onChange={(e) => setPolicyForm({
                  ...policyForm,
                  max_login_sessions: e.target.value,
                })}
                data-testid="users-policy-max-login-sessions"
                style={{
                  width: '100%',
                  padding: '10px 12px',
                  border: '1px solid #d1d5db',
                  borderRadius: '4px',
                }}
              />
            </div>

            <div style={{ marginBottom: 16 }}>
              <label style={{ display: 'block', marginBottom: 8, fontWeight: '500' }}>
                {'\u95f2\u7f6e\u8d85\u65f6 (\u5206\u949f, 1-43200)'}
              </label>
              <input
                type="number"
                min={1}
                max={43200}
                value={policyForm.idle_timeout_minutes}
                onChange={(e) => setPolicyForm({
                  ...policyForm,
                  idle_timeout_minutes: e.target.value,
                })}
                data-testid="users-policy-idle-timeout"
                style={{
                  width: '100%',
                  padding: '10px 12px',
                  border: '1px solid #d1d5db',
                  borderRadius: '4px',
                }}
              />
            </div>

            {policyError && (
              <div style={{ marginBottom: 16, color: '#ef4444' }} data-testid="users-policy-error">
                {policyError}
              </div>
            )}

            <div style={{ display: 'flex', gap: '12px' }}>
              <button
                type="button"
                onClick={handleClosePolicyModal}
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
                {'\u53d6\u6d88'}
              </button>
              <button
                type="button"
                onClick={handleSavePolicy}
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
                {policySubmitting ? '\u63d0\u4ea4\u4e2d...' : '\u4fdd\u5b58'}
              </button>
            </div>
          </div>
        </div>
      )}

      {canManageUsers && showCreateModal && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'rgba(0, 0, 0, 0.5)',
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          zIndex: 1000,
        }}>
          <div style={{
            backgroundColor: 'white',
            padding: '32px',
            borderRadius: '8px',
            width: '100%',
            maxWidth: '400px',
          }}>
            <h3 style={{ margin: '0 0 24px 0' }}>{'\u65b0\u5efa\u7528\u6237'}</h3>
            <form onSubmit={handleCreateUser} data-testid="users-create-form">
              <div style={{ marginBottom: '16px' }}>
                <label style={{ display: 'block', marginBottom: '8px', fontWeight: '500' }}>
                  {'\u7528\u6237\u540d'}
                </label>
                <input
                  type="text"
                  required
                  value={newUser.username}
                  onChange={(e) => setNewUser({ ...newUser, username: e.target.value })}
                  data-testid="users-create-username"
                  style={{
                    width: '100%',
                    padding: '8px',
                    border: '1px solid #d1d5db',
                    borderRadius: '4px',
                    boxSizing: 'border-box',
                  }}
                />
              </div>

              <div style={{ marginBottom: '16px' }}>
                <label style={{ display: 'block', marginBottom: '8px', fontWeight: '500' }}>
                  {'\u5bc6\u7801'}
                </label>
                <input
                  type="password"
                  required
                  value={newUser.password}
                  onChange={(e) => setNewUser({ ...newUser, password: e.target.value })}
                  data-testid="users-create-password"
                  style={{
                    width: '100%',
                    padding: '8px',
                    border: '1px solid #d1d5db',
                    borderRadius: '4px',
                    boxSizing: 'border-box',
                  }}
                />
              </div>

              <div style={{ marginBottom: '16px' }}>
                <label style={{ display: 'block', marginBottom: '8px', fontWeight: '500' }}>
                  {'\u90ae\u7bb1'}
                </label>
                <input
                  type="email"
                  value={newUser.email}
                  onChange={(e) => setNewUser({ ...newUser, email: e.target.value })}
                  data-testid="users-create-email"
                  style={{
                    width: '100%',
                    padding: '8px',
                    border: '1px solid #d1d5db',
                    borderRadius: '4px',
                    boxSizing: 'border-box',
                  }}
                />
              </div>

              <div style={{ marginBottom: '16px' }}>
                <label style={{ display: 'block', marginBottom: '8px', fontWeight: '500' }}>
                  {'\u516c\u53f8'}
                </label>
                <select
                  required
                  value={newUser.company_id}
                  onChange={(e) => setNewUser({ ...newUser, company_id: e.target.value })}
                  data-testid="users-create-company"
                  style={{
                    width: '100%',
                    padding: '8px',
                    border: '1px solid #d1d5db',
                    borderRadius: '4px',
                    boxSizing: 'border-box',
                    backgroundColor: 'white',
                  }}
                >
                  <option value="" disabled>{'\u8bf7\u9009\u62e9\u516c\u53f8'}</option>
                  {companies.map((c) => (
                    <option key={c.id} value={String(c.id)}>{c.name}</option>
                  ))}
                </select>
              </div>

              <div style={{ marginBottom: '16px' }}>
                <label style={{ display: 'block', marginBottom: '8px', fontWeight: '500' }}>
                  {'\u90e8\u95e8'}
                </label>
                <select
                  required
                  value={newUser.department_id}
                  onChange={(e) => setNewUser({ ...newUser, department_id: e.target.value })}
                  data-testid="users-create-department"
                  style={{
                    width: '100%',
                    padding: '8px',
                    border: '1px solid #d1d5db',
                    borderRadius: '4px',
                    boxSizing: 'border-box',
                    backgroundColor: 'white',
                  }}
                >
                  <option value="" disabled>{'\u8bf7\u9009\u62e9\u90e8\u95e8'}</option>
                  {departments.map((d) => (
                    <option key={d.id} value={String(d.id)}>{d.name}</option>
                  ))}
                </select>
              </div>

              <div style={{ marginBottom: '16px' }}>
                <label style={{ display: 'block', marginBottom: '8px', fontWeight: '500' }}>
                  {'\u53ef\u767b\u5f55\u4e2a\u6570'}
                </label>
                <input
                  type="number"
                  min={1}
                  max={1000}
                  required
                  value={newUser.max_login_sessions}
                  onChange={(e) => setNewUser({ ...newUser, max_login_sessions: e.target.value })}
                  data-testid="users-create-max-login-sessions"
                  style={{
                    width: '100%',
                    padding: '8px',
                    border: '1px solid #d1d5db',
                    borderRadius: '4px',
                    boxSizing: 'border-box',
                  }}
                />
              </div>

              <div style={{ marginBottom: '16px' }}>
                <label style={{ display: 'block', marginBottom: '8px', fontWeight: '500' }}>
                  {'\u95f2\u7f6e\u8d85\u65f6(\u5206\u949f)'}
                </label>
                <input
                  type="number"
                  min={1}
                  max={43200}
                  required
                  value={newUser.idle_timeout_minutes}
                  onChange={(e) => setNewUser({ ...newUser, idle_timeout_minutes: e.target.value })}
                  data-testid="users-create-idle-timeout"
                  style={{
                    width: '100%',
                    padding: '8px',
                    border: '1px solid #d1d5db',
                    borderRadius: '4px',
                    boxSizing: 'border-box',
                  }}
                />
              </div>

              <div style={{ marginBottom: '24px' }}>
                <label style={{ display: 'block', marginBottom: '8px', fontWeight: '500' }}>
                  {'\u6743\u9650\u7ec4(\u53ef\u591a\u9009)'}
                </label>
                <div style={{
                  border: '1px solid #d1d5db',
                  borderRadius: '4px',
                  padding: '12px',
                  maxHeight: '200px',
                  overflowY: 'auto',
                  backgroundColor: '#f9fafb',
                }}>
                  {availableGroups.length === 0 ? (
                    <div style={{ color: '#6b7280', textAlign: 'center', padding: '8px' }}>
                      {'\u6682\u65e0\u53ef\u7528\u6743\u9650\u7ec4'}
                    </div>
                  ) : (
                    availableGroups.map((group) => (
                      <label
                        key={group.group_id}
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          padding: '8px 0',
                          cursor: 'pointer',
                        }}
                      >
                        <input
                          type="checkbox"
                          checked={newUser.group_ids?.includes(group.group_id) || false}
                          onChange={(e) => {
                            const groupIds = newUser.group_ids || [];
                            if (e.target.checked) {
                              setNewUser({ ...newUser, group_ids: [...groupIds, group.group_id] });
                            } else {
                              setNewUser({ ...newUser, group_ids: groupIds.filter(id => id !== group.group_id) });
                            }
                          }}
                          data-testid={`users-create-group-${group.group_id}`}
                          style={{ marginRight: '8px' }}
                        />
                        <div>
                          <div style={{ fontWeight: '500' }}>{group.group_name}</div>
                          {group.description && (
                            <div style={{ fontSize: '0.85rem', color: '#6b7280' }}>
                              {group.description}
                            </div>
                          )}
                        </div>
                      </label>
                    ))
                  )}
                </div>
                {newUser.group_ids && newUser.group_ids.length > 0 && (
                  <div style={{ marginTop: '8px', fontSize: '0.85rem', color: '#6b7280' }}>
                    {'\u5df2\u9009\u62e9'} {newUser.group_ids.length} {'\u4e2a\u6743\u9650\u7ec4'}
                  </div>
                )}
              </div>

              <div style={{ display: 'flex', gap: '12px' }}>
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
                  }}
                >
                  {'\u521b\u5efa'}
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setShowCreateModal(false);
                    setNewUser({
                      username: '',
                      password: '',
                      email: '',
                      company_id: '',
                      department_id: '',
                      group_ids: [],
                      max_login_sessions: 3,
                      idle_timeout_minutes: 120,
                    });
                  }}
                  data-testid="users-create-cancel"
                  style={{
                    flex: 1,
                    padding: '10px',
                    backgroundColor: '#6b7280',
                    color: 'white',
                    border: 'none',
                    borderRadius: '4px',
                    cursor: 'pointer',
                  }}
                >
                  {'\u53d6\u6d88'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {showGroupModal && editingGroupUser && (
        <div data-testid="users-group-modal" style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'rgba(0, 0, 0, 0.5)',
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          zIndex: 1000,
        }}>
          <div style={{
            backgroundColor: 'white',
            padding: '32px',
            borderRadius: '8px',
            width: '100%',
            maxWidth: '500px',
          }}>
            <h3 style={{ margin: '0 0 24px 0' }}>
              {'\u5206\u914d\u6743\u9650\u7ec4 - '} {editingGroupUser.username}
            </h3>
            <div style={{ marginBottom: '24px' }}>
              <label style={{ display: 'block', marginBottom: '8px', fontWeight: '500' }}>
                {'\u9009\u62e9\u6743\u9650\u7ec4(\u53ef\u591a\u9009)'}
              </label>
              <div style={{
                border: '1px solid #d1d5db',
                borderRadius: '4px',
                padding: '12px',
                maxHeight: '300px',
                overflowY: 'auto',
                backgroundColor: '#f9fafb',
              }}>
                {availableGroups.length === 0 ? (
                  <div style={{ color: '#6b7280', textAlign: 'center', padding: '8px' }}>
                    {'\u6682\u65e0\u53ef\u7528\u6743\u9650\u7ec4'}
                  </div>
                ) : (
                  availableGroups.map((group) => (
                    <label
                      key={group.group_id}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        padding: '8px 0',
                        cursor: 'pointer',
                      }}
                    >
                      <input
                        type="checkbox"
                        checked={selectedGroupIds?.includes(group.group_id) || false}
                        data-testid={`users-group-checkbox-${group.group_id}`}
                        onChange={(e) => {
                          const groupIds = selectedGroupIds || [];
                          if (e.target.checked) {
                            setSelectedGroupIds([...groupIds, group.group_id]);
                          } else {
                            setSelectedGroupIds(groupIds.filter(id => id !== group.group_id));
                          }
                        }}
                        style={{ marginRight: '8px' }}
                      />
                      <div>
                        <div style={{ fontWeight: '500' }}>{group.group_name}</div>
                        {group.description && (
                          <div style={{ fontSize: '0.85rem', color: '#6b7280' }}>
                            {group.description}
                          </div>
                        )}
                      </div>
                    </label>
                  ))
                )}
              </div>
              {selectedGroupIds && selectedGroupIds.length > 0 && (
                <div style={{ marginTop: '8px', fontSize: '0.85rem', color: '#6b7280' }}>
                  {'\u5df2\u9009\u62e9'} {selectedGroupIds.length} {'\u4e2a\u6743\u9650\u7ec4'}
                </div>
              )}
            </div>
            <div style={{ display: 'flex', gap: '12px' }}>
              <button
                type="button"
                onClick={handleCloseGroupModal}
                data-testid="users-group-cancel"
                style={{
                  flex: 1,
                  padding: '10px',
                  backgroundColor: '#6b7280',
                  color: 'white',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: 'pointer',
                }}
              >
                {'\u53d6\u6d88'}
              </button>
              <button
                type="button"
                onClick={handleSaveGroup}
                data-testid="users-group-save"
                style={{
                  flex: 1,
                  padding: '10px',
                  backgroundColor: '#8b5cf6',
                  color: 'white',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: 'pointer',
                }}
              >
                {'\u4fdd\u5b58'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default UserManagement;

