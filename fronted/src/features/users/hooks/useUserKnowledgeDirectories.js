import { useKnowledgeDirectoryListing } from './useKnowledgeDirectoryListing';
import { useKnowledgeDirectoryRootCreation } from './useKnowledgeDirectoryRootCreation';

export const useUserKnowledgeDirectories = ({
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
    kbDirectoryLoading,
    kbDirectoryError,
    managedKbRootInvalid,
    fetchKnowledgeDirectories,
  } = useKnowledgeDirectoryListing({
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
    resetKnowledgeDirectoryRootCreation,
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
