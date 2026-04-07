import { useEffect } from 'react';
import { isKnowledgeDirectoryModeActive } from '../utils/userKnowledgeDirectories';

export const useKnowledgeDirectoryModeLoader = ({
  companyId,
  isOpen,
  userType,
  loadKnowledgeDirectories,
}) => {
  useEffect(() => {
    if (!isKnowledgeDirectoryModeActive({ isOpen, userType })) {
      return;
    }
    loadKnowledgeDirectories(companyId);
  }, [companyId, isOpen, loadKnowledgeDirectories, userType]);
};
