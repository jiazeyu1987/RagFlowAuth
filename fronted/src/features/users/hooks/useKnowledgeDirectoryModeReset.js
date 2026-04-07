import { useEffect } from 'react';
import { shouldResetKnowledgeDirectoryState } from '../utils/userKnowledgeDirectories';

export const useKnowledgeDirectoryModeReset = ({
  createMode,
  policyMode,
  resetKnowledgeDirectoryState,
}) => {
  useEffect(() => {
    if (
      !shouldResetKnowledgeDirectoryState({
        showCreateModal: createMode.isOpen,
        newUserType: createMode.userType,
        showPolicyModal: policyMode.isOpen,
        policyUserType: policyMode.userType,
      })
    ) {
      return;
    }
    resetKnowledgeDirectoryState();
  }, [
    createMode.isOpen,
    createMode.userType,
    policyMode.isOpen,
    policyMode.userType,
    resetKnowledgeDirectoryState,
  ]);
};
