import { useCallback, useState } from 'react';
import { usersApi } from '../api';
import { canAssignManagedUserTools } from '../utils/userManagementRules';
import { toggleSelectedToolIds } from '../utils/userManagementDrafts';
import {
  buildClosedToolAssignmentState,
  buildOpenedToolAssignmentState,
} from '../utils/userManagementModalState';
import { runPreparedUserManagementMutation } from '../utils/userManagementPreparedMutations';
import { prepareToolAssignmentSubmission } from '../utils/userManagementSubmissions';
import { SAVE_TOOL_ERROR } from '../utils/userManagementMessages';
import { runStateAction } from '../utils/userManagementActionRunners';

export const useUserToolAssignment = ({
  actorRole,
  actorUserId,
  availableToolIds,
  mapErrorMessage,
  onError,
  onSaved,
}) => {
  const [editingToolUser, setEditingToolUser] = useState(null);
  const [showToolModal, setShowToolModal] = useState(false);
  const [selectedToolIds, setSelectedToolIds] = useState([]);

  const applyToolModalState = useCallback((nextState) => {
    setEditingToolUser(nextState.editingToolUser);
    setShowToolModal(nextState.showToolModal);
    setSelectedToolIds(nextState.selectedToolIds);
  }, []);

  const handleAssignTool = useCallback(
    async (targetUser) => {
      if (
        !canAssignManagedUserTools({
          actorRole,
          actorUserId,
          targetUser,
        })
      ) {
        return;
      }

      runStateAction(
        applyToolModalState,
        buildOpenedToolAssignmentState,
        {
          targetUser,
          availableToolIds,
        }
      );
    },
    [actorRole, actorUserId, applyToolModalState, availableToolIds]
  );

  const handleCloseToolModal = useCallback(() => {
    runStateAction(
      applyToolModalState,
      buildClosedToolAssignmentState
    );
  }, [applyToolModalState]);

  const toggleSelectedTool = useCallback((toolId, checked) => {
    setSelectedToolIds((prev) => toggleSelectedToolIds(prev, toolId, checked));
  }, []);

  const handleSaveTool = useCallback(async () => {
    await runPreparedUserManagementMutation({
      prepareSubmission: () =>
        prepareToolAssignmentSubmission({
          editingToolUser,
          selectedToolIds,
        }),
      mapErrorMessage,
      fallbackMessage: SAVE_TOOL_ERROR,
      setError: onError,
      execute: (submission) => usersApi.update(submission.userId, submission.payload),
      onSuccess: async () => {
        handleCloseToolModal();
        await onSaved?.();
      },
    });
  }, [
    editingToolUser,
    handleCloseToolModal,
    mapErrorMessage,
    onError,
    onSaved,
    selectedToolIds,
  ]);

  return {
    editingToolUser,
    showToolModal,
    selectedToolIds,
    handleAssignTool,
    handleCloseToolModal,
    toggleSelectedTool,
    handleSaveTool,
  };
};
