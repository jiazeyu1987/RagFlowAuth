import { normalizeToolIds } from './toolCatalog';

export const COMPANY_REQUIRED_MESSAGE = '\u8bf7\u9009\u62e9\u516c\u53f8\u548c\u90e8\u95e8';
export const SUB_ADMIN_REQUIRED_MESSAGE = '\u8bf7\u9009\u62e9\u5f52\u5c5e\u5b50\u7ba1\u7406\u5458';
export const KB_ROOT_REQUIRED_MESSAGE = '\u8bf7\u9009\u62e9\u5b50\u7ba1\u7406\u5458\u8d1f\u8d23\u7684\u77e5\u8bc6\u5e93\u76ee\u5f55';
export const KB_ROOT_REBIND_MESSAGE = '\u5f53\u524d\u8d1f\u8d23\u76ee\u5f55\u5df2\u5931\u6548\uff0c\u8bf7\u5148\u91cd\u65b0\u7ed1\u5b9a\u6709\u6548\u76ee\u5f55';
export const MAX_LOGIN_SESSIONS_MESSAGE = '\u53ef\u767b\u5f55\u4f1a\u8bdd\u6570\u9700\u4e3a 1-1000 \u7684\u6574\u6570';
export const IDLE_TIMEOUT_MESSAGE = '\u7a7a\u95f2\u8d85\u65f6\u9700\u4e3a 1-43200 \u5206\u949f\u7684\u6574\u6570';
export const DISABLE_UNTIL_REQUIRED_MESSAGE = '\u8bf7\u9009\u62e9\u7981\u7528\u5230\u671f\u65e5\u671f';
export const DISABLE_UNTIL_FUTURE_MESSAGE = '\u7981\u7528\u5230\u671f\u65f6\u95f4\u5fc5\u987b\u665a\u4e8e\u5f53\u524d\u65f6\u95f4';
export const EMPLOYEE_USER_ID_REQUIRED_MESSAGE = '\u8bf7\u4ece\u59d3\u540d\u4e0b\u62c9\u4e2d\u9009\u62e9\u7ec4\u7ec7\u540c\u4e8b';
export const USERNAME_REQUIRED_MESSAGE = '\u8bf7\u8f93\u5165\u7528\u6237\u8d26\u53f7';
export const EMPLOYEE_PROFILE_REQUIRED_MESSAGE = '\u8bf7\u4ece\u4e0b\u62c9\u9009\u62e9\u5458\u5de5\u4ee5\u56de\u586b\u59d3\u540d\u3001\u516c\u53f8\u548c\u90e8\u95e8';

const normalizeUserType = (value) =>
  String(value || 'normal') === 'sub_admin' ? 'sub_admin' : 'normal';

const normalizeNullableString = (value) => {
  const normalized = String(value || '').trim();
  return normalized || null;
};

const normalizeNullableNumber = (value) => {
  const normalized = String(value ?? '').trim();
  return normalized ? Number(normalized) : null;
};

export const parseDisableUntilDate = (dateText) => {
  const raw = String(dateText || '').trim();
  if (!raw) return null;
  const date = new Date(`${raw}T23:59:59`);
  const ms = date.getTime();
  return Number.isFinite(ms) ? ms : null;
};

export const normalizeGroupId = (value) => {
  const groupId = Number(value);
  return Number.isInteger(groupId) && groupId > 0 ? groupId : null;
};

export const normalizeGroupIds = (values) =>
  Array.from(
    new Set(
      (Array.isArray(values) ? values : [])
        .map((value) => normalizeGroupId(value))
        .filter((groupId) => groupId != null)
    )
  );

export const normalizeDraftByUserType = (draft) => {
  const userType = normalizeUserType(draft?.user_type);
  const next = {
    ...draft,
    user_type: userType,
    group_ids: normalizeGroupIds(draft?.group_ids),
    tool_ids: normalizeToolIds(draft?.tool_ids),
  };

  if (userType !== 'sub_admin') {
    next.managed_kb_root_node_id = '';
    next.group_ids = [];
    next.tool_ids = [];
  } else {
    next.manager_user_id = '';
  }

  return next;
};

export const nodeExistsInTree = (nodes, nodeId) =>
  (Array.isArray(nodes) ? nodes : []).some((node) => String(node?.id || '') === String(nodeId || ''));

export const buildCreateUserPayload = (draft) => {
  const userType = normalizeUserType(draft?.user_type);
  const payload = {
    ...draft,
    username: normalizeNullableString(draft?.username),
    employee_user_id: normalizeNullableString(draft?.employee_user_id),
    full_name: normalizeNullableString(draft?.full_name),
    manager_user_id: userType === 'sub_admin' ? null : normalizeNullableString(draft?.manager_user_id),
    role: userType === 'sub_admin' ? 'sub_admin' : 'viewer',
    group_ids: userType === 'sub_admin' ? normalizeGroupIds(draft?.group_ids) : [],
    tool_ids: userType === 'sub_admin' ? normalizeToolIds(draft?.tool_ids) : [],
    managed_kb_root_node_id:
      userType === 'sub_admin' ? normalizeNullableString(draft?.managed_kb_root_node_id) : null,
    company_id: normalizeNullableNumber(draft?.company_id),
    department_id: normalizeNullableNumber(draft?.department_id),
    max_login_sessions: Number(draft?.max_login_sessions),
    idle_timeout_minutes: Number(draft?.idle_timeout_minutes),
  };

  delete payload.user_type;
  return payload;
};

