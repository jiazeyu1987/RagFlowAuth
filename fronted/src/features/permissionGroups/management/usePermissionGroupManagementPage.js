import { useCallback, useEffect, useState } from 'react';

import { ROOT } from './constants';
import usePermissionGroupManagement from './usePermissionGroupManagement';
import { useAuth } from '../../../hooks/useAuth';

const MOBILE_BREAKPOINT = 768;

export default function usePermissionGroupManagementPage() {
  const management = usePermissionGroupManagement();
  const { user } = useAuth();
  const [isMobile, setIsMobile] = useState(() => {
    if (typeof window === 'undefined') return false;
    return window.innerWidth <= MOBILE_BREAKPOINT;
  });
  const [pendingDeleteGroup, setPendingDeleteGroup] = useState(null);

  useEffect(() => {
    if (typeof window === 'undefined') return undefined;

    const handleResize = () => setIsMobile(window.innerWidth <= MOBILE_BREAKPOINT);
    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const currentUserId = String(user?.user_id || '').trim();
  const isOwnedFolder = useCallback(
    (folderId) => {
      if (!folderId || folderId === ROOT) return false;
      const folder = management.folderIndexes?.byId?.get(folderId);
      return String(folder?.created_by || '').trim() === currentUserId;
    },
    [currentUserId, management.folderIndexes]
  );
  const hasEditableFolder = isOwnedFolder(management.selectedFolderId);
  const canCreateFolder = management.currentFolderId === ROOT || isOwnedFolder(management.currentFolderId);

  const handleCreateGroup = useCallback(() => {
    setPendingDeleteGroup(null);
    management.startCreateGroup();
  }, [management]);

  const handleViewGroup = useCallback(
    (group) => {
      setPendingDeleteGroup(null);
      management.viewGroup(group);
    },
    [management]
  );

  const handleEditGroup = useCallback(
    (group) => {
      setPendingDeleteGroup(null);
      management.activateGroup(group);
    },
    [management]
  );

  const handleRequestDeleteGroup = useCallback((group) => {
    setPendingDeleteGroup(group);
  }, []);

  const handleCancelDeleteGroup = useCallback(() => {
    setPendingDeleteGroup(null);
  }, []);

  const handleConfirmDeleteGroup = useCallback(async () => {
    if (!pendingDeleteGroup) return;
    const targetGroup = pendingDeleteGroup;
    setPendingDeleteGroup(null);
    await management.removeGroup(targetGroup, { skipConfirm: true });
  }, [management, pendingDeleteGroup]);

  return {
    ...management,
    isMobile,
    pendingDeleteGroup,
    hasEditableFolder,
    canCreateFolder,
    handleCreateGroup,
    handleViewGroup,
    handleEditGroup,
    handleRequestDeleteGroup,
    handleCancelDeleteGroup,
    handleConfirmDeleteGroup,
  };
}
