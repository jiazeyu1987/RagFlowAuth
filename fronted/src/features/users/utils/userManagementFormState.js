import { DEFAULT_NEW_USER, DEFAULT_POLICY_FORM } from './constants';
import { normalizeDraftByUserType } from './userAccessPolicy';
import { buildPolicyFormFromUser } from './userPolicyForm';

export const buildOpenedCreateUserState = (currentNewUser = DEFAULT_NEW_USER) => ({
  showCreateModal: true,
  newUser: currentNewUser,
  createUserError: null,
});

export const buildClosedCreateUserState = () => ({
  showCreateModal: false,
  newUser: DEFAULT_NEW_USER,
  createUserError: null,
});

export const buildOpenedPolicyState = (targetUser) => ({
  showPolicyModal: true,
  policyUser: targetUser,
  policyError: null,
  policyForm: normalizeDraftByUserType(buildPolicyFormFromUser(targetUser)),
});

export const buildClosedPolicyState = (initialPolicyForm = DEFAULT_POLICY_FORM) => ({
  showPolicyModal: false,
  policyUser: null,
  policyError: null,
  policyForm: initialPolicyForm,
});