export const validateCreateUserEmployeeBindingPayload = (payload) => {
  const employeeUserId = normalizeNullableString(payload?.employee_user_id);
  const username = normalizeNullableString(payload?.username);
  const fullName = normalizeNullableString(payload?.full_name);

  if (!employeeUserId) {
    throw new Error(EMPLOYEE_USER_ID_REQUIRED_MESSAGE);
  }
  if (!username) {
    throw new Error(USERNAME_REQUIRED_MESSAGE);
  }
  if (!fullName || payload?.company_id == null || payload?.department_id == null) {
    throw new Error(EMPLOYEE_PROFILE_REQUIRED_MESSAGE);
  }

  return {
    ...payload,
    username,
    employee_user_id: employeeUserId,
    full_name: fullName,
  };
};

export const buildPolicyUpdatePayload = ({ policyForm, policyUser }) => {
  const isAdminTarget = String(policyUser?.role || '') === 'admin';
  const userType = isAdminTarget ? 'normal' : normalizeUserType(policyForm?.user_type);

  const payload = {
    full_name: normalizeNullableString(policyForm?.full_name),
    company_id: normalizeNullableNumber(policyForm?.company_id),
    department_id: normalizeNullableNumber(policyForm?.department_id),
    manager_user_id:
      isAdminTarget || userType === 'sub_admin' ? null : normalizeNullableString(policyForm?.manager_user_id),
    role: isAdminTarget ? 'admin' : userType === 'sub_admin' ? 'sub_admin' : 'viewer',
    group_ids:
      isAdminTarget ? undefined : userType === 'sub_admin' ? normalizeGroupIds(policyForm?.group_ids) : [],
    tool_ids:
      isAdminTarget ? undefined : userType === 'sub_admin' ? normalizeToolIds(policyForm?.tool_ids) : undefined,
    managed_kb_root_node_id:
      userType === 'sub_admin' ? normalizeNullableString(policyForm?.managed_kb_root_node_id) : null,
    max_login_sessions: Number(policyForm?.max_login_sessions),
    idle_timeout_minutes: Number(policyForm?.idle_timeout_minutes),
    can_change_password: !!policyForm?.can_change_password,
  };

  if (isAdminTarget) {
    delete payload.group_ids;
    delete payload.tool_ids;
    delete payload.managed_kb_root_node_id;
    delete payload.manager_user_id;
  }

  return payload;
};

export const validateManagedUserPayload = ({ payload, kbDirectoryNodes }) => {
  const maxSessions = Number(payload?.max_login_sessions);
  const idleMinutes = Number(payload?.idle_timeout_minutes);

  if (!Number.isInteger(maxSessions) || maxSessions < 1 || maxSessions > 1000) {
    throw new Error(MAX_LOGIN_SESSIONS_MESSAGE);
  }

  if (!Number.isInteger(idleMinutes) || idleMinutes < 1 || idleMinutes > 43200) {
    throw new Error(IDLE_TIMEOUT_MESSAGE);
  }

  if (!payload?.company_id || !payload?.department_id) {
    throw new Error(COMPANY_REQUIRED_MESSAGE);
  }

  if (payload?.role === 'viewer' && !payload?.manager_user_id) {
    throw new Error(SUB_ADMIN_REQUIRED_MESSAGE);
  }

  if (payload?.role === 'sub_admin' && !payload?.managed_kb_root_node_id) {
    throw new Error(KB_ROOT_REQUIRED_MESSAGE);
  }

  if (
    payload?.role === 'sub_admin'
    && !nodeExistsInTree(kbDirectoryNodes, payload?.managed_kb_root_node_id)
  ) {
    throw new Error(KB_ROOT_REBIND_MESSAGE);
  }

  return payload;
};

export const applyPolicyDisableState = ({ payload, policyForm, nowMs = Date.now() }) => {
  if (!policyForm?.disable_account) {
    return {
      ...payload,
      status: 'active',
      disable_login_enabled: false,
      disable_login_until_ms: null,
    };
  }

  if (policyForm?.disable_mode === 'until') {
    const untilMs = parseDisableUntilDate(policyForm?.disable_until_date);
    if (!untilMs) {
      throw new Error(DISABLE_UNTIL_REQUIRED_MESSAGE);
    }
    if (untilMs <= nowMs) {
      throw new Error(DISABLE_UNTIL_FUTURE_MESSAGE);
    }
    return {
      ...payload,
      status: 'active',
      disable_login_enabled: true,
      disable_login_until_ms: untilMs,
    };
  }

  return {
    ...payload,
    status: 'inactive',
    disable_login_enabled: false,
    disable_login_until_ms: null,
  };
};
