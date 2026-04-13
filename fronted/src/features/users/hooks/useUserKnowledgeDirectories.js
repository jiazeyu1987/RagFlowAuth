import { useKnowledgeDirectoryListing } from './useKnowledgeDirectoryListing';
import { useKnowledgeDirectoryRootCreation } from './useKnowledgeDirectoryRootCreation';

export const useUserKnowledgeDirectories = ({
  allUsers,
  isAdminUser,
  createMode,
  policyMode,
  policyUser,
  mapErrorMessage,
  companyRequiredMessage,
  nameRequiredMessage,
  loadErrorMessage,
  createErrorMessage,
}) => {
  const {
    kbDirectoryNodes,
    kbDirectoryDisabledNodeIds,
    kbDirectoryLoading,
    kbDirectoryError,
    managedKbRootInvalid,
    fetchKnowledgeDirectories,
  } = useKnowledgeDirectoryListing({
    allUsers,
    isAdminUser,
    createMode,
    policyMode,
    policyUser,
    mapErrorMessage,
    loadErrorMessage,
  });

  const {
    kbDirectoryCreatingRoot,
    kbDirectoryCreateError,
    clearKbDirectoryCreateError,
    handleCreateModalRootDirectory,
    handlePolicyRootDirectory,
  } = useKnowledgeDirectoryRootCreation({
    isAdminUser,
    createMode,
    policyMode,
    mapErrorMessage,
    companyRequiredMessage,
    nameRequiredMessage,
    createErrorMessage,
    fetchKnowledgeDirectories,
  });

  return {
    kbDirectoryNodes,
    kbDirectoryDisabledNodeIds,
    kbDirectoryLoading,
    kbDirectoryError,
    kbDirectoryCreatingRoot,
    kbDirectoryCreateError,
    managedKbRootInvalid,
    clearKbDirectoryCreateError,
    handleCreateModalRootDirectory,
    handlePolicyRootDirectory,
  };
};
