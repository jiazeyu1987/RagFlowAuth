import { useCallback, useEffect, useMemo, useState } from 'react';
import { useAuth } from '../../../hooks/useAuth';
import { permissionGroupsApi } from '../../permissionGroups/api';
import { usersApi } from '../api';
import { orgDirectoryApi } from '../../orgDirectory/api';
import { knowledgeApi } from '../../knowledge/api';
import { DEFAULT_FILTERS, DEFAULT_NEW_USER, DEFAULT_POLICY_FORM } from '../utils/constants';
import { buildListParams, filterUsers, groupUsersByDepartment } from '../utils/userFilters';

const UUID_LIKE_PATTERN =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

const COMPANY_REQUIRED_MESSAGE = '请选择公司和部门';
const SUB_ADMIN_REQUIRED_MESSAGE = '请选择归属子管理员';
const KB_ROOT_REQUIRED_MESSAGE = '请选择子管理员负责的知识库目录';
const KB_ROOT_REBIND_MESSAGE = '当前负责目录已失效，请先重新绑定有效目录';
const ORG_NO_COMPANY_MESSAGE = '组织管理中没有可用公司，无法创建或编辑用户';
const ORG_NO_DEPARTMENT_MESSAGE = '组织管理中没有可用部门，无法创建或编辑用户';

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

const normalizePersonName = (value) => {
  const text = String(value || '').trim();
  if (!text) return '';
  if (UUID_LIKE_PATTERN.test(text)) return '';
  return text;
};

const normalizeGroupId = (value) => {
  const groupId = Number(value);
  return Number.isInteger(groupId) && groupId > 0 ? groupId : null;
};

const normalizeGroupIds = (values) =>
  Array.from(
    new Set(
      (Array.isArray(values) ? values : [])
        .map((value) => normalizeGroupId(value))
        .filter((groupId) => groupId != null)
    )
  );

const buildUserDisplayLabel = (item) => {
  const fullName = normalizePersonName(item?.full_name);
  const username = String(item?.username || '').trim();
  if (fullName && username) return `${fullName}(${username})`;
  if (fullName) return fullName;
  if (username) return username;
  return String(item?.user_id || '').trim();
};

const mapRoleToUserType = (role) => (String(role || '') === 'sub_admin' ? 'sub_admin' : 'normal');

const normalizeDraftByUserType = (draft) => {
  const userType = String(draft?.user_type || 'normal') === 'sub_admin' ? 'sub_admin' : 'normal';
  const next = {
    ...draft,
    user_type: userType,
    group_ids: normalizeGroupIds(draft?.group_ids),
  };
  if (userType !== 'sub_admin') {
    next.managed_kb_root_node_id = '';
    next.group_ids = [];
  } else {
    next.manager_user_id = '';
  }
  return next;
};

const nodeExistsInTree = (nodes, nodeId) =>
  (Array.isArray(nodes) ? nodes : []).some((node) => String(node?.id || '') === String(nodeId || ''));

const mapUserManagementErrorMessage = (value) => {
  const code = String(value || '').trim();
  if (!code) return '';
  if (code === 'managed_kb_root_node_not_found') {
    return '当前负责目录已失效，请先在目标公司的知识库目录中重新绑定有效目录。';
  }
  if (code === 'managed_kb_root_node_required_for_sub_admin') {
    return '请选择子管理员负责的知识库目录';
  }
  if (code === 'company_required_for_sub_admin') {
    return '子管理员必须选择公司';
  }
  if (code === 'username_already_exists') {
    return '用户账号已存在';
  }
  return code;
};

