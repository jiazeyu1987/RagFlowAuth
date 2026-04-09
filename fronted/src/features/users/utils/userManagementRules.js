import {
  DISABLE_UNTIL_FUTURE_MESSAGE,
  DISABLE_UNTIL_REQUIRED_MESSAGE,
  normalizeGroupId,
  parseDisableUntilDate,
} from './userAccessPolicy';
import { normalizeToolIds } from './toolCatalog';

export const mapRoleToUserType = (role) =>
  (String(role || '') === 'sub_admin' ? 'sub_admin' : 'normal');

export const isUserLoginDisabled = (user, nowMs = Date.now()) => {
  if (!user) return false;
  if (user.login_disabled === true) return true;

  const status = String(user.status || '').toLowerCase();
  if (status && status !== 'active') return true;

  if (user.disable_login_enabled !== true) return false;

  const untilMs = Number(user.disable_login_until_ms || 0);
  if (!Number.isFinite(untilMs) || untilMs <= 0) return true;
  return nowMs < untilMs;
};

export const formatDateForInput = (ms) => {
  if (!ms) return '';
  const date = new Date(Number(ms));
  if (!Number.isFinite(date.getTime())) return '';

  const year = date.getFullYear();
  const month = `${date.getMonth() + 1}`.padStart(2, '0');
  const day = `${date.getDate()}`.padStart(2, '0');
  return `${year}-${month}-${day}`;
};

export const buildDisableUserPayload = ({ mode, untilDate, nowMs = Date.now() }) => {
  if (String(mode || 'immediate') !== 'until') {
    return {
      status: 'inactive',
      disable_login_enabled: false,
      disable_login_until_ms: null,
    };
  }

  const untilMs = parseDisableUntilDate(untilDate);
  if (!untilMs) {
    throw new Error(DISABLE_UNTIL_REQUIRED_MESSAGE);
  }
  if (untilMs <= nowMs) {
    throw new Error(DISABLE_UNTIL_FUTURE_MESSAGE);
  }

  return {
    status: 'active',
    disable_login_enabled: true,
    disable_login_until_ms: untilMs,
  };
};

export const buildEnableUserPayload = () => ({
  status: 'active',
  disable_login_enabled: false,
  disable_login_until_ms: null,
});

export const canResetManagedUserPassword = ({ actorRole, actorUserId, targetUser }) => {
  const normalizedActorRole = String(actorRole || '');
  const normalizedActorUserId = String(actorUserId || '');
  const targetUserId = String(targetUser?.user_id || '');

  if (!targetUserId) return false;
  if (normalizedActorRole === 'admin') return true;
  if (normalizedActorRole !== 'sub_admin') return false;
  if (targetUserId === normalizedActorUserId) return true;

  return (
    String(targetUser?.role || '') === 'viewer'
    && String(targetUser?.manager_user_id || '') === normalizedActorUserId
  );
};

export const canAssignManagedUserGroups = ({ actorRole, actorUserId, targetUser }) => {
  if (String(targetUser?.role || '') === 'sub_admin') return false;
  if (String(actorRole || '') === 'admin') return true;
  if (String(actorRole || '') !== 'sub_admin') return false;

  return String(targetUser?.manager_user_id || '') === String(actorUserId || '');
};

export const canAssignManagedUserTools = ({ actorRole, actorUserId, targetUser }) => {
  if (String(targetUser?.role || '') !== 'viewer') return false;
  if (String(actorRole || '') !== 'sub_admin') return false;

  return String(targetUser?.manager_user_id || '') === String(actorUserId || '');
};

export const getValidAssignableGroupIds = ({ availableGroups, groupIds }) => {
  const allowedGroupIds = new Set(
    (Array.isArray(availableGroups) ? availableGroups : [])
      .map((group) => normalizeGroupId(group?.group_id))
      .filter((groupId) => groupId != null)
  );

  return Array.from(
    new Set(
      (Array.isArray(groupIds) ? groupIds : [])
        .map((groupId) => normalizeGroupId(groupId))
        .filter((groupId) => groupId != null && allowedGroupIds.has(groupId))
    )
  );
};

export const getValidAssignableToolIds = ({ availableToolIds, toolIds }) => {
  const allowedToolIds = new Set(normalizeToolIds(availableToolIds));
  return normalizeToolIds(toolIds).filter((toolId) => allowedToolIds.has(toolId));
};
