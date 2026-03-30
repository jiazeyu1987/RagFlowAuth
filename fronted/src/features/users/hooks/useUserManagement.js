import { useCallback, useEffect, useMemo, useState } from 'react';
import { useAuth } from '../../../hooks/useAuth';
import { permissionGroupsApi } from '../../permissionGroups/api';
import { usersApi } from '../api';
import { orgDirectoryApi } from '../../orgDirectory/api';
import { DEFAULT_FILTERS, DEFAULT_NEW_USER, DEFAULT_POLICY_FORM } from '../utils/constants';
import { buildListParams, filterUsers, groupUsersByDepartment } from '../utils/userFilters';

const isUserLoginDisabled = (user) => {
  if (!user) return false;
  if (user.login_disabled === true) return true;
  const status = String(user.status || '').toLowerCase();
  if (status && status !== 'active') return true;
  const disableEnabled = user.disable_login_enabled === true;
  if (!disableEnabled) return false;
  const untilMs = Number(user.disable_login_until_ms || 0);
  if (!Number.isFinite(untilMs) || untilMs <= 0) return true;
  return Date.now() < untilMs;
};

const formatDateForInput = (ms) => {
  if (!ms) return '';
  const date = new Date(Number(ms));
  if (!Number.isFinite(date.getTime())) return '';
  const y = date.getFullYear();
  const m = `${date.getMonth() + 1}`.padStart(2, '0');
  const d = `${date.getDate()}`.padStart(2, '0');
  return `${y}-${m}-${d}`;
};

const parseDisableUntilDate = (dateText) => {
  const raw = String(dateText || '').trim();
  if (!raw) return null;
  const date = new Date(`${raw}T23:59:59`);
  const ms = date.getTime();
  return Number.isFinite(ms) ? ms : null;
};

