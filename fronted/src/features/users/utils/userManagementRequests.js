import {
  applyPolicyDisableState,
  buildCreateUserPayload,
  buildPolicyUpdatePayload,
  validateManagedUserPayload,
} from './userAccessPolicy';
import { parseRootDirectoryCreationInput } from './userKnowledgeDirectories';
import { buildDisableUserPayload, buildEnableUserPayload } from './userManagementRules';

export const buildCreateUserRequest = ({ draft, kbDirectoryNodes }) =>
  validateManagedUserPayload({
    payload: buildCreateUserPayload(draft),
    kbDirectoryNodes,
  });

export const buildPolicyUpdateRequest = ({ policyForm, policyUser, kbDirectoryNodes, nowMs }) =>
  applyPolicyDisableState({
    payload: validateManagedUserPayload({
      payload: buildPolicyUpdatePayload({ policyForm, policyUser }),
      kbDirectoryNodes,
    }),
    policyForm,
    ...(nowMs == null ? {} : { nowMs }),
  });

export const parseRootDirectoryCreateRequest = ({ companyId, name, isAdminUser }) => {
  const parsed = parseRootDirectoryCreationInput({ companyId, name });
  if (parsed.errorCode) return parsed;

  return {
    errorCode: null,
    normalizedCompanyId: parsed.normalizedCompanyId,
    payload: {
      name: parsed.cleanName,
      parent_id: null,
    },
    requestOptions: {
      companyId: isAdminUser ? parsed.normalizedCompanyId : undefined,
    },
  };
};

export const buildDisableUserUpdateRequest = ({ mode, untilDate, nowMs }) =>
  buildDisableUserPayload({
    mode,
    untilDate,
    ...(nowMs == null ? {} : { nowMs }),
  });

export const buildEnableUserUpdateRequest = () => buildEnableUserPayload();

export const buildResetPasswordUpdateRequest = ({
  resetPasswordUser,
  resetPasswordValue,
  resetPasswordConfirm,
}) => {
  if (!resetPasswordUser?.user_id) {
    return { skipped: true };
  }
  if (!resetPasswordValue) {
    return { errorCode: 'password_required' };
  }
  if (resetPasswordValue !== resetPasswordConfirm) {
    return { errorCode: 'password_mismatch' };
  }

  return {
    userId: resetPasswordUser.user_id,
    password: resetPasswordValue,
  };
};

export const buildGroupAssignmentUpdateRequest = ({ editingGroupUser, selectedGroupIds }) => {
  if (!editingGroupUser?.user_id) {
    return { skipped: true };
  }

  return {
    userId: editingGroupUser.user_id,
    payload: {
      group_ids: selectedGroupIds,
    },
  };
};
