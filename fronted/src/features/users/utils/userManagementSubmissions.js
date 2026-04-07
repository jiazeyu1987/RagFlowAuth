import {
  buildCreateUserRequest,
  buildDisableUserUpdateRequest,
  buildEnableUserUpdateRequest,
  buildGroupAssignmentUpdateRequest,
  buildPolicyUpdateRequest,
  parseRootDirectoryCreateRequest,
  buildResetPasswordUpdateRequest,
} from './userManagementRequests';

export const prepareCreateUserSubmission = ({ draft, kbDirectoryNodes, orgDirectoryError }) => {
  if (orgDirectoryError) {
    return { errorMessage: orgDirectoryError };
  }

  return {
    payload: buildCreateUserRequest({
      draft,
      kbDirectoryNodes,
    }),
  };
};

export const preparePolicyUpdateSubmission = ({
  policyUser,
  policyForm,
  kbDirectoryNodes,
  orgDirectoryError,
}) => {
  if (!policyUser) {
    return { skipped: true };
  }
  if (orgDirectoryError) {
    return { errorMessage: orgDirectoryError };
  }

  return {
    userId: policyUser.user_id,
    payload: buildPolicyUpdateRequest({
      policyForm,
      policyUser,
      kbDirectoryNodes,
    }),
  };
};

export const prepareDisableUserSubmission = ({ disableTargetUser, disableMode, disableUntilDate }) => {
  if (!disableTargetUser?.user_id) {
    return { skipped: true };
  }

  return {
    userId: disableTargetUser.user_id,
    payload: buildDisableUserUpdateRequest({
      mode: disableMode,
      untilDate: disableUntilDate,
    }),
  };
};

export const prepareEnableUserSubmission = ({ targetUser }) => {
  if (!targetUser?.user_id) {
    return { skipped: true };
  }

  return {
    userId: targetUser.user_id,
    payload: buildEnableUserUpdateRequest(),
  };
};

export const prepareDeleteUserSubmission = ({ userId }) => {
  if (!userId) {
    return { skipped: true };
  }

  return {
    userId,
  };
};

export const prepareResetPasswordSubmission = ({
  resetPasswordUser,
  resetPasswordValue,
  resetPasswordConfirm,
}) => {
  return buildResetPasswordUpdateRequest({
    resetPasswordUser,
    resetPasswordValue,
    resetPasswordConfirm,
  });
};

export const prepareGroupAssignmentSubmission = ({ editingGroupUser, selectedGroupIds }) =>
  buildGroupAssignmentUpdateRequest({
    editingGroupUser,
    selectedGroupIds,
  });

export const prepareRootDirectoryCreateSubmission = ({ companyId, name, isAdminUser }) =>
  parseRootDirectoryCreateRequest({
    companyId,
    name,
    isAdminUser,
  });
