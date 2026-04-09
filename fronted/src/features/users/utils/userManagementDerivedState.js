import { nodeExistsInTree } from './userAccessPolicy';
import {
  getValidAssignableGroupIds,
  getValidAssignableToolIds,
  isUserLoginDisabled,
} from './userManagementRules';
import { getUserPermissionGroupIds, getUserToolIds } from './userPolicyForm';

export const isManagedKbRootSelectionInvalid = ({
  policyUserType,
  managedKbRootNodeId,
  managedKbRootPath,
  kbDirectoryNodes,
  selectedManagedKbRootNodeId,
}) =>
  String(policyUserType || 'normal') === 'sub_admin'
  && !!String(managedKbRootNodeId || '').trim()
  && !String(managedKbRootPath || '').trim()
  && !nodeExistsInTree(kbDirectoryNodes, selectedManagedKbRootNodeId);

export const buildGroupAssignmentModalState = ({ targetUser, availableGroups }) => {
  const groupIds = getUserPermissionGroupIds(targetUser);
  return {
    editingGroupUser: targetUser,
    selectedGroupIds: getValidAssignableGroupIds({ availableGroups, groupIds }),
  };
};

export const buildToolAssignmentModalState = ({ targetUser, availableToolIds }) => {
  const toolIds = getUserToolIds(targetUser);
  return {
    editingToolUser: targetUser,
    selectedToolIds: getValidAssignableToolIds({ availableToolIds, toolIds }),
  };
};

export const resolveUserStatusToggleAction = (targetUser) => {
  if (!targetUser?.user_id) {
    return { type: 'ignore' };
  }
  if (String(targetUser?.username || '').toLowerCase() === 'admin') {
    return { type: 'ignore' };
  }
  if (isUserLoginDisabled(targetUser)) {
    return { type: 'enable' };
  }
  return { type: 'disable' };
};
