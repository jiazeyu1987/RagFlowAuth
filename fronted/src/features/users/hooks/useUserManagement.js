import { useCallback, useEffect, useMemo, useState } from 'react';
import { useAuth } from '../../../hooks/useAuth';
import { permissionGroupsApi } from '../../permissionGroups/api';
import { usersApi } from '../api';
import { orgDirectoryApi } from '../../orgDirectory/api';
import { DEFAULT_FILTERS, DEFAULT_NEW_USER, DEFAULT_POLICY_FORM } from '../utils/constants';
import { buildListParams, filterUsers, groupUsersByDepartment } from '../utils/userFilters';

export const useUserManagement = () => {
  const { can } = useAuth();

  const [allUsers, setAllUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [canManageUsers, setCanManageUsers] = useState(false);

  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newUser, setNewUser] = useState(DEFAULT_NEW_USER);

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
  const [policyForm, setPolicyForm] = useState(DEFAULT_POLICY_FORM);
  const [statusUpdatingUserId, setStatusUpdatingUserId] = useState(null);

  const [companies, setCompanies] = useState([]);
  const [departments, setDepartments] = useState([]);

  useEffect(() => {
    setCanManageUsers(can('users', 'manage'));
  }, [can]);

  const fetchUsers = useCallback(async () => {
    try {
      setLoading(true);
      const data = await usersApi.list(buildListParams(DEFAULT_FILTERS));
      setAllUsers(Array.isArray(data) ? data : []);
      setError(null);
    } catch (err) {
      setError(err?.message || String(err || 'Failed to load users'));
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchPermissionGroups = useCallback(async () => {
    try {
      const data = await permissionGroupsApi.list();
      if (data?.ok) {
        setAvailableGroups(Array.isArray(data.data) ? data.data : []);
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

  const filteredUsers = useMemo(() => filterUsers(allUsers, filters), [allUsers, filters]);
  const groupedUsers = useMemo(() => groupUsersByDepartment(filteredUsers), [filteredUsers]);

  const handleOpenCreateModal = useCallback(() => {
    setShowCreateModal(true);
  }, []);

  const handleCloseCreateModal = useCallback(() => {
    setShowCreateModal(false);
    setNewUser(DEFAULT_NEW_USER);
  }, []);

  const setNewUserField = useCallback((field, value) => {
    setNewUser((prev) => ({ ...prev, [field]: value }));
  }, []);

  const toggleNewUserGroup = useCallback((groupId, checked) => {
    setNewUser((prev) => {
      const groupIds = Array.isArray(prev.group_ids) ? prev.group_ids : [];
      if (checked) {
        if (groupIds.includes(groupId)) return prev;
        return { ...prev, group_ids: [...groupIds, groupId] };
      }
      return { ...prev, group_ids: groupIds.filter((id) => id !== groupId) };
    });
  }, []);

  const handleCreateUser = useCallback(
    async (e) => {
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
        handleCloseCreateModal();
        fetchUsers();
      } catch (err) {
        setError(err?.message || String(err || 'Create user failed'));
      }
    },
    [fetchUsers, handleCloseCreateModal, newUser]
  );

  const handleDeleteUser = useCallback(
    async (userId) => {
      if (!window.confirm('确定要删除该用户吗？')) return;
      try {
        await usersApi.remove(userId);
        fetchUsers();
      } catch (err) {
        setError(err?.message || String(err || 'Delete user failed'));
      }
    },
    [fetchUsers]
  );

  const handleToggleUserStatus = useCallback(
    async (user) => {
      if (!user?.user_id) return;
      const nextStatus = user.status === 'active' ? 'inactive' : 'active';
      try {
        setStatusUpdatingUserId(user.user_id);
        await usersApi.update(user.user_id, { status: nextStatus });
        await fetchUsers();
      } catch (err) {
        setError(err?.message || String(err || 'Toggle user status failed'));
      } finally {
        setStatusUpdatingUserId(null);
      }
    },
    [fetchUsers]
  );

  const handleOpenResetPassword = useCallback((user) => {
    setResetPasswordUser(user);
    setResetPasswordValue('');
    setResetPasswordConfirm('');
    setResetPasswordError(null);
    setShowResetPasswordModal(true);
  }, []);

  const handleCloseResetPassword = useCallback(() => {
    setShowResetPasswordModal(false);
    setResetPasswordUser(null);
    setResetPasswordValue('');
    setResetPasswordConfirm('');
    setResetPasswordError(null);
  }, []);

  const handleSubmitResetPassword = useCallback(async () => {
    if (!resetPasswordUser) return;
    setResetPasswordError(null);

    if (!resetPasswordValue) {
      setResetPasswordError('请输入新密码');
      return;
    }
    if (resetPasswordValue !== resetPasswordConfirm) {
      setResetPasswordError('两次输入的新密码不一致');
      return;
    }

    try {
      setResetPasswordSubmitting(true);
      await usersApi.resetPassword(resetPasswordUser.user_id, resetPasswordValue);
      handleCloseResetPassword();
    } catch (err) {
      setResetPasswordError(err?.message || '修改密码失败');
    } finally {
      setResetPasswordSubmitting(false);
    }
  }, [handleCloseResetPassword, resetPasswordConfirm, resetPasswordUser, resetPasswordValue]);

  const handleOpenPolicyModal = useCallback((user) => {
    setPolicyUser(user);
    setPolicyError(null);
    setPolicyForm({
      max_login_sessions: Number(user?.max_login_sessions || 3),
      idle_timeout_minutes: Number(user?.idle_timeout_minutes || 120),
    });
    setShowPolicyModal(true);
  }, []);

  const handleClosePolicyModal = useCallback(() => {
    setShowPolicyModal(false);
    setPolicyUser(null);
    setPolicySubmitting(false);
    setPolicyError(null);
    setPolicyForm(DEFAULT_POLICY_FORM);
  }, []);

  const handleSavePolicy = useCallback(async () => {
    if (!policyUser) return;
    setPolicyError(null);

    const maxSessions = Number(policyForm.max_login_sessions);
    const idleMinutes = Number(policyForm.idle_timeout_minutes);

    if (!Number.isInteger(maxSessions) || maxSessions < 1 || maxSessions > 1000) {
      setPolicyError('可登录个数需为 1-1000 的整数');
      return;
    }
    if (!Number.isInteger(idleMinutes) || idleMinutes < 1 || idleMinutes > 43200) {
      setPolicyError('闲置超时需为 1-43200 分钟的整数');
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
      setPolicyError(err?.message || '保存登录策略失败');
    } finally {
      setPolicySubmitting(false);
    }
  }, [fetchUsers, handleClosePolicyModal, policyForm, policyUser]);

  const handleAssignGroup = useCallback((user) => {
    setEditingGroupUser(user);
    const groupIds = user?.group_ids || (user?.permission_groups || []).map((pg) => pg.group_id);
    setSelectedGroupIds(Array.isArray(groupIds) ? groupIds : []);
    setShowGroupModal(true);
  }, []);

  const handleCloseGroupModal = useCallback(() => {
    setShowGroupModal(false);
    setEditingGroupUser(null);
    setSelectedGroupIds([]);
  }, []);

  const toggleSelectedGroup = useCallback((groupId, checked) => {
    setSelectedGroupIds((prev) => {
      const groupIds = Array.isArray(prev) ? prev : [];
      if (checked) {
        if (groupIds.includes(groupId)) return groupIds;
        return [...groupIds, groupId];
      }
      return groupIds.filter((id) => id !== groupId);
    });
  }, []);

  const handleSaveGroup = useCallback(async () => {
    try {
      await usersApi.update(editingGroupUser.user_id, {
        group_ids: selectedGroupIds,
      });
      handleCloseGroupModal();
      fetchUsers();
    } catch (err) {
      setError(err?.message || String(err || 'Save group failed'));
    }
  }, [editingGroupUser, fetchUsers, handleCloseGroupModal, selectedGroupIds]);

  const handleResetFilters = useCallback(() => {
    setFilters(DEFAULT_FILTERS);
  }, []);

  return {
    allUsers,
    loading,
    error,
    canManageUsers,
    showCreateModal,
    newUser,
    filters,
    availableGroups,
    editingGroupUser,
    showGroupModal,
    selectedGroupIds,
    showResetPasswordModal,
    resetPasswordUser,
    resetPasswordValue,
    resetPasswordConfirm,
    resetPasswordSubmitting,
    resetPasswordError,
    showPolicyModal,
    policyUser,
    policySubmitting,
    policyError,
    policyForm,
    statusUpdatingUserId,
    companies,
    departments,
    filteredUsers,
    groupedUsers,
    setFilters,
    setPolicyForm,
    setResetPasswordValue,
    setResetPasswordConfirm,
    handleOpenCreateModal,
    handleCloseCreateModal,
    setNewUserField,
    toggleNewUserGroup,
    handleCreateUser,
    handleDeleteUser,
    handleToggleUserStatus,
    handleOpenResetPassword,
    handleCloseResetPassword,
    handleSubmitResetPassword,
    handleOpenPolicyModal,
    handleClosePolicyModal,
    handleSavePolicy,
    handleAssignGroup,
    handleCloseGroupModal,
    toggleSelectedGroup,
    handleSaveGroup,
    handleResetFilters,
  };
};
