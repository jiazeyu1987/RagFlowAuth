const UNASSIGNED_DEPARTMENT = '未分配部门';

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

  return users.filter((u) => {
    const username = String(u?.username || '');
    const fullName = String(u?.full_name || '');
    const email = String(u?.email || '');
    if (q && !username.includes(q) && !fullName.includes(q) && !email.includes(q)) return false;
    if (companyId != null && u?.company_id !== companyId) return false;
    if (departmentId != null && u?.department_id !== departmentId) return false;
    if (status && u?.status !== status) return false;
    if (groupId != null) {
      const gids = u?.group_ids || (u?.permission_groups || []).map((pg) => pg.group_id);
      if (!Array.isArray(gids) || !gids.includes(groupId)) return false;
    }
    if (fromMs != null && Number(u?.created_at_ms || 0) < fromMs) return false;
    if (toMs != null && Number(u?.created_at_ms || 0) > toMs) return false;
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
