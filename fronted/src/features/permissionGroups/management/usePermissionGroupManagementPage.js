import { useCallback, useEffect, useState } from 'react';

import { ROOT } from './constants';
import usePermissionGroupManagement from './usePermissionGroupManagement';

const MOBILE_BREAKPOINT = 768;

export default function usePermissionGroupManagementPage() {
  const management = usePermissionGroupManagement();
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

  const hasEditableFolder = !!management.selectedFolderId && management.selectedFolderId !== ROOT;

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
    handleCreateGroup,
    handleViewGroup,
    handleEditGroup,
    handleRequestDeleteGroup,
    handleCancelDeleteGroup,
    handleConfirmDeleteGroup,
  };
}
