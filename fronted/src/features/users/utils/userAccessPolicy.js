export const COMPANY_REQUIRED_MESSAGE = '请选择公司和部门';
export const SUB_ADMIN_REQUIRED_MESSAGE = '请选择归属子管理员';
export const KB_ROOT_REQUIRED_MESSAGE = '请选择子管理员负责的知识库目录';
export const KB_ROOT_REBIND_MESSAGE = '当前负责目录已失效，请先重新绑定有效目录';
export const MAX_LOGIN_SESSIONS_MESSAGE = '可登录会话数需为 1-1000 的整数';
export const IDLE_TIMEOUT_MESSAGE = '空闲超时需为 1-43200 分钟的整数';
export const DISABLE_UNTIL_REQUIRED_MESSAGE = '请选择禁用到期日期';
export const DISABLE_UNTIL_FUTURE_MESSAGE = '禁用到期时间必须晚于当前时间';

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
  };

  if (userType !== 'sub_admin') {
    next.managed_kb_root_node_id = '';
    next.group_ids = [];
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
    full_name: normalizeNullableString(draft?.full_name),
    manager_user_id: userType === 'sub_admin' ? null : normalizeNullableString(draft?.manager_user_id),
    role: userType === 'sub_admin' ? 'sub_admin' : 'viewer',
    group_ids: userType === 'sub_admin' ? normalizeGroupIds(draft?.group_ids) : [],
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
    managed_kb_root_node_id:
      userType === 'sub_admin' ? normalizeNullableString(policyForm?.managed_kb_root_node_id) : null,
    max_login_sessions: Number(policyForm?.max_login_sessions),
    idle_timeout_minutes: Number(policyForm?.idle_timeout_minutes),
    can_change_password: !!policyForm?.can_change_password,
  };

  if (isAdminTarget) {
    delete payload.group_ids;
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