export const useUserManagement = () => {
  const { can } = useAuth();

  const [allUsers, setAllUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [canManageUsers, setCanManageUsers] = useState(false);

  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newUser, setNewUser] = useState(DEFAULT_NEW_USER);
  const [createUserError, setCreateUserError] = useState(null);

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
  const [showDisableUserModal, setShowDisableUserModal] = useState(false);
  const [disableTargetUser, setDisableTargetUser] = useState(null);
  const [disableMode, setDisableMode] = useState('immediate');
  const [disableUntilDate, setDisableUntilDate] = useState('');
  const [disableUserError, setDisableUserError] = useState(null);

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
      setError(err?.message || String(err || '加载用户失败'));
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
    setCreateUserError(null);
    setShowCreateModal(true);
  }, []);

  const handleCloseCreateModal = useCallback(() => {
    setShowCreateModal(false);
    setNewUser(DEFAULT_NEW_USER);
    setCreateUserError(null);
  }, []);

  const setNewUserField = useCallback((field, value) => {
    setCreateUserError(null);
    setNewUser((prev) => ({ ...prev, [field]: value }));
  }, []);

  const toggleNewUserGroup = useCallback((groupId, checked) => {
    setCreateUserError(null);
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
      setCreateUserError(null);
      try {
        const payload = {
          ...newUser,
          full_name: String(newUser.full_name || '').trim() || null,
          company_id: newUser.company_id ? Number(newUser.company_id) : null,
          department_id: newUser.department_id ? Number(newUser.department_id) : null,
          max_login_sessions: Number(newUser.max_login_sessions),
          idle_timeout_minutes: Number(newUser.idle_timeout_minutes),
        };
        await usersApi.create(payload);
        handleCloseCreateModal();
        fetchUsers();
      } catch (err) {
        const code = String(err?.message || '').trim();
        if (code === 'username_already_exists') {
          setCreateUserError('用户名已存在');
          return;
        }
        setCreateUserError(code || String(err || '创建用户失败'));
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
        setError(err?.message || String(err || '删除用户失败'));
      }
    },
    [fetchUsers]
  );

  const handleCloseDisableUserModal = useCallback(() => {
    setShowDisableUserModal(false);
    setDisableTargetUser(null);
    setDisableMode('immediate');
    setDisableUntilDate('');
    setDisableUserError(null);
  }, []);

  const handleChangeDisableMode = useCallback((mode) => {
    const nextMode = mode === 'until' ? 'until' : 'immediate';
    setDisableMode(nextMode);
    if (nextMode !== 'until') {
      setDisableUntilDate('');
    }
    setDisableUserError(null);
  }, []);

  const handleChangeDisableUntilDate = useCallback((value) => {
    setDisableUntilDate(String(value || ''));
    setDisableUserError(null);
  }, []);

  const handleConfirmDisableUser = useCallback(async () => {
    if (!disableTargetUser?.user_id) return;
    setDisableUserError(null);

    let payload = {
      status: 'inactive',
      disable_login_enabled: false,
      disable_login_until_ms: null,
    };

    if (disableMode === 'until') {
      const untilMs = parseDisableUntilDate(disableUntilDate);
      if (!untilMs) {
        setDisableUserError('请选择禁用到期日期');
        return;
      }
      if (untilMs <= Date.now()) {
        setDisableUserError('禁用到期时间必须晚于当前时间');
        return;
      }
      payload = {
        status: 'active',
        disable_login_enabled: true,
        disable_login_until_ms: untilMs,
      };
    }

    try {
      setStatusUpdatingUserId(disableTargetUser.user_id);
      await usersApi.update(disableTargetUser.user_id, payload);
      handleCloseDisableUserModal();
      await fetchUsers();
    } catch (err) {
      setDisableUserError(err?.message || '禁用用户失败');
    } finally {
      setStatusUpdatingUserId(null);
    }
  }, [disableMode, disableTargetUser, disableUntilDate, fetchUsers, handleCloseDisableUserModal]);

  const handleToggleUserStatus = useCallback(
    async (user) => {
      if (!user?.user_id) return;
      if (String(user?.username || '').toLowerCase() === 'admin') return;

      const disabledNow = isUserLoginDisabled(user);
      if (!disabledNow) {
        setDisableTargetUser(user);
        setDisableMode('immediate');
        setDisableUntilDate('');
        setDisableUserError(null);
        setShowDisableUserModal(true);
        return;
      }

      const payload = { status: 'active', disable_login_enabled: false, disable_login_until_ms: null };
      try {
        setStatusUpdatingUserId(user.user_id);
        await usersApi.update(user.user_id, payload);
        await fetchUsers();
      } catch (err) {
        setError(err?.message || String(err || '切换用户状态失败'));
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
    const disabledNow = isUserLoginDisabled(user);
    const disableUntilMs = Number(user?.disable_login_until_ms || 0);
    const hasFutureUntil = Number.isFinite(disableUntilMs) && disableUntilMs > Date.now();

    setPolicyUser(user);
    setPolicyError(null);
    setPolicyForm({
      full_name: String(user?.full_name || ''),
      max_login_sessions: Number(user?.max_login_sessions || 3),
      idle_timeout_minutes: Number(user?.idle_timeout_minutes || 120),
      can_change_password: user?.can_change_password !== false,
      disable_account: disabledNow,
      disable_mode: hasFutureUntil ? 'until' : 'immediate',
      disable_until_date: hasFutureUntil ? formatDateForInput(disableUntilMs) : '',
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
      setPolicyError('可登录会话数需为 1-1000 的整数');
      return;
    }
    if (!Number.isInteger(idleMinutes) || idleMinutes < 1 || idleMinutes > 43200) {
      setPolicyError('空闲超时需为 1-43200 分钟的整数');
      return;
    }

    const payload = {
      full_name: String(policyForm.full_name || '').trim(),
      max_login_sessions: maxSessions,
      idle_timeout_minutes: idleMinutes,
      can_change_password: !!policyForm.can_change_password,
    };

    if (!policyForm.disable_account) {
      payload.status = 'active';
      payload.disable_login_enabled = false;
      payload.disable_login_until_ms = null;
    } else if (policyForm.disable_mode === 'until') {
      const untilMs = parseDisableUntilDate(policyForm.disable_until_date);
      if (!untilMs) {
        setPolicyError('请选择禁用到期日期');
        return;
      }
      if (untilMs <= Date.now()) {
        setPolicyError('禁用到期时间必须晚于当前时间');
        return;
      }
      payload.status = 'active';
      payload.disable_login_enabled = true;
      payload.disable_login_until_ms = untilMs;
    } else {
      payload.status = 'inactive';
      payload.disable_login_enabled = false;
      payload.disable_login_until_ms = null;
    }

    try {
      setPolicySubmitting(true);
      await usersApi.update(policyUser.user_id, payload);
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
      setError(err?.message || String(err || '保存权限组失败'));
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
    createUserError,
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
    showDisableUserModal,
    disableTargetUser,
    disableMode,
    disableUntilDate,
    disableUserError,
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
    handleCloseDisableUserModal,
    handleChangeDisableMode,
    handleChangeDisableUntilDate,
    handleConfirmDisableUser,
    handleAssignGroup,
    handleCloseGroupModal,
    toggleSelectedGroup,
    handleSaveGroup,
    handleResetFilters,
  };
};

