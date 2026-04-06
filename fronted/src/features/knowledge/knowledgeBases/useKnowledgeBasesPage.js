import { useEffect, useMemo, useState } from 'react';

import { knowledgeApi } from '../api';
import { useAuth } from '../../../hooks/useAuth';
import {
  DATASET_CREATE_ALLOWED_KEYS,
  DATASET_UPDATE_ALLOWED_KEYS,
  ROOT,
} from './constants';
import {
  buildDatasetsByNode,
  buildIndexes,
  datasetEmpty,
  fmtTime,
  pathNodes,
  pickAllowed,
} from './utils';

const MOBILE_BREAKPOINT = 768;

const getInitialIsMobile = () => {
  if (typeof window === 'undefined') return false;
  return window.innerWidth <= MOBILE_BREAKPOINT;
};

export default function useKnowledgeBasesPage() {
  const { canManageKbDirectory, canManageKnowledgeTree } = useAuth();
  const canManageDirectory = canManageKbDirectory();
  const canManageDatasets = canManageKnowledgeTree();

  const [subtab, setSubtab] = useState('kbs');
  const [isMobile, setIsMobile] = useState(getInitialIsMobile);
  const [kbList, setKbList] = useState([]);
  const [directoryTree, setDirectoryTree] = useState({ nodes: [], datasets: [] });
  const [kbError, setKbError] = useState('');
  const [treeError, setTreeError] = useState('');
  const [kbBusy, setKbBusy] = useState(false);
  const [kbSaveStatus, setKbSaveStatus] = useState('');
  const [currentDirId, setCurrentDirId] = useState(ROOT);
  const [selectedNodeId, setSelectedNodeId] = useState(ROOT);
  const [expanded, setExpanded] = useState([]);
  const [keyword, setKeyword] = useState('');
  const [selectedItem, setSelectedItem] = useState(null);
  const [dragDatasetId, setDragDatasetId] = useState('');
  const [dropTargetNodeId, setDropTargetNodeId] = useState(null);
  const [kbSelected, setKbSelected] = useState(null);
  const [kbNameText, setKbNameText] = useState('');
  const [datasetDirId, setDatasetDirId] = useState(ROOT);
  const [createOpen, setCreateOpen] = useState(false);
  const [createName, setCreateName] = useState('');
  const [createFromId, setCreateFromId] = useState('');
  const [createPayload, setCreatePayload] = useState({});
  const [createDirId, setCreateDirId] = useState(ROOT);
  const [createError, setCreateError] = useState('');

  useEffect(() => {
    if (typeof window === 'undefined') return undefined;

    const handleResize = () => setIsMobile(window.innerWidth <= MOBILE_BREAKPOINT);
    handleResize();
    window.addEventListener('resize', handleResize);

    return () => window.removeEventListener('resize', handleResize);
  }, []);

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
      { id: ROOT, name: '根目录' },
      ...pathNodes(currentDirId, indexes.byId).map((node) => ({
        id: node.id,
        name: node.name || '(未命名目录)',
      })),
    ],
    [currentDirId, indexes.byId]
  );

  const dirOptions = useMemo(() => {
    const options = [{ id: ROOT, label: '(挂载到根目录)' }];
    const nodes = [...(directoryTree?.nodes || [])].sort((left, right) =>
      String(left.path || '').localeCompare(String(right.path || ''), 'zh-Hans-CN')
    );

    nodes.forEach((node) => {
      options.push({
        id: node.id,
        label: node.path || node.name || node.id,
      });
    });

    return options;
  }, [directoryTree]);

  const rows = useMemo(() => {
    const next = [];

    (indexes.childrenByParent.get(currentDirId) || []).forEach((node) => {
      next.push({
        kind: 'dir',
        id: node.id,
        name: node.name || '(未命名目录)',
        modified: fmtTime(node.updated_at_ms),
        type: '文件夹',
      });
    });

    (datasetsByNode.get(currentDirId) || []).forEach((dataset) => {
      next.push({
        kind: 'dataset',
        id: dataset.id,
        name: dataset.name || '(未命名知识库)',
        modified: '-',
        type: '知识库',
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
      const validIds = new Set(tree.nodes.map((node) => node.id));

      if (currentDirId && !validIds.has(currentDirId)) {
        setCurrentDirId(ROOT);
      }
      if (selectedNodeId && selectedNodeId !== ROOT && !validIds.has(selectedNodeId)) {
        setSelectedNodeId(ROOT);
      }

      setExpanded((previous) => previous.filter((id) => validIds.has(id)));
    } catch (requestError) {
      setTreeError(requestError?.message || '加载目录树失败');
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
      setDatasetDirId(nodeId);
    } catch (requestError) {
      setKbSelected(null);
      setKbError(requestError?.message || '加载知识库详情失败');
    }
  }

  async function refreshAll() {
    try {
      await Promise.all([fetchKbList(), fetchTree()]);
    } catch (requestError) {
      setKbError(requestError?.message || '刷新失败');
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
        throw new Error('知识库名称不能为空');
      }

      const updates = {
        ...pickAllowed(kbSelected, DATASET_UPDATE_ALLOWED_KEYS),
        name,
      };
      const updated = await knowledgeApi.updateRagflowDataset(kbSelected.id, updates);

      if (!updated?.id) {
        throw new Error('知识库更新失败');
      }

      await knowledgeApi.assignDatasetDirectory(updated.id, datasetDirId || null);
      setKbSelected({
        ...updated,
        local_document_count: Number(selectedKb?.local_document_count || 0),
      });
      setKbNameText(String(updated.name || name));
      setKbSaveStatus('保存成功');
      await refreshAll();
    } catch (requestError) {
      setKbError(requestError?.message || '保存知识库失败');
    } finally {
      setKbBusy(false);
    }
  }

  async function deleteKb(dataset) {
    if (!canManageDatasets || !dataset?.id) return;

    if (!datasetEmpty(dataset)) {
      setKbError('知识库非空，无法删除');
      return;
    }

    if (!window.confirm(`确认删除知识库“${dataset.name || dataset.id}”？`)) {
      return;
    }

    setKbBusy(true);
    setKbError('');

    try {
      const request = await knowledgeApi.deleteRagflowDataset(dataset.id);
      const requestIdText = request?.request_id ? `：${request.request_id}` : '';
      setKbSaveStatus(`删除申请已提交${requestIdText}`);
      await refreshAll();
    } catch (requestError) {
      setKbError(requestError?.message || '删除知识库失败');
    } finally {
      setKbBusy(false);
    }
  }

  async function moveDatasetToNode(datasetId, targetNodeId) {
    if (!canManageDirectory || !datasetId) return;

    const fromNodeId = datasetNodeMap.get(datasetId) || ROOT;
    const nextNodeId = targetNodeId || ROOT;

    if (fromNodeId === nextNodeId) return;

    setKbError('');

    try {
      await knowledgeApi.assignDatasetDirectory(datasetId, nextNodeId || null);
      setKbSaveStatus(`已将知识库 ${datasetId} 移动到${nextNodeId ? '目标目录' : '根目录'}`);
      await fetchTree();

      if (kbSelected?.id === datasetId) {
        setDatasetDirId(nextNodeId);
      }
    } catch (requestError) {
      setKbError(requestError?.message || '移动知识库失败');
    }
  }

  function handleTreeDragOver(event, nodeId) {
    if (!canManageDirectory || !dragDatasetId) return;

    event.preventDefault();
    if (event.dataTransfer) {
      event.dataTransfer.dropEffect = 'move';
    }
    setDropTargetNodeId(nodeId);
  }

  async function handleTreeDrop(event, nodeId) {
    if (!canManageDirectory || !dragDatasetId) return;

    event.preventDefault();
    const datasetId = event.dataTransfer?.getData('application/x-kb-id') || dragDatasetId;
    setDropTargetNodeId(null);
    setDragDatasetId('');
    await moveDatasetToNode(datasetId, nodeId);
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

  async function createDirectory() {
    if (!canManageDirectory) return;

    const name = window.prompt('请输入新目录名称');
    if (!name || !name.trim()) return;

    try {
      const node = await knowledgeApi.createKnowledgeDirectory({
        name: name.trim(),
        parent_id: currentDirId || null,
      });
      const newNodeId = node?.id;
      await fetchTree();

      if (newNodeId) {
        openDir(newNodeId);
        setSelectedItem({ kind: 'dir', id: newNodeId });
      }
    } catch (requestError) {
      setTreeError(requestError?.message || '创建目录失败');
    }
  }

  async function renameDirectory() {
    if (!canManageDirectory || !selectedNodeId || selectedNodeId === ROOT) return;

    const node = indexes.byId.get(selectedNodeId);
    const nextName = window.prompt('请输入新的目录名称', node?.name || '');
    if (!nextName || !nextName.trim()) return;

    try {
      await knowledgeApi.updateKnowledgeDirectory(selectedNodeId, { name: nextName.trim() });
      await fetchTree();
    } catch (requestError) {
      setTreeError(requestError?.message || '重命名目录失败');
    }
  }

  async function deleteDirectory() {
    if (!canManageDirectory || !selectedNodeId || selectedNodeId === ROOT) return;

    const node = indexes.byId.get(selectedNodeId);
    if (
      !window.confirm(
        `确认删除目录“${node?.name || selectedNodeId}”？删除后子目录也会一并移除。`
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
      setTreeError(requestError?.message || '删除目录失败');
    }
  }

  function openCreateKb() {
    const preferredDirId = selectedItem?.kind === 'dir' ? selectedItem.id : currentDirId;
    setCreateOpen(true);
    setCreateName('');
    setCreateFromId(String(kbList[0]?.id || ''));
    setCreatePayload({});
    setCreateDirId(preferredDirId || ROOT);
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
        throw new Error('请选择要复制的知识库');
      }

      setCreatePayload(pickAllowed(source, DATASET_CREATE_ALLOWED_KEYS));
      setCreateError('');
    } catch (requestError) {
      setCreatePayload({});
      setCreateError(requestError?.message || '创建失败');
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
        throw new Error('请输入知识库名称');
      }

      await knowledgeApi.createRagflowDataset({
        name,
        node_id: createDirId || null,
        ...pickAllowed(createPayload, DATASET_CREATE_ALLOWED_KEYS),
      });
      setCreateOpen(false);
      setKbSaveStatus('新建知识库成功');
      await refreshAll();
    } catch (requestError) {
      setCreateError(requestError?.message || '创建失败');
    } finally {
      setKbBusy(false);
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

  function handleSelectRow(row) {
    setSelectedItem({ kind: row.kind, id: row.id });

    if (row.kind === 'dir') {
      setSelectedNodeId(row.id);
      return;
    }

    if (row.kind === 'dataset') {
      loadKbDetail(row.id);
    }
  }

  function handleDoubleClickRow(row) {
    if (row.kind === 'dir') {
      openDir(row.id);
      return;
    }

    if (row.kind === 'dataset') {
      loadKbDetail(row.id);
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

  function handleDeleteSelectedKb() {
    return deleteKb(selectedKb);
  }

  return {
    ROOT,
    subtab,
    isMobile,
    kbList,
    kbError,
    treeError,
    kbBusy,
    kbSaveStatus,
    currentDirId,
    selectedNodeId,
    expanded,
    keyword,
    selectedItem,
    dragDatasetId,
    dropTargetNodeId,
    selectedKb,
    kbNameText,
    datasetDirId,
    createOpen,
    createName,
    createFromId,
    createDirId,
    createError,
    canManageDirectory,
    canManageDatasets,
    indexes,
    breadcrumb,
    dirOptions,
    filteredRows,
    canDeleteSelectedKb,
    showSelectedDatasetDetails,
    setSubtab,
    setKeyword,
    setKbNameText,
    setDatasetDirId,
    setCreateName,
    setCreateDirId,
    refreshAll,
    saveKb,
    createDirectory,
    renameDirectory,
    deleteDirectory,
    openCreateKb,
    closeCreateKb,
    createKb,
    handleCreateFromIdChange,
    handleToggleExpanded,
    handleTreeNodeOpen,
    handleOpenBreadcrumb,
    handleGoParent,
    handleSelectRow,
    handleDoubleClickRow,
    handleDatasetDragStart,
    handleDatasetDragEnd,
    handleDeleteSelectedKb,
    handleTreeDragOver,
    handleTreeDrop,
    handleTreeDragLeave,
  };
}