export const useUserManagement = () => {
  const { can, user } = useAuth();
  const isAdminUser = String(user?.role || '') === 'admin';
  const isSubAdminUser = String(user?.role || '') === 'sub_admin';
  const currentUserId = String(user?.user_id || '');

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
  const [policyForm, setPolicyFormState] = useState(DEFAULT_POLICY_FORM);
  const [statusUpdatingUserId, setStatusUpdatingUserId] = useState(null);
  const [showDisableUserModal, setShowDisableUserModal] = useState(false);
  const [disableTargetUser, setDisableTargetUser] = useState(null);
  const [disableMode, setDisableMode] = useState('immediate');
  const [disableUntilDate, setDisableUntilDate] = useState('');
  const [disableUserError, setDisableUserError] = useState(null);

  const [companies, setCompanies] = useState([]);
  const [departments, setDepartments] = useState([]);
  const [orgDirectoryError, setOrgDirectoryError] = useState(null);
  const [kbDirectoryNodes, setKbDirectoryNodes] = useState([]);
  const [kbDirectoryLoading, setKbDirectoryLoading] = useState(false);
  const [kbDirectoryError, setKbDirectoryError] = useState(null);
  const [kbDirectoryCreatingRoot, setKbDirectoryCreatingRoot] = useState(false);
  const [kbDirectoryCreateError, setKbDirectoryCreateError] = useState(null);

  useEffect(() => {
    setCanManageUsers(can('users', 'manage'));
  }, [can]);

  const fetchUsers = useCallback(async () => {
    try {
      setLoading(true);
      const data = await usersApi.list(buildListParams(DEFAULT_FILTERS));
      setAllUsers(data);
      setError(null);
    } catch (err) {
      setError(mapUserManagementErrorMessage(err?.message || '加载用户失败'));
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchPermissionGroups = useCallback(async () => {
    if (!isAdminUser && !isSubAdminUser) {
      setAvailableGroups([]);
      return;
    }
    try {
      const data = await permissionGroupsApi.listAssignable();
      setAvailableGroups(data);
    } catch (err) {
      console.error('Failed to load permission groups:', err);
      setAvailableGroups([]);
    }
  }, [isAdminUser, isSubAdminUser]);

  const fetchOrgDirectory = useCallback(async () => {
    try {
      const [companyList, deptList] = await Promise.all([
        orgDirectoryApi.listCompanies(),
        orgDirectoryApi.listDepartments(),
      ]);
      const nextCompanies = Array.isArray(companyList) ? companyList : [];
      const nextDepartments = Array.isArray(deptList) ? deptList : [];
      setCompanies(nextCompanies);
      setDepartments(nextDepartments);
      if (!nextCompanies.length) {
        setOrgDirectoryError(ORG_NO_COMPANY_MESSAGE);
        return;
      }
      if (!nextDepartments.length) {
        setOrgDirectoryError(ORG_NO_DEPARTMENT_MESSAGE);
        return;
      }
      setOrgDirectoryError(null);
    } catch (err) {
      setCompanies([]);
      setDepartments([]);
      setOrgDirectoryError(mapUserManagementErrorMessage(err?.message || '加载组织管理数据失败'));
    }
  }, []);

  const fetchKnowledgeDirectories = useCallback(
    async (companyId) => {
      const normalizedCompanyId = companyId == null || companyId === '' ? null : Number(companyId);
      if (normalizedCompanyId == null || !Number.isFinite(normalizedCompanyId)) {
        setKbDirectoryNodes([]);
        setKbDirectoryError(null);
        setKbDirectoryCreateError(null);
        return [];
      }
      try {
        setKbDirectoryLoading(true);
        const data = await knowledgeApi.listKnowledgeDirectories({
          companyId: isAdminUser ? normalizedCompanyId : undefined,
        });
        const nodes = Array.isArray(data?.nodes) ? data.nodes : [];
        setKbDirectoryNodes(nodes);
        setKbDirectoryError(null);
        return nodes;
      } catch (err) {
        setKbDirectoryNodes([]);
        setKbDirectoryError(mapUserManagementErrorMessage(err?.message || '加载知识库目录失败'));
        return [];
      } finally {
        setKbDirectoryLoading(false);
      }
    },
    [isAdminUser]
  );

  useEffect(() => {
    fetchUsers();
    fetchPermissionGroups();
    fetchOrgDirectory();
  }, [fetchOrgDirectory, fetchPermissionGroups, fetchUsers]);

  useEffect(() => {
    const selectedCompanyId = newUser.company_id ? Number(newUser.company_id) : null;
    const selectedDepartmentId = newUser.department_id ? Number(newUser.department_id) : null;
    if (selectedDepartmentId == null) return;
    const selectedDepartment = departments.find((department) => department.id === selectedDepartmentId);
    if (!selectedDepartment) return;
    if (
      selectedCompanyId != null
      && selectedDepartment.company_id != null
      && Number(selectedDepartment.company_id) !== selectedCompanyId
    ) {
      setNewUser((prev) => ({ ...prev, department_id: '' }));
    }
  }, [departments, newUser.company_id, newUser.department_id]);

  useEffect(() => {
    const selectedCompanyId = policyForm.company_id ? Number(policyForm.company_id) : null;
    const selectedDepartmentId = policyForm.department_id ? Number(policyForm.department_id) : null;
    if (selectedDepartmentId == null) return;
    const selectedDepartment = departments.find((department) => department.id === selectedDepartmentId);
    if (!selectedDepartment) return;
    if (
      selectedCompanyId != null
      && selectedDepartment.company_id != null
      && Number(selectedDepartment.company_id) !== selectedCompanyId
    ) {
      setPolicyFormState((prev) => ({ ...prev, department_id: '' }));
    }
  }, [departments, policyForm.company_id, policyForm.department_id]);

  useEffect(() => {
    if (!showCreateModal || String(newUser.user_type || 'normal') !== 'sub_admin') return;
    fetchKnowledgeDirectories(newUser.company_id);
  }, [fetchKnowledgeDirectories, newUser.company_id, newUser.user_type, showCreateModal]);

  useEffect(() => {
    if (!showPolicyModal || String(policyForm.user_type || 'normal') !== 'sub_admin') return;
    fetchKnowledgeDirectories(policyForm.company_id);
  }, [fetchKnowledgeDirectories, policyForm.company_id, policyForm.user_type, showPolicyModal]);

  useEffect(() => {
    const createNeedsTree = showCreateModal && String(newUser.user_type || 'normal') === 'sub_admin';
    const policyNeedsTree = showPolicyModal && String(policyForm.user_type || 'normal') === 'sub_admin';
    if (createNeedsTree || policyNeedsTree) return;
    setKbDirectoryNodes([]);
    setKbDirectoryError(null);
    setKbDirectoryCreateError(null);
    setKbDirectoryCreatingRoot(false);
  }, [newUser.user_type, policyForm.user_type, showCreateModal, showPolicyModal]);

  const filteredUsers = useMemo(() => filterUsers(allUsers, filters), [allUsers, filters]);
  const groupedUsers = useMemo(() => groupUsersByDepartment(filteredUsers), [filteredUsers]);

  const subAdminOptions = useMemo(() => {
    const companyId = newUser.company_id ? Number(newUser.company_id) : null;
    return (Array.isArray(allUsers) ? allUsers : [])
      .filter((item) => String(item?.role || '') === 'sub_admin')
      .filter((item) => String(item?.status || '').toLowerCase() === 'active')
      .filter((item) => (companyId == null ? true : Number(item?.company_id) === companyId))
      .map((item) => ({
        value: String(item?.user_id || ''),
        label: buildUserDisplayLabel(item),
        username: String(item?.username || ''),
        company_id: item?.company_id ?? null,
      }))
      .filter((item) => item.value);
  }, [allUsers, newUser.company_id]);

  const policySubAdminOptions = useMemo(() => {
    const companyId = policyForm.company_id ? Number(policyForm.company_id) : null;
    const currentUserId = String(policyUser?.user_id || '');
    return (Array.isArray(allUsers) ? allUsers : [])
      .filter((item) => String(item?.role || '') === 'sub_admin')
      .filter((item) => String(item?.status || '').toLowerCase() === 'active')
      .filter((item) => String(item?.user_id || '') !== currentUserId)
      .filter((item) => (companyId == null ? true : Number(item?.company_id) === companyId))
      .map((item) => ({
        value: String(item?.user_id || ''),
        label: buildUserDisplayLabel(item),
        username: String(item?.username || ''),
        company_id: item?.company_id ?? null,
      }))
      .filter((item) => item.value);
  }, [allUsers, policyForm.company_id, policyUser?.user_id]);

  const managedKbRootInvalid = useMemo(
    () =>
      String(policyForm.user_type || 'normal') === 'sub_admin'
      && !!String(policyUser?.managed_kb_root_node_id || '').trim()
      && !String(policyUser?.managed_kb_root_path || '').trim()
      && !nodeExistsInTree(kbDirectoryNodes, policyForm.managed_kb_root_node_id),
    [
      kbDirectoryNodes,
      policyForm.managed_kb_root_node_id,
      policyForm.user_type,
      policyUser?.managed_kb_root_node_id,
      policyUser?.managed_kb_root_path,
    ]
  );

  const handleOpenCreateModal = useCallback(() => {
    setCreateUserError(null);
    setKbDirectoryCreateError(null);
    setShowCreateModal(true);
  }, []);

  const handleCloseCreateModal = useCallback(() => {
    setShowCreateModal(false);
    setNewUser(DEFAULT_NEW_USER);
    setCreateUserError(null);
    setKbDirectoryCreateError(null);
  }, []);

  const setNewUserField = useCallback((field, value) => {
    setCreateUserError(null);
    setKbDirectoryCreateError(null);
    setNewUser((prev) => {
      const next = { ...prev, [field]: value };
      if (field === 'company_id') {
        next.department_id = '';
        next.manager_user_id = '';
        next.managed_kb_root_node_id = '';
      }
      return normalizeDraftByUserType(next);
    });
  }, []);

  const toggleNewUserGroup = useCallback((groupId, checked) => {
    setCreateUserError(null);
    setNewUser((prev) => {
      if (String(prev.user_type || 'normal') !== 'sub_admin') return { ...prev, group_ids: [] };
      const groupIds = Array.isArray(prev.group_ids) ? prev.group_ids : [];
      if (checked) {
        if (groupIds.includes(groupId)) return prev;
        return { ...prev, group_ids: [...groupIds, groupId] };
      }
      return { ...prev, group_ids: groupIds.filter((id) => id !== groupId) };
    });
  }, []);

  const createRootDirectory = useCallback(
    async ({ companyId, name, onCreated }) => {
      const normalizedCompanyId = companyId == null || companyId === '' ? null : Number(companyId);
      if (normalizedCompanyId == null || !Number.isFinite(normalizedCompanyId)) {
        setKbDirectoryCreateError('请先选择公司');
        return null;
      }
      const cleanName = String(name || '').trim();
      if (!cleanName) {
        setKbDirectoryCreateError('请输入顶级目录名称');
        return null;
      }
      try {
        setKbDirectoryCreatingRoot(true);
        setKbDirectoryCreateError(null);
        const response = await knowledgeApi.createKnowledgeDirectory(
          { name: cleanName, parent_id: null },
          { companyId: isAdminUser ? normalizedCompanyId : undefined }
        );
        const createdNodeId = String(response?.node?.id || '').trim();
        await fetchKnowledgeDirectories(normalizedCompanyId);
        if (createdNodeId && typeof onCreated === 'function') {
          onCreated(createdNodeId);
        }
        return createdNodeId || null;
      } catch (err) {
        setKbDirectoryCreateError(mapUserManagementErrorMessage(err?.message || '创建顶级目录失败'));
        return null;
      } finally {
        setKbDirectoryCreatingRoot(false);
      }
    },
    [fetchKnowledgeDirectories, isAdminUser]
  );

  const handleCreateModalRootDirectory = useCallback(
    async (name) =>
      createRootDirectory({
        companyId: newUser.company_id,
        name,
        onCreated: (nodeId) => setNewUser((prev) => ({ ...prev, managed_kb_root_node_id: nodeId })),
      }),
    [createRootDirectory, newUser.company_id]
  );

  const handlePolicyRootDirectory = useCallback(
    async (name) =>
      createRootDirectory({
        companyId: policyForm.company_id,
        name,
        onCreated: (nodeId) => setPolicyFormState((prev) => ({ ...prev, managed_kb_root_node_id: nodeId })),
      }),
    [createRootDirectory, policyForm.company_id]
  );

  const handleCreateUser = useCallback(
    async (event) => {
      event.preventDefault();
      setCreateUserError(null);
      if (orgDirectoryError) {
        setCreateUserError(orgDirectoryError);
        return;
      }
      try {
        const userType = String(newUser.user_type || 'normal') === 'sub_admin' ? 'sub_admin' : 'normal';
        const payload = {
          ...newUser,
          full_name: String(newUser.full_name || '').trim() || null,
          manager_user_id:
            userType === 'sub_admin' ? null : String(newUser.manager_user_id || '').trim() || null,
          role: userType === 'sub_admin' ? 'sub_admin' : 'viewer',
          group_ids: userType === 'sub_admin' ? normalizeGroupIds(newUser.group_ids) : [],
          managed_kb_root_node_id:
            userType === 'sub_admin' ? String(newUser.managed_kb_root_node_id || '').trim() || null : null,
          company_id: newUser.company_id ? Number(newUser.company_id) : null,
          department_id: newUser.department_id ? Number(newUser.department_id) : null,
          max_login_sessions: Number(newUser.max_login_sessions),
          idle_timeout_minutes: Number(newUser.idle_timeout_minutes),
        };
        delete payload.user_type;

        if (!payload.company_id || !payload.department_id) {
          setCreateUserError(COMPANY_REQUIRED_MESSAGE);
          return;
        }
        if (payload.role === 'viewer' && !payload.manager_user_id) {
          setCreateUserError(SUB_ADMIN_REQUIRED_MESSAGE);
          return;
        }
        if (payload.role === 'sub_admin' && !payload.managed_kb_root_node_id) {
          setCreateUserError(KB_ROOT_REQUIRED_MESSAGE);
          return;
        }
        if (
          payload.role === 'sub_admin'
          && !nodeExistsInTree(kbDirectoryNodes, payload.managed_kb_root_node_id)
        ) {
          setCreateUserError(KB_ROOT_REBIND_MESSAGE);
          return;
        }

        await usersApi.create(payload);
        handleCloseCreateModal();
        fetchUsers();
      } catch (err) {
        setCreateUserError(mapUserManagementErrorMessage(err?.message || '创建用户失败'));
      }
    },
    [fetchUsers, handleCloseCreateModal, kbDirectoryNodes, newUser, orgDirectoryError]
  );

  const handleDeleteUser = useCallback(
    async (userId) => {
      if (!window.confirm('确定要删除该用户吗？')) return;
      try {
        await usersApi.remove(userId);
        fetchUsers();
      } catch (err) {
        setError(mapUserManagementErrorMessage(err?.message || '删除用户失败'));
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
      setDisableUserError(mapUserManagementErrorMessage(err?.message || '禁用用户失败'));
    } finally {
      setStatusUpdatingUserId(null);
    }
  }, [disableMode, disableTargetUser, disableUntilDate, fetchUsers, handleCloseDisableUserModal]);

  const handleToggleUserStatus = useCallback(
    async (targetUser) => {
      if (!targetUser?.user_id) return;
      if (String(targetUser?.username || '').toLowerCase() === 'admin') return;

      const disabledNow = isUserLoginDisabled(targetUser);
      if (!disabledNow) {
        setDisableTargetUser(targetUser);
        setDisableMode('immediate');
        setDisableUntilDate('');
        setDisableUserError(null);
        setShowDisableUserModal(true);
        return;
      }

      const payload = { status: 'active', disable_login_enabled: false, disable_login_until_ms: null };
      try {
        setStatusUpdatingUserId(targetUser.user_id);
        await usersApi.update(targetUser.user_id, payload);
        await fetchUsers();
      } catch (err) {
        setError(mapUserManagementErrorMessage(err?.message || '切换用户状态失败'));
      } finally {
        setStatusUpdatingUserId(null);
      }
    },
    [fetchUsers]
  );

  const canResetPasswordForUser = useCallback(
    (targetUser) => {
      const targetUserId = String(targetUser?.user_id || '');
      if (!targetUserId) return false;
      if (isAdminUser) return true;
      if (!isSubAdminUser) return false;
      if (targetUserId === currentUserId) return true;
      return (
        String(targetUser?.role || '') === 'viewer'
        && String(targetUser?.manager_user_id || '') === currentUserId
      );
    },
    [currentUserId, isAdminUser, isSubAdminUser]
  );

  const handleOpenResetPassword = useCallback((targetUser) => {
    if (!canResetPasswordForUser(targetUser)) return;
    setResetPasswordUser(targetUser);
    setResetPasswordValue('');
    setResetPasswordConfirm('');
    setResetPasswordError(null);
    setShowResetPasswordModal(true);
  }, [canResetPasswordForUser]);

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
      setResetPasswordError(mapUserManagementErrorMessage(err?.message || '修改密码失败'));
    } finally {
      setResetPasswordSubmitting(false);
    }
  }, [handleCloseResetPassword, resetPasswordConfirm, resetPasswordUser, resetPasswordValue]);

  const handleOpenPolicyModal = useCallback((targetUser) => {
    const disabledNow = isUserLoginDisabled(targetUser);
    const disableUntilMs = Number(targetUser?.disable_login_until_ms || 0);
    const hasFutureUntil = Number.isFinite(disableUntilMs) && disableUntilMs > Date.now();

    setPolicyUser(targetUser);
    setPolicyError(null);
    setKbDirectoryCreateError(null);
    setPolicyFormState(
      normalizeDraftByUserType({
        full_name: String(targetUser?.full_name || ''),
        company_id: targetUser?.company_id != null ? String(targetUser.company_id) : '',
        department_id: targetUser?.department_id != null ? String(targetUser.department_id) : '',
        manager_user_id: String(targetUser?.manager_user_id || ''),
        user_type: mapRoleToUserType(targetUser?.role),
        managed_kb_root_node_id: String(targetUser?.managed_kb_root_node_id || ''),
        group_ids: Array.isArray(targetUser?.group_ids)
          ? [...targetUser.group_ids]
          : Array.isArray(targetUser?.permission_groups)
            ? targetUser.permission_groups.map((pg) => pg.group_id)
            : [],
        max_login_sessions: Number(targetUser?.max_login_sessions || 3),
        idle_timeout_minutes: Number(targetUser?.idle_timeout_minutes || 120),
        can_change_password: targetUser?.can_change_password !== false,
        disable_account: disabledNow,
        disable_mode: hasFutureUntil ? 'until' : 'immediate',
        disable_until_date: hasFutureUntil ? formatDateForInput(disableUntilMs) : '',
      })
    );
    setShowPolicyModal(true);
  }, []);

  const handleClosePolicyModal = useCallback(() => {
    setShowPolicyModal(false);
    setPolicyUser(null);
    setPolicySubmitting(false);
    setPolicyError(null);
    setPolicyFormState(DEFAULT_POLICY_FORM);
    setKbDirectoryCreateError(null);
  }, []);

  const handleChangePolicyForm = useCallback((nextValue) => {
    setPolicyError(null);
    setKbDirectoryCreateError(null);
    setPolicyFormState((prev) => {
      const draft = typeof nextValue === 'function' ? nextValue(prev) : nextValue;
      const next = normalizeDraftByUserType(draft);
      if (String(next.company_id || '') !== String(prev.company_id || '')) {
        next.department_id = '';
        next.manager_user_id = '';
        next.managed_kb_root_node_id = '';
      }
      return next;
    });
  }, []);

  const handleTogglePolicyGroup = useCallback(
    (groupId, checked) => {
      setPolicyFormState((prev) => {
        if (String(policyUser?.role || '') === 'admin' || String(prev.user_type || 'normal') !== 'sub_admin') {
          return { ...prev, group_ids: [] };
        }
        const current = normalizeGroupIds(prev.group_ids);
        if (checked) {
          if (current.includes(groupId)) return prev;
          return { ...prev, group_ids: [...current, groupId] };
        }
        return { ...prev, group_ids: current.filter((id) => id !== groupId) };
      });
    },
    [policyUser]
  );

  const handleSavePolicy = useCallback(async () => {
    if (!policyUser) return;
    setPolicyError(null);
    if (orgDirectoryError) {
      setPolicyError(orgDirectoryError);
      return;
    }

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

    const isAdminTarget = String(policyUser.role || '') === 'admin';
    const userType = isAdminTarget
      ? 'normal'
      : String(policyForm.user_type || 'normal') === 'sub_admin'
        ? 'sub_admin'
        : 'normal';

    const payload = {
      full_name: String(policyForm.full_name || '').trim(),
      company_id: policyForm.company_id ? Number(policyForm.company_id) : null,
      department_id: policyForm.department_id ? Number(policyForm.department_id) : null,
      manager_user_id:
        isAdminTarget || userType === 'sub_admin'
          ? null
          : String(policyForm.manager_user_id || '').trim() || null,
      role: isAdminTarget ? 'admin' : userType === 'sub_admin' ? 'sub_admin' : 'viewer',
      group_ids:
        isAdminTarget
          ? undefined
          : userType === 'sub_admin'
            ? normalizeGroupIds(policyForm.group_ids)
            : [],
      managed_kb_root_node_id:
        userType === 'sub_admin' ? String(policyForm.managed_kb_root_node_id || '').trim() || null : null,
      max_login_sessions: maxSessions,
      idle_timeout_minutes: idleMinutes,
      can_change_password: !!policyForm.can_change_password,
    };

    if (!payload.company_id || !payload.department_id) {
      setPolicyError(COMPANY_REQUIRED_MESSAGE);
      return;
    }
    if (payload.role === 'viewer' && !payload.manager_user_id) {
      setPolicyError(SUB_ADMIN_REQUIRED_MESSAGE);
      return;
    }
    if (payload.role === 'sub_admin' && !payload.managed_kb_root_node_id) {
      setPolicyError(KB_ROOT_REQUIRED_MESSAGE);
      return;
    }
    if (
      payload.role === 'sub_admin'
      && !nodeExistsInTree(kbDirectoryNodes, payload.managed_kb_root_node_id)
    ) {
      setPolicyError(KB_ROOT_REBIND_MESSAGE);
      return;
    }
    if (isAdminTarget) {
      delete payload.group_ids;
      delete payload.managed_kb_root_node_id;
      delete payload.manager_user_id;
    }

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
      setPolicyError(mapUserManagementErrorMessage(err?.message || '保存登录策略失败'));
    } finally {
      setPolicySubmitting(false);
    }
  }, [fetchUsers, handleClosePolicyModal, kbDirectoryNodes, orgDirectoryError, policyForm, policyUser]);

  const handleAssignGroup = useCallback(
    (targetUser) => {
      if (String(targetUser?.role || '') === 'sub_admin') return;
      if (isSubAdminUser && String(targetUser?.manager_user_id || '') !== String(user?.user_id || '')) return;
      setEditingGroupUser(targetUser);
      const allowedGroupIds = new Set(
        (Array.isArray(availableGroups) ? availableGroups : [])
          .map((group) => normalizeGroupId(group?.group_id))
          .filter((groupId) => groupId != null)
      );
      const groupIds = Array.isArray(targetUser?.group_ids)
        ? targetUser.group_ids
        : (targetUser?.permission_groups || []).map((pg) => pg.group_id);
      const validGroupIds = Array.from(
        new Set(
          (Array.isArray(groupIds) ? groupIds : [])
            .map((groupId) => normalizeGroupId(groupId))
            .filter((groupId) => groupId != null && allowedGroupIds.has(groupId))
        )
      );
      setSelectedGroupIds(validGroupIds);
      setShowGroupModal(true);
    },
    [availableGroups, isSubAdminUser, user?.user_id]
  );

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
      setError(mapUserManagementErrorMessage(err?.message || '保存权限组失败'));
    }
  }, [editingGroupUser, fetchUsers, handleCloseGroupModal, selectedGroupIds]);

  const handleResetFilters = useCallback(() => {
    setFilters(DEFAULT_FILTERS);
  }, []);

  return {
    allUsers,
    loading,
    error,
    isSubAdminUser,
    canManageUsers,
    canCreateUsers: isAdminUser,
    canEditUserPolicy: isAdminUser,
    canResetPasswords: isAdminUser || isSubAdminUser,
    canResetPasswordForUser,
    canToggleUserStatus: isAdminUser,
    canDeleteUsers: isAdminUser,
    canAssignGroups: isSubAdminUser,
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
    orgDirectoryError,
    kbDirectoryNodes,
    kbDirectoryLoading,
    kbDirectoryError,
    kbDirectoryCreateError,
    kbDirectoryCreatingRoot,
    managedKbRootInvalid,
    filteredUsers,
    groupedUsers,
    subAdminOptions,
    policySubAdminOptions,
    setFilters,
    handleChangePolicyForm,
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
    handleTogglePolicyGroup,
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
    handleCreateModalRootDirectory,
    handlePolicyRootDirectory,
  };
};
