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
  });

  // 用户筛选
  const [filters, setFilters] = useState(DEFAULT_FILTERS);

  // 权限组相关 state
  const [availableGroups, setAvailableGroups] = useState([]);
  const [editingGroupUser, setEditingGroupUser] = useState(null);
  const [showGroupModal, setShowGroupModal] = useState(false);
  const [selectedGroupIds, setSelectedGroupIds] = useState([]);

  // 公司/部门下拉数据
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

    // For admin UI, we want enough rows for client-side filtering.
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

  const handleCreateUser = async (e) => {
    e.preventDefault();
    try {
      const payload = {
        ...newUser,
        company_id: newUser.company_id ? Number(newUser.company_id) : null,
        department_id: newUser.department_id ? Number(newUser.department_id) : null,
      };
      await usersApi.create(payload);
      setShowCreateModal(false);
      setNewUser({ username: '', password: '', email: '', company_id: '', department_id: '', group_ids: [] });
      fetchUsers();
    } catch (err) {
      setError(err.message);
    }
  };

  const handleDeleteUser = async (userId) => {
    if (!window.confirm('确定要删除该用户吗？')) return;

    try {
      await usersApi.remove(userId);
      fetchUsers();
    } catch (err) {
      setError(err.message);
    }
  };

  // 权限组相关函数
  const handleAssignGroup = async (user) => {
    try {
      setEditingGroupUser(user);
      // 从 permission_groups 中提取 group_ids，确保正确预选
      const groupIds = user.group_ids || (user.permission_groups || []).map(pg => pg.group_id);
      setSelectedGroupIds(groupIds);
      setShowGroupModal(true);
      console.log('编辑用户权限组:', user.username, '已有权限组:', groupIds);
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
        <h2 style={{ margin: 0 }}>用户管理</h2>
        {canManageUsers && (
          <button
            onClick={() => setShowCreateModal(true)}
            style={{
              padding: '10px 20px',
              backgroundColor: '#3b82f6',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
            }}
          >
            新建用户
          </button>
        )}
      </div>

      {/* 筛选栏 */}
      <div style={{
        backgroundColor: 'white',
        borderRadius: '8px',
        boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
        padding: '16px',
        marginBottom: '16px',
      }}>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '12px', alignItems: 'flex-end' }}>
          <div style={{ minWidth: '220px' }}>
            <label style={{ display: 'block', marginBottom: '6px', fontWeight: 500 }}>搜索用户名</label>
            <input
              value={filters.q}
              onChange={(e) => setFilters({ ...filters, q: e.target.value })}
              placeholder="支持模糊搜索"
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
            <label style={{ display: 'block', marginBottom: '6px', fontWeight: 500 }}>公司</label>
            <select
              value={filters.company_id}
              onChange={(e) => setFilters({ ...filters, company_id: e.target.value })}
              style={{ width: '100%', padding: '8px', border: '1px solid #d1d5db', borderRadius: '6px' }}
            >
              <option value="">全部</option>
              {companies.map((c) => (
                <option key={c.id} value={String(c.id)}>{c.name}</option>
              ))}
            </select>
          </div>

          <div style={{ minWidth: '180px' }}>
            <label style={{ display: 'block', marginBottom: '6px', fontWeight: 500 }}>部门</label>
            <select
              value={filters.department_id}
              onChange={(e) => setFilters({ ...filters, department_id: e.target.value })}
              style={{ width: '100%', padding: '8px', border: '1px solid #d1d5db', borderRadius: '6px' }}
            >
              <option value="">全部</option>
              {departments.map((d) => (
                <option key={d.id} value={String(d.id)}>{d.name}</option>
              ))}
            </select>
          </div>

          <div style={{ minWidth: '140px' }}>
            <label style={{ display: 'block', marginBottom: '6px', fontWeight: 500 }}>状态</label>
            <select
              value={filters.status}
              onChange={(e) => setFilters({ ...filters, status: e.target.value })}
              style={{ width: '100%', padding: '8px', border: '1px solid #d1d5db', borderRadius: '6px' }}
            >
              <option value="">全部</option>
              <option value="active">激活</option>
              <option value="inactive">停用</option>
            </select>
          </div>

          <div style={{ minWidth: '180px' }}>
            <label style={{ display: 'block', marginBottom: '6px', fontWeight: 500 }}>权限组</label>
            <select
              value={filters.group_id}
              onChange={(e) => setFilters({ ...filters, group_id: e.target.value })}
              style={{ width: '100%', padding: '8px', border: '1px solid #d1d5db', borderRadius: '6px' }}
            >
              <option value="">全部</option>
              {availableGroups.map((g) => (
                <option key={g.group_id} value={String(g.group_id)}>{g.group_name}</option>
              ))}
            </select>
          </div>

          <div>
            <label style={{ display: 'block', marginBottom: '6px', fontWeight: 500 }}>创建时间(从)</label>
            <input
              type="date"
              value={filters.created_from}
              onChange={(e) => setFilters({ ...filters, created_from: e.target.value })}
              style={{ padding: '8px', border: '1px solid #d1d5db', borderRadius: '6px' }}
            />
          </div>

          <div>
            <label style={{ display: 'block', marginBottom: '6px', fontWeight: 500 }}>创建时间(到)</label>
            <input
              type="date"
              value={filters.created_to}
              onChange={(e) => setFilters({ ...filters, created_to: e.target.value })}
              style={{ padding: '8px', border: '1px solid #d1d5db', borderRadius: '6px' }}
            />
          </div>

          <button
            type="button"
            onClick={() => {
              setFilters(DEFAULT_FILTERS);
            }}
            style={{
              padding: '10px 14px',
              backgroundColor: '#6b7280',
              color: 'white',
              border: 'none',
              borderRadius: '6px',
              cursor: 'pointer',
            }}
          >
            重置
          </button>
        </div>
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
              <th style={{ padding: '12px 16px', textAlign: 'left', borderBottom: '1px solid #e5e7eb' }}>用户名</th>
              <th style={{ padding: '12px 16px', textAlign: 'left', borderBottom: '1px solid #e5e7eb' }}>邮箱</th>
              <th style={{ padding: '12px 16px', textAlign: 'left', borderBottom: '1px solid #e5e7eb' }}>公司</th>
              <th style={{ padding: '12px 16px', textAlign: 'left', borderBottom: '1px solid #e5e7eb' }}>部门</th>
              <th style={{ padding: '12px 16px', textAlign: 'left', borderBottom: '1px solid #e5e7eb' }}>状态</th>
              <th style={{ padding: '12px 16px', textAlign: 'left', borderBottom: '1px solid #e5e7eb' }}>权限组</th>
              <th style={{ padding: '12px 16px', textAlign: 'left', borderBottom: '1px solid #e5e7eb' }}>创建时间</th>
              <th style={{ padding: '12px 16px', textAlign: 'right', borderBottom: '1px solid #e5e7eb' }}>操作</th>
            </tr>
          </thead>
          <tbody>
            {filteredUsers.map((user) => (
              <tr key={user.user_id} style={{ borderBottom: '1px solid #e5e7eb' }}>
                <td style={{ padding: '12px 16px' }}>{user.username}</td>
                <td style={{ padding: '12px 16px', color: '#6b7280' }}>{user.email || '-'}</td>
                <td style={{ padding: '12px 16px', color: '#6b7280' }}>{user.company_name || '-'}</td>
                <td style={{ padding: '12px 16px', color: '#6b7280' }}>{user.department_name || '-'}</td>
                <td style={{ padding: '12px 16px' }}>
                  <span style={{
                    color: user.status === 'active' ? '#10b981' : '#ef4444',
                  }}>
                    {user.status === 'active' ? '激活' : '停用'}
                  </span>
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
                    <span style={{ color: '#9ca3af', fontSize: '0.85rem' }}>未分配</span>
                  )}
                </td>
                <td style={{ padding: '12px 16px', color: '#6b7280', fontSize: '0.9rem' }}>
                  {new Date(user.created_at_ms).toLocaleString('zh-CN')}
                </td>
                <td style={{ padding: '12px 16px', textAlign: 'right' }}>
                  <button
                    onClick={() => handleAssignGroup(user)}
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
                    权限组
                  </button>
                  {canManageUsers && user.username !== 'admin' && (
                    <button
                      onClick={() => handleDeleteUser(user.user_id)}
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
                      删除
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {filteredUsers.length === 0 && (
          <div style={{ padding: '48px', textAlign: 'center', color: '#6b7280' }}>
            暂无用户
          </div>
        )}
      </div>

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
            <h3 style={{ margin: '0 0 24px 0' }}>新建用户</h3>
            <form onSubmit={handleCreateUser}>
              <div style={{ marginBottom: '16px' }}>
                <label style={{ display: 'block', marginBottom: '8px', fontWeight: '500' }}>
                  用户名
                </label>
                <input
                  type="text"
                  required
                  value={newUser.username}
                  onChange={(e) => setNewUser({ ...newUser, username: e.target.value })}
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
                  密码
                </label>
                <input
                  type="password"
                  required
                  value={newUser.password}
                  onChange={(e) => setNewUser({ ...newUser, password: e.target.value })}
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
                  邮箱
                </label>
                <input
                  type="email"
                  value={newUser.email}
                  onChange={(e) => setNewUser({ ...newUser, email: e.target.value })}
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
                  公司
                </label>
                <select
                  required
                  value={newUser.company_id}
                  onChange={(e) => setNewUser({ ...newUser, company_id: e.target.value })}
                  style={{
                    width: '100%',
                    padding: '8px',
                    border: '1px solid #d1d5db',
                    borderRadius: '4px',
                    boxSizing: 'border-box',
                    backgroundColor: 'white',
                  }}
                >
                  <option value="" disabled>请选择公司</option>
                  {companies.map((c) => (
                    <option key={c.id} value={String(c.id)}>{c.name}</option>
                  ))}
                </select>
              </div>

              <div style={{ marginBottom: '16px' }}>
                <label style={{ display: 'block', marginBottom: '8px', fontWeight: '500' }}>
                  部门
                </label>
                <select
                  required
                  value={newUser.department_id}
                  onChange={(e) => setNewUser({ ...newUser, department_id: e.target.value })}
                  style={{
                    width: '100%',
                    padding: '8px',
                    border: '1px solid #d1d5db',
                    borderRadius: '4px',
                    boxSizing: 'border-box',
                    backgroundColor: 'white',
                  }}
                >
                  <option value="" disabled>请选择部门</option>
                  {departments.map((d) => (
                    <option key={d.id} value={String(d.id)}>{d.name}</option>
                  ))}
                </select>
              </div>

              <div style={{ marginBottom: '24px' }}>
                <label style={{ display: 'block', marginBottom: '8px', fontWeight: '500' }}>
                  权限组 (可多选)
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
                      暂无可用权限组
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
                    已选择 {newUser.group_ids.length} 个权限组
                  </div>
                )}
              </div>

              <div style={{ display: 'flex', gap: '12px' }}>
                <button
                  type="submit"
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
                  创建
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setShowCreateModal(false);
                    setNewUser({ username: '', password: '', email: '', company_id: '', department_id: '', group_ids: [] });
                  }}
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
                  取消
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* 权限组分配模态框 */}
      {showGroupModal && editingGroupUser && (
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
            maxWidth: '500px',
          }}>
            <h3 style={{ margin: '0 0 24px 0' }}>
              分配权限组 - {editingGroupUser.username}
            </h3>
            <div style={{ marginBottom: '24px' }}>
              <label style={{ display: 'block', marginBottom: '8px', fontWeight: '500' }}>
                选择权限组 (可多选)
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
                    暂无可用权限组
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
                  已选择 {selectedGroupIds.length} 个权限组
                </div>
              )}
            </div>
            <div style={{ display: 'flex', gap: '12px' }}>
              <button
                type="button"
                onClick={handleCloseGroupModal}
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
                取消
              </button>
              <button
                type="button"
                onClick={handleSaveGroup}
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
                保存
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default UserManagement;
