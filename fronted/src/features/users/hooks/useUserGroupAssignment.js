import { useCallback, useState } from 'react';
import { usersApi } from '../api';
import { canAssignManagedUserGroups } from '../utils/userManagementRules';
import {
  toggleSelectedGroupIds,
} from '../utils/userManagementDrafts';
import {
  buildClosedGroupAssignmentState,
  buildOpenedGroupAssignmentState,
} from '../utils/userManagementModalState';
import { runPreparedUserManagementMutation } from '../utils/userManagementPreparedMutations';
import { prepareGroupAssignmentSubmission } from '../utils/userManagementSubmissions';
import { SAVE_GROUP_ERROR } from '../utils/userManagementMessages';
import {
  bindStateAction,
  runStateAction,
} from '../utils/userManagementActionRunners';

export const useUserGroupAssignment = ({
  actorRole,
  actorUserId,
  availableGroups,
  mapErrorMessage,
  onError,
  onSaved,
}) => {
  const [editingGroupUser, setEditingGroupUser] = useState(null);
  const [showGroupModal, setShowGroupModal] = useState(false);
  const [selectedGroupIds, setSelectedGroupIds] = useState([]);

  const applyGroupModalState = useCallback((nextState) => {
    setEditingGroupUser(nextState.editingGroupUser);
    setShowGroupModal(nextState.showGroupModal);
    setSelectedGroupIds(nextState.selectedGroupIds);
  }, []);

  const handleAssignGroup = useCallback(
    (targetUser) => {
      if (
        !canAssignManagedUserGroups({
          actorRole,
          actorUserId,
          targetUser,
        })
      ) {
        return;
      }
      runStateAction(
        applyGroupModalState,
        buildOpenedGroupAssignmentState,
        { targetUser, availableGroups }
      );
    },
    [actorRole, actorUserId, applyGroupModalState, availableGroups]
  );

  const handleCloseGroupModal = useCallback(
    bindStateAction(
      applyGroupModalState,
      buildClosedGroupAssignmentState
    ),
    [applyGroupModalState]
  );

  const toggleSelectedGroup = useCallback((groupId, checked) => {
    setSelectedGroupIds((prev) => toggleSelectedGroupIds(prev, groupId, checked));
  }, []);

  const handleSaveGroup = useCallback(async () => {
    await runPreparedUserManagementMutation({
      prepareSubmission: () =>
        prepareGroupAssignmentSubmission({
          editingGroupUser,
          selectedGroupIds,
        }),
      mapErrorMessage,
      fallbackMessage: SAVE_GROUP_ERROR,
      setError: onError,
      execute: (submission) => usersApi.update(submission.userId, submission.payload),
      onSuccess: async () => {
        handleCloseGroupModal();
        await onSaved?.();
      },
    });
  }, [
    editingGroupUser,
    handleCloseGroupModal,
    mapErrorMessage,
    onError,
    onSaved,
    selectedGroupIds,
  ]);

  return {
    editingGroupUser,
    showGroupModal,
    selectedGroupIds,
    handleAssignGroup,
    handleCloseGroupModal,
    toggleSelectedGroup,
    handleSaveGroup,
  };
};
