import { useCallback } from 'react';

export default function usePermissionGroupManagementDrag({
  dragGroupId,
  dropTargetFolderId,
  moveGroupToFolder,
  setDragGroupId,
  setDropTargetFolderId,
}) {
  const onDragOverFolder = useCallback(
    (event, folderId) => {
      if (!dragGroupId) return;

      event.preventDefault();

      if (event.dataTransfer) {
        event.dataTransfer.dropEffect = 'move';
      }

      setDropTargetFolderId(folderId);
    },
    [dragGroupId, setDropTargetFolderId]
  );

  const onDragLeaveFolder = useCallback(
    (event, folderId) => {
      if (!dragGroupId) return;

      const relatedTarget = event.relatedTarget;
      if (relatedTarget && event.currentTarget.contains(relatedTarget)) return;
      if (dropTargetFolderId === folderId) {
        setDropTargetFolderId(null);
      }
    },
    [dragGroupId, dropTargetFolderId, setDropTargetFolderId]
  );

  const onDropFolder = useCallback(
    async (event, folderId) => {
      if (!dragGroupId) return;

      event.preventDefault();

      const rawGroupId = event.dataTransfer?.getData('application/x-pg-group-id');
      const droppedGroupId = Number(rawGroupId || dragGroupId);

      setDropTargetFolderId(null);
      setDragGroupId(null);

      if (!Number.isFinite(droppedGroupId)) return;

      await moveGroupToFolder(droppedGroupId, folderId);
    },
    [dragGroupId, moveGroupToFolder, setDragGroupId, setDropTargetFolderId]
  );

  const startGroupDrag = useCallback(
    (event, groupId) => {
      if (event.dataTransfer) {
        event.dataTransfer.setData('application/x-pg-group-id', String(groupId));
        event.dataTransfer.effectAllowed = 'move';
      }

      setDragGroupId(groupId);
      setDropTargetFolderId(null);
    },
    [setDragGroupId, setDropTargetFolderId]
  );

  const endGroupDrag = useCallback(() => {
    setDragGroupId(null);
    setDropTargetFolderId(null);
  }, [setDragGroupId, setDropTargetFolderId]);

  return {
    onDragOverFolder,
    onDragLeaveFolder,
    onDropFolder,
    startGroupDrag,
    endGroupDrag,
  };
}
