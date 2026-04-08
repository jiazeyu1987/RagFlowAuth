const VALID_SCOPES = new Set(['all', 'set', 'none']);

export const DEFAULT_AUTH_PERMISSIONS = Object.freeze({
  can_upload: false,
  can_review: false,
  can_download: false,
  can_copy: false,
  can_delete: false,
  can_manage_kb_directory: false,
  can_view_kb_config: false,
  can_view_tools: false,
  accessible_tools: Object.freeze([]),
});

export const DEFAULT_AUTH_CAPABILITIES = Object.freeze({});

const EMPTY_CAPABILITY = Object.freeze({
  scope: 'none',
  targets: Object.freeze([]),
});

const isPlainObject = (value) => !!value && typeof value === 'object' && !Array.isArray(value);

const assertPlainObject = (value, errorCode) => {
  if (!isPlainObject(value)) {
    throw new Error(errorCode);
  }
  return value;
};

const normalizeStringList = (value, errorCode) => {
  if (!Array.isArray(value)) {
    throw new Error(errorCode);
  }

  const seen = new Set();
  const normalized = [];

  for (const item of value) {
    if (typeof item !== 'string') {
      continue;
    }

    const clean = item.trim();
    if (!clean || seen.has(clean)) {
      continue;
    }

    seen.add(clean);
    normalized.push(clean);
  }

  return normalized;
};

export const normalizePermissions = (value) => {
  const raw = assertPlainObject(value, 'auth_user_invalid_permissions');

  return {
    can_upload: Boolean(raw.can_upload),
    can_review: Boolean(raw.can_review),
    can_download: Boolean(raw.can_download),
    can_copy: Boolean(raw.can_copy),
    can_delete: Boolean(raw.can_delete),
    can_manage_kb_directory: Boolean(raw.can_manage_kb_directory),
    can_view_kb_config: Boolean(raw.can_view_kb_config),
    can_view_tools: Boolean(raw.can_view_tools),
    accessible_tools: normalizeStringList(raw.accessible_tools, 'auth_user_invalid_permissions'),
  };
};

const normalizeCapabilityEntry = (value) => {
  const raw = assertPlainObject(value, 'auth_user_invalid_capabilities');
  const scope = String(raw.scope || '').trim().toLowerCase();

  if (!VALID_SCOPES.has(scope)) {
    throw new Error('auth_user_invalid_capabilities');
  }

  const targets = raw.targets === undefined
    ? []
    : normalizeStringList(raw.targets, 'auth_user_invalid_capabilities');

  return {
    scope,
    targets: scope === 'set' ? targets : [],
  };
};

export const normalizeCapabilities = (value) => {
  const raw = assertPlainObject(value, 'auth_user_invalid_capabilities');
  const normalized = {};

  for (const [resource, actions] of Object.entries(raw)) {
    const actionMap = assertPlainObject(actions, 'auth_user_invalid_capabilities');
    normalized[resource] = {};

    for (const [action, capability] of Object.entries(actionMap)) {
      normalized[resource][action] = normalizeCapabilityEntry(capability);
    }
  }

  return normalized;
};

export const normalizeAuthenticatedUser = (value) => {
  const raw = assertPlainObject(value, 'auth_user_invalid_payload');

  return {
    ...raw,
    permissions: normalizePermissions(raw.permissions),
    capabilities: normalizeCapabilities(raw.capabilities),
    accessible_kb_ids: normalizeStringList(raw.accessible_kb_ids, 'auth_user_invalid_accessible_kb_ids'),
  };
};

export const canWithCapabilities = (capabilities, resource, action, target = null) => {
  if (!resource || !action) {
    return false;
  }

  const capability = capabilities?.[resource]?.[action] || EMPTY_CAPABILITY;
  if (capability.scope === 'all') {
    return true;
  }
  if (capability.scope !== 'set') {
    return false;
  }

  const cleanTarget = String(target ?? '').trim();
  if (!cleanTarget) {
    return capability.targets.length > 0;
  }

  return capability.targets.includes(cleanTarget);
};

export const hasAnyRole = (user, roles) => {
  if (!user) {
    return false;
  }
  if (Array.isArray(roles)) {
    return roles.includes(user.role);
  }
  return user.role === roles;
};

const normalizePermissionRequirements = ({ permission, permissions }) => {
  if (Array.isArray(permissions) && permissions.length > 0) {
    return permissions;
  }
  if (permission) {
    return [permission];
  }
  return [];
};

const isPermissionAllowed = (capabilities, item) => {
  const resource = typeof item?.resource === 'string' ? item.resource : '';
  const action = typeof item?.action === 'string' ? item.action : '';

  if (!resource || !action) {
    return false;
  }

  return canWithCapabilities(capabilities, resource, action, item?.target ?? null);
};

export const isAuthorized = ({
  user,
  capabilities,
  allowedRoles,
  permission,
  permissions,
  anyPermissions,
}) => {
  if (!user) {
    return false;
  }

  if (allowedRoles && !hasAnyRole(user, allowedRoles)) {
    return false;
  }

  if (Array.isArray(anyPermissions) && anyPermissions.length > 0) {
    const hasAnyPermission = anyPermissions.some((item) => isPermissionAllowed(capabilities, item));
    if (!hasAnyPermission) {
      return false;
    }
  }

  return normalizePermissionRequirements({ permission, permissions }).every((item) => (
    isPermissionAllowed(capabilities, item)
  ));
};
