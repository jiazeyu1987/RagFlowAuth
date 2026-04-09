import { useMemo } from 'react';

import { ROOT } from './constants';
import {
  buildDatasetsByNode,
  buildIndexes,
  datasetEmpty,
  fmtTime,
  pathNodes,
} from './utils';

const TEXT = {
  root: '\u6839\u76ee\u5f55',
  unnamedDir: '(\u672a\u547d\u540d\u76ee\u5f55)',
  mountRoot: '(\u6302\u8f7d\u5230\u6839\u76ee\u5f55)',
  folder: '\u6587\u4ef6\u5939',
  knowledgeBase: '\u77e5\u8bc6\u5e93',
};

export default function useKnowledgeBasesViewState({
  canManageDirectory,
  directoryTree,
  kbList,
  kbSelected,
  currentDirId,
  setCurrentDirId,
  selectedNodeId,
  setSelectedNodeId,
  expanded,
  setExpanded,
  keyword,
  selectedItem,
  setSelectedItem,
  dragDatasetId,
  setDragDatasetId,
  dropTargetNodeId,
  setDropTargetNodeId,
  isSubAdmin = false,
  managedKbRootNodeId = null,
  managedKbRootPath = null,
}) {
  const normalizedManagedRootNodeId = String(managedKbRootNodeId || '').trim();
  const normalizedManagedRootPath = String(managedKbRootPath || '').trim();
  const indexes = useMemo(() => buildIndexes(directoryTree), [directoryTree]);
  const datasetsByNode = useMemo(() => buildDatasetsByNode(directoryTree), [directoryTree]);

  const datasetNodeMap = useMemo(() => {
    const next = new Map();
    (directoryTree?.datasets || []).forEach((dataset) => {
      if (dataset?.id) {
        next.set(dataset.id, dataset.node_id || ROOT);
      }
    });
    return next;
  }, [directoryTree]);

  const kbById = useMemo(() => {
    const next = new Map();
    kbList.forEach((dataset) => {
      if (dataset?.id) {
        next.set(dataset.id, dataset);
      }
    });
    return next;
  }, [kbList]);

  const selectedKb = useMemo(() => {
    if (!kbSelected?.id) return kbSelected;
    return { ...(kbById.get(kbSelected.id) || {}), ...kbSelected };
  }, [kbById, kbSelected]);

  const breadcrumb = useMemo(
    () => [
      { id: ROOT, name: TEXT.root },
      ...pathNodes(currentDirId, indexes.byId).map((node) => ({
        id: node.id,
        name: node.name || TEXT.unnamedDir,
      })),
    ],
    [currentDirId, indexes.byId]
  );

  const dirOptions = useMemo(() => {
    const options = [];
    const nodes = [...(directoryTree?.nodes || [])].sort((left, right) =>
      String(left.path || '').localeCompare(String(right.path || ''), 'zh-Hans-CN')
    );

    if (!isSubAdmin) {
      options.push({ id: ROOT, label: TEXT.mountRoot });
    } else if (normalizedManagedRootNodeId) {
      const hasManagedRoot = nodes.some((node) => String(node?.id || '') === normalizedManagedRootNodeId);
      if (!hasManagedRoot) {
        options.push({
          id: normalizedManagedRootNodeId,
          label: normalizedManagedRootPath || normalizedManagedRootNodeId,
        });
      }
    }

    nodes.forEach((node) => {
      options.push({
        id: node.id,
        label: node.path || node.name || node.id,
      });
    });

    return options;
  }, [directoryTree, isSubAdmin, normalizedManagedRootNodeId, normalizedManagedRootPath]);

  const rows = useMemo(() => {
    const next = [];

    (indexes.childrenByParent.get(currentDirId) || []).forEach((node) => {
      next.push({
        kind: 'dir',
        id: node.id,
        name: node.name || TEXT.unnamedDir,
        modified: fmtTime(node.updated_at_ms),
        type: TEXT.folder,
      });
    });

    (datasetsByNode.get(currentDirId) || []).forEach((dataset) => {
      next.push({
        kind: 'dataset',
        id: dataset.id,
        name: dataset.name || `(\u672a\u547d\u540d${TEXT.knowledgeBase})`,
        modified: '-',
        type: TEXT.knowledgeBase,
      });
    });

    return next;
  }, [currentDirId, datasetsByNode, indexes.childrenByParent]);

  const filteredRows = useMemo(() => {
    const normalizedKeyword = String(keyword || '').trim().toLowerCase();
    if (!normalizedKeyword) return rows;

    return rows.filter((row) => {
      const name = String(row.name || '').toLowerCase();
      const id = String(row.id || '').toLowerCase();
      return name.includes(normalizedKeyword) || id.includes(normalizedKeyword);
    });
  }, [keyword, rows]);

  const canDeleteSelectedKb = useMemo(() => datasetEmpty(selectedKb), [selectedKb]);
  const showSelectedDatasetDetails = Boolean(
    selectedItem?.kind === 'dataset' && kbSelected?.id === selectedItem?.id
  );

  function ensureExpanded(nodeId) {
    if (!nodeId) return;

    const parentIds = pathNodes(nodeId, indexes.byId).map((node) => node.id);
    setExpanded((previous) => {
      const next = new Set(previous);
      parentIds.forEach((id) => next.add(id));
      return Array.from(next);
    });
  }

  function openDir(nodeId) {
    const nextNodeId = nodeId || ROOT;
    setCurrentDirId(nextNodeId);
    setSelectedNodeId(nextNodeId);
    if (nextNodeId) {
      ensureExpanded(nextNodeId);
    }
  }

  function handleToggleExpanded(id) {
    setExpanded((previous) =>
      previous.includes(id) ? previous.filter((item) => item !== id) : [...previous, id]
    );
  }

  function handleTreeNodeOpen(id) {
    openDir(id);
    setSelectedItem(id ? { kind: 'dir', id } : null);
  }

  function handleOpenBreadcrumb(id) {
    openDir(id);
  }

  function handleGoParent() {
    openDir(indexes.byId.get(currentDirId)?.parent_id || ROOT);
  }

  function handleSelectRow(row, onDatasetOpen) {
    setSelectedItem({ kind: row.kind, id: row.id });

    if (row.kind === 'dir') {
      setSelectedNodeId(row.id);
      return;
    }

    if (row.kind === 'dataset' && typeof onDatasetOpen === 'function') {
      onDatasetOpen(row.id);
    }
  }

  function handleDoubleClickRow(row, onDatasetOpen) {
    if (row.kind === 'dir') {
      openDir(row.id);
      return;
    }

    if (row.kind === 'dataset' && typeof onDatasetOpen === 'function') {
      onDatasetOpen(row.id);
    }
  }

  function handleDatasetDragStart(event, row) {
    if (!canManageDirectory || row.kind !== 'dataset') return;

    if (event.dataTransfer) {
      event.dataTransfer.setData('application/x-kb-id', row.id);
      event.dataTransfer.setData('text/plain', row.id);
      event.dataTransfer.effectAllowed = 'move';
    }

    setDragDatasetId(row.id);
    setDropTargetNodeId(null);
  }

  function handleDatasetDragEnd() {
    setDragDatasetId('');
    setDropTargetNodeId(null);
  }

  function handleTreeDragOver(event, nodeId) {
    if (!canManageDirectory || !dragDatasetId) return;

    event.preventDefault();
    if (event.dataTransfer) {
      event.dataTransfer.dropEffect = 'move';
    }
    setDropTargetNodeId(nodeId);
  }

  async function handleTreeDrop(event, nodeId, onDatasetMove) {
    if (!canManageDirectory || !dragDatasetId || typeof onDatasetMove !== 'function') return;

    event.preventDefault();
    const datasetId = event.dataTransfer?.getData('application/x-kb-id') || dragDatasetId;
    setDropTargetNodeId(null);
    setDragDatasetId('');
    await onDatasetMove(datasetId, nodeId);
  }

  function handleTreeDragLeave(event, nodeId) {
    if (!canManageDirectory || !dragDatasetId) return;

    const relatedTarget = event.relatedTarget;
    if (relatedTarget && event.currentTarget.contains(relatedTarget)) {
      return;
    }

    if (dropTargetNodeId === nodeId) {
      setDropTargetNodeId(null);
    }
  }

  return {
    indexes,
    datasetNodeMap,
    selectedKb,
    breadcrumb,
    dirOptions,
    filteredRows,
    canDeleteSelectedKb,
    showSelectedDatasetDetails,
    openDir,
    handleToggleExpanded,
    handleTreeNodeOpen,
    handleOpenBreadcrumb,
    handleGoParent,
    handleSelectRow,
    handleDoubleClickRow,
    handleDatasetDragStart,
    handleDatasetDragEnd,
    handleTreeDragOver,
    handleTreeDrop,
    handleTreeDragLeave,
  };
}
