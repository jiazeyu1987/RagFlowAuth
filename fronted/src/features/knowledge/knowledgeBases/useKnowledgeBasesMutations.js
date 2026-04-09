import { useEffect } from 'react';

import { knowledgeApi } from '../api';
import { mapUserFacingErrorMessage } from '../../../shared/errors/userFacingErrorMessages';
import {
  DATASET_CREATE_ALLOWED_KEYS,
  DATASET_UPDATE_ALLOWED_KEYS,
  ROOT,
} from './constants';
import { datasetEmpty, pickAllowed } from './utils';

const TEXT = {
  loadTreeFailed: '\u52a0\u8f7d\u76ee\u5f55\u6811\u5931\u8d25',
  loadDatasetDetailFailed: '\u52a0\u8f7d\u77e5\u8bc6\u5e93\u8be6\u60c5\u5931\u8d25',
  refreshFailed: '\u5237\u65b0\u5931\u8d25',
  datasetNameRequired: '\u77e5\u8bc6\u5e93\u540d\u79f0\u4e0d\u80fd\u4e3a\u7a7a',
  saveFailed: '\u4fdd\u5b58\u77e5\u8bc6\u5e93\u5931\u8d25',
  saveSuccess: '\u4fdd\u5b58\u6210\u529f',
  datasetNotEmpty: '\u77e5\u8bc6\u5e93\u975e\u7a7a\uff0c\u65e0\u6cd5\u5220\u9664',
  deleteDatasetFailed: '\u5220\u9664\u77e5\u8bc6\u5e93\u5931\u8d25',
  deleteRequestSubmitted: '\u5220\u9664\u7533\u8bf7\u5df2\u63d0\u4ea4',
  moveDatasetFailed: '\u79fb\u52a8\u77e5\u8bc6\u5e93\u5931\u8d25',
  moveToRoot: '\u6839\u76ee\u5f55',
  moveToTarget: '\u76ee\u6807\u76ee\u5f55',
  createDirectoryPrompt: '\u8bf7\u8f93\u5165\u65b0\u76ee\u5f55\u540d\u79f0',
  createDirectoryFailed: '\u521b\u5efa\u76ee\u5f55\u5931\u8d25',
  renameDirectoryPrompt: '\u8bf7\u8f93\u5165\u65b0\u7684\u76ee\u5f55\u540d\u79f0',
  renameDirectoryFailed: '\u91cd\u547d\u540d\u76ee\u5f55\u5931\u8d25',
  deleteDirectoryFailed: '\u5220\u9664\u76ee\u5f55\u5931\u8d25',
  createFailed: '\u521b\u5efa\u5931\u8d25',
  createNameRequired: '\u8bf7\u8f93\u5165\u77e5\u8bc6\u5e93\u540d\u79f0',
  createSuccess: '\u65b0\u5efa\u77e5\u8bc6\u5e93\u6210\u529f',
  selectCopySource: '\u8bf7\u9009\u62e9\u8981\u590d\u5236\u7684\u77e5\u8bc6\u5e93',
  subAdminRootMissing:
    '\u5f53\u524d\u5b50\u7ba1\u7406\u5458\u672a\u914d\u7f6e\u77e5\u8bc6\u5e93\u6839\u76ee\u5f55\uff0c\u8bf7\u8054\u7cfb\u7cfb\u7edf\u7ba1\u7406\u5458',
};

