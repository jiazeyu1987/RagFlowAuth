const UNASSIGNED_DEPARTMENT = '未分配部门';

const getUserGroupIds = (user) => {
  if (Array.isArray(user?.group_ids)) return user.group_ids;
  if (Array.isArray(user?.permission_groups)) return user.permission_groups.map((group) => group.group_id);
  return [];
};

const getVisiblePermissionGroups = (user) =>
  Array.isArray(user?.permission_groups)
    ? user.permission_groups.filter((group) => String(group?.group_name || '').trim())
    : [];

const hasAssignedPermissionGroups = (user) => getVisiblePermissionGroups(user).length > 0;

export const buildListParams = (filters) => {
  const f = filters || {};
  const params = {};

  if (f.q && String(f.q).trim()) params.q = String(f.q).trim();
  if (f.company_id) params.company_id = String(f.company_id);
  if (f.department_id) params.department_id = String(f.department_id);
  if (f.status) params.status = String(f.status);
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
};

export const filterUsers = (allUsers, filters) => {
  const users = Array.isArray(allUsers) ? allUsers : [];
  const f = filters || {};

  const q = String(f.q || '').trim();
  const companyId = f.company_id ? Number(f.company_id) : null;
  const departmentId = f.department_id ? Number(f.department_id) : null;
  const status = f.status || '';
  const groupId = f.group_id ? Number(f.group_id) : null;
  const assignmentStatus = String(f.assignment_status || '').trim();

  let fromMs = null;
  let toMs = null;
  if (f.created_from) {
    const ms = new Date(`${f.created_from}T00:00:00`).getTime();
    fromMs = Number.isNaN(ms) ? null : ms;
  }
  if (f.created_to) {
    const ms = new Date(`${f.created_to}T23:59:59.999`).getTime();
    toMs = Number.isNaN(ms) ? null : ms;
  }

  return users.filter((user) => {
    const username = String(user?.username || '');
    const fullName = String(user?.full_name || '');
    const email = String(user?.email || '');

    if (q && !username.includes(q) && !fullName.includes(q) && !email.includes(q)) return false;
    if (companyId != null && user?.company_id !== companyId) return false;
    if (departmentId != null && user?.department_id !== departmentId) return false;
    if (status && user?.status !== status) return false;
    if (groupId != null) {
      const groupIds = getUserGroupIds(user);
      if (!Array.isArray(groupIds) || !groupIds.some((id) => Number(id) === groupId)) return false;
    }
    if (assignmentStatus === 'assigned' && !hasAssignedPermissionGroups(user)) return false;
    if (assignmentStatus === 'unassigned' && hasAssignedPermissionGroups(user)) return false;
    if (fromMs != null && Number(user?.created_at_ms || 0) < fromMs) return false;
    if (toMs != null && Number(user?.created_at_ms || 0) > toMs) return false;
    return true;
  });
};

export const groupUsersByDepartment = (users) => {
  const groups = new Map();
  (Array.isArray(users) ? users : []).forEach((user) => {
    const key = user?.department_id != null ? String(user.department_id) : '__unassigned__';
    const departmentName = user?.department_name || UNASSIGNED_DEPARTMENT;
    if (!groups.has(key)) {
      groups.set(key, {
        key,
        departmentId: user?.department_id ?? null,
        departmentName,
        users: [],
      });
    }
    groups.get(key).users.push(user);
  });

  return Array.from(groups.values()).sort((a, b) => {
    if (a.departmentName === UNASSIGNED_DEPARTMENT) return 1;
    if (b.departmentName === UNASSIGNED_DEPARTMENT) return -1;
    return a.departmentName.localeCompare(b.departmentName, 'zh-CN');
  });
};