export default function useKnowledgeBasesMutations({
  canManageDirectory,
  canManageDatasets,
  isSubAdmin = false,
  managedKbRootNodeId = null,
  datasetState,
  createState,
  navigationState,
}) {
  const {
    kbList,
    setKbList,
    directoryTree,
    setDirectoryTree,
    setKbError,
    setTreeError,
    setKbBusy,
    setKbSaveStatus,
    kbSelected,
    setKbSelected,
    kbNameText,
    setKbNameText,
    datasetDirId,
    setDatasetDirId,
    selectedKb,
  } = datasetState;
  const {
    setCreateOpen,
    setCreateFromId,
    setCreatePayload,
    createName,
    createPayload,
    createDirId,
    setCreateError,
  } = createState;
  const {
    currentDirId,
    setCurrentDirId,
    selectedNodeId,
    setSelectedNodeId,
    setExpanded,
    selectedItem,
    setSelectedItem,
    indexes,
    datasetNodeMap,
    openDir,
  } = navigationState;
  const normalizedManagedRootNodeId = String(managedKbRootNodeId || '').trim();

  function resolveSelectableNodeId(nodeId) {
    const normalizedNodeId = typeof nodeId === 'string' ? nodeId.trim() : '';
    if (normalizedNodeId) {
      return normalizedNodeId;
    }
    if (isSubAdmin && normalizedManagedRootNodeId) {
      return normalizedManagedRootNodeId;
    }
    return ROOT;
  }

  function resolveNodeIdForWrite(nodeId) {
    const normalizedNodeId = typeof nodeId === 'string' ? nodeId.trim() : '';
    if (normalizedNodeId) {
      return normalizedNodeId;
    }
    if (isSubAdmin) {
      if (!normalizedManagedRootNodeId) {
        throw new Error(TEXT.subAdminRootMissing);
      }
      return normalizedManagedRootNodeId;
    }
    return null;
  }

  async function fetchKbList() {
    setKbError('');
    const datasets = await knowledgeApi.listRagflowDatasets();
    setKbList(datasets);
  }

  async function fetchTree() {
    setTreeError('');

    try {
      const tree = await knowledgeApi.listKnowledgeDirectories();
      setDirectoryTree(tree);
      const validIds = new Set((tree.nodes || []).map((node) => node.id));
      const fallbackDirId =
        isSubAdmin && normalizedManagedRootNodeId ? normalizedManagedRootNodeId : ROOT;

      if (currentDirId && currentDirId !== ROOT && !validIds.has(currentDirId)) {
        setCurrentDirId(fallbackDirId);
      }
      if (selectedNodeId && selectedNodeId !== ROOT && !validIds.has(selectedNodeId)) {
        setSelectedNodeId(fallbackDirId);
      }

      setExpanded((previous) => previous.filter((id) => validIds.has(id)));
    } catch (requestError) {
      setTreeError(mapUserFacingErrorMessage(requestError?.message, TEXT.loadTreeFailed));
    }
  }

  async function loadKbDetail(datasetId) {
    if (!datasetId) return;

    setKbError('');

    try {
      const [dataset, documentsResponse] = await Promise.all([
        knowledgeApi.getRagflowDataset(datasetId),
        knowledgeApi.listLocalDocuments({ kb_id: datasetId, limit: 1 }),
      ]);

      if (!dataset?.id) {
        throw new Error('dataset_not_found');
      }

      const localDocumentCount = Number(documentsResponse?.count);
      if (!Number.isFinite(localDocumentCount)) {
        throw new Error('local_document_count_invalid');
      }

      setKbSelected({
        ...dataset,
        local_document_count: localDocumentCount,
      });
      setKbNameText(String(dataset.name || ''));

      const nodeId =
        (directoryTree?.datasets || []).find((item) => item.id === dataset.id)?.node_id || ROOT;
      setDatasetDirId(resolveSelectableNodeId(nodeId));
    } catch (requestError) {
      setKbSelected(null);
      setKbError(mapUserFacingErrorMessage(requestError?.message, TEXT.loadDatasetDetailFailed));
    }
  }

  async function refreshAll() {
    try {
      await Promise.all([fetchKbList(), fetchTree()]);
    } catch (requestError) {
      setKbError(mapUserFacingErrorMessage(requestError?.message, TEXT.refreshFailed));
    }
  }

  useEffect(() => {
    refreshAll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function saveKb() {
    if (!canManageDatasets || !kbSelected?.id) return;

    setKbBusy(true);
    setKbError('');
    setKbSaveStatus('');

    try {
      const name = String(kbNameText || '').trim();
      if (!name) {
        throw new Error(TEXT.datasetNameRequired);
      }

      const updates = {
        ...pickAllowed(kbSelected, DATASET_UPDATE_ALLOWED_KEYS),
        name,
      };
      const updated = await knowledgeApi.updateRagflowDataset(kbSelected.id, updates);

      if (!updated?.id) {
        throw new Error('dataset_update_failed');
      }

      await knowledgeApi.assignDatasetDirectory(updated.id, resolveNodeIdForWrite(datasetDirId));
      setKbSelected({
        ...updated,
        local_document_count: Number(selectedKb?.local_document_count || 0),
      });
      setKbNameText(String(updated.name || name));
      setKbSaveStatus(TEXT.saveSuccess);
      await refreshAll();
    } catch (requestError) {
      setKbError(mapUserFacingErrorMessage(requestError?.message, TEXT.saveFailed));
    } finally {
      setKbBusy(false);
    }
  }

  async function deleteKb(dataset) {
    if (!canManageDatasets || !dataset?.id) return;

    if (!datasetEmpty(dataset)) {
      setKbError(TEXT.datasetNotEmpty);
      return;
    }

    if (
      !window.confirm(
        `\u786e\u8ba4\u5220\u9664\u77e5\u8bc6\u5e93\u201c${dataset.name || dataset.id}\u201d\uff1f`
      )
    ) {
      return;
    }

    setKbBusy(true);
    setKbError('');

    try {
      const request = await knowledgeApi.deleteRagflowDataset(dataset.id);
      const requestIdText = request?.request_id ? `\uff1a${request.request_id}` : '';
      setKbSaveStatus(`${TEXT.deleteRequestSubmitted}${requestIdText}`);
      await refreshAll();
    } catch (requestError) {
      setKbError(mapUserFacingErrorMessage(requestError?.message, TEXT.deleteDatasetFailed));
    } finally {
      setKbBusy(false);
    }
  }

  async function moveDatasetToNode(datasetId, targetNodeId) {
    if (!canManageDirectory || !datasetId) return;

    const fromNodeId = resolveSelectableNodeId(datasetNodeMap.get(datasetId));
    const nextNodeId = resolveSelectableNodeId(targetNodeId);

    if (fromNodeId === nextNodeId) return;

    setKbError('');

    try {
      const nextNodeIdForWrite = resolveNodeIdForWrite(nextNodeId);
      await knowledgeApi.assignDatasetDirectory(datasetId, nextNodeIdForWrite);
      setKbSaveStatus(
        `\u5df2\u5c06\u77e5\u8bc6\u5e93 ${datasetId} \u79fb\u52a8\u5230${
          nextNodeIdForWrite ? TEXT.moveToTarget : TEXT.moveToRoot
        }`
      );
      await fetchTree();

      if (kbSelected?.id === datasetId) {
        setDatasetDirId(nextNodeId);
      }
    } catch (requestError) {
      setKbError(mapUserFacingErrorMessage(requestError?.message, TEXT.moveDatasetFailed));
    }
  }

  async function createDirectory() {
    if (!canManageDirectory) return;

    const name = window.prompt(TEXT.createDirectoryPrompt);
    if (!name || !name.trim()) return;

    try {
      const node = await knowledgeApi.createKnowledgeDirectory({
        name: name.trim(),
        parent_id: resolveNodeIdForWrite(currentDirId),
      });
      const newNodeId = node?.id;
      await fetchTree();

      if (newNodeId) {
        openDir(newNodeId);
        setSelectedItem({ kind: 'dir', id: newNodeId });
      }
    } catch (requestError) {
      setTreeError(mapUserFacingErrorMessage(requestError?.message, TEXT.createDirectoryFailed));
    }
  }

  async function renameDirectory() {
    if (!canManageDirectory || !selectedNodeId || selectedNodeId === ROOT) return;

    const node = indexes.byId.get(selectedNodeId);
    const nextName = window.prompt(TEXT.renameDirectoryPrompt, node?.name || '');
    if (!nextName || !nextName.trim()) return;

    try {
      await knowledgeApi.updateKnowledgeDirectory(selectedNodeId, { name: nextName.trim() });
      await fetchTree();
    } catch (requestError) {
      setTreeError(mapUserFacingErrorMessage(requestError?.message, TEXT.renameDirectoryFailed));
    }
  }

  async function deleteDirectory() {
    if (!canManageDirectory || !selectedNodeId || selectedNodeId === ROOT) return;

    const node = indexes.byId.get(selectedNodeId);
    if (
      !window.confirm(
        `\u786e\u8ba4\u5220\u9664\u76ee\u5f55\u201c${
          node?.name || selectedNodeId
        }\u201d\uff1f\u5220\u9664\u540e\u5b50\u76ee\u5f55\u4e5f\u4f1a\u4e00\u5e76\u79fb\u9664\u3002`
      )
    ) {
      return;
    }

    try {
      const parentId = node?.parent_id || ROOT;
      await knowledgeApi.deleteKnowledgeDirectory(selectedNodeId);
      setSelectedNodeId(parentId);
      setCurrentDirId(parentId);
      setSelectedItem(null);
      await fetchTree();
    } catch (requestError) {
      setTreeError(mapUserFacingErrorMessage(requestError?.message, TEXT.deleteDirectoryFailed));
    }
  }

  function openCreateKb() {
    const preferredDirId = selectedItem?.kind === 'dir' ? selectedItem.id : currentDirId;
    setCreateOpen(true);
    createState.setCreateName('');
    setCreateFromId(String(kbList[0]?.id || ''));
    setCreatePayload({});
    createState.setCreateDirId(resolveSelectableNodeId(preferredDirId));
    setCreateError('');
  }

  function closeCreateKb() {
    setCreateOpen(false);
  }

  async function syncCreateFromCopy(sourceId) {
    if (!sourceId) return;

    try {
      const source = await knowledgeApi.getRagflowDataset(sourceId);
      if (!source?.id) {
        throw new Error(TEXT.selectCopySource);
      }

      setCreatePayload(pickAllowed(source, DATASET_CREATE_ALLOWED_KEYS));
      setCreateError('');
    } catch (requestError) {
      setCreatePayload({});
      setCreateError(mapUserFacingErrorMessage(requestError?.message, TEXT.createFailed));
    }
  }

  async function handleCreateFromIdChange(value) {
    setCreateFromId(value);
    await syncCreateFromCopy(value);
  }

  async function createKb() {
    if (!canManageDatasets) return;

    setKbBusy(true);

    try {
      const name = String(createName || '').trim();
      if (!name) {
        throw new Error(TEXT.createNameRequired);
      }

      await knowledgeApi.createRagflowDataset({
        name,
        node_id: resolveNodeIdForWrite(createDirId),
        ...pickAllowed(createPayload, DATASET_CREATE_ALLOWED_KEYS),
      });
      setCreateOpen(false);
      setKbSaveStatus(TEXT.createSuccess);
      await refreshAll();
    } catch (requestError) {
      setCreateError(mapUserFacingErrorMessage(requestError?.message, TEXT.createFailed));
    } finally {
      setKbBusy(false);
    }
  }

  function handleDeleteSelectedKb() {
    return deleteKb(selectedKb);
  }

  return {
    loadKbDetail,
    refreshAll,
    saveKb,
    createDirectory,
    renameDirectory,
    deleteDirectory,
    openCreateKb,
    closeCreateKb,
    createKb,
    handleCreateFromIdChange,
    handleDeleteSelectedKb,
    moveDatasetToNode,
  };
}
