import { useEffect, useState } from 'react';

import { useAuth } from '../../../hooks/useAuth';
import { ROOT } from './constants';
import useKnowledgeBasesMutations from './useKnowledgeBasesMutations';
import useKnowledgeBasesViewState from './useKnowledgeBasesViewState';

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

  const viewState = useKnowledgeBasesViewState({
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
  });

  const mutations = useKnowledgeBasesMutations({
    canManageDirectory,
    canManageDatasets,
    datasetState: {
      kbList,
      setKbList,
      directoryTree,
      setDirectoryTree,
      kbError,
      setKbError,
      treeError,
      setTreeError,
      kbBusy,
      setKbBusy,
      kbSaveStatus,
      setKbSaveStatus,
      kbSelected,
      setKbSelected,
      kbNameText,
      setKbNameText,
      datasetDirId,
      setDatasetDirId,
      selectedKb: viewState.selectedKb,
    },
    createState: {
      createOpen,
      setCreateOpen,
      createName,
      setCreateName,
      createFromId,
      setCreateFromId,
      createPayload,
      setCreatePayload,
      createDirId,
      setCreateDirId,
      createError,
      setCreateError,
    },
    navigationState: {
      currentDirId,
      setCurrentDirId,
      selectedNodeId,
      setSelectedNodeId,
      expanded,
      setExpanded,
      selectedItem,
      setSelectedItem,
      indexes: viewState.indexes,
      datasetNodeMap: viewState.datasetNodeMap,
      openDir: viewState.openDir,
    },
  });

  const handleSelectRow = (row) => viewState.handleSelectRow(row, mutations.loadKbDetail);
  const handleDoubleClickRow = (row) =>
    viewState.handleDoubleClickRow(row, mutations.loadKbDetail);
  const handleTreeDrop = (event, nodeId) =>
    viewState.handleTreeDrop(event, nodeId, mutations.moveDatasetToNode);

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
    selectedKb: viewState.selectedKb,
    kbNameText,
    datasetDirId,
    createOpen,
    createName,
    createFromId,
    createDirId,
    createError,
    canManageDirectory,
    canManageDatasets,
    indexes: viewState.indexes,
    breadcrumb: viewState.breadcrumb,
    dirOptions: viewState.dirOptions,
    filteredRows: viewState.filteredRows,
    canDeleteSelectedKb: viewState.canDeleteSelectedKb,
    showSelectedDatasetDetails: viewState.showSelectedDatasetDetails,
    setSubtab,
    setKeyword,
    setKbNameText,
    setDatasetDirId,
    setCreateName,
    setCreateDirId,
    refreshAll: mutations.refreshAll,
    saveKb: mutations.saveKb,
    createDirectory: mutations.createDirectory,
    renameDirectory: mutations.renameDirectory,
    deleteDirectory: mutations.deleteDirectory,
    openCreateKb: mutations.openCreateKb,
    closeCreateKb: mutations.closeCreateKb,
    createKb: mutations.createKb,
    handleCreateFromIdChange: mutations.handleCreateFromIdChange,
    handleToggleExpanded: viewState.handleToggleExpanded,
    handleTreeNodeOpen: viewState.handleTreeNodeOpen,
    handleOpenBreadcrumb: viewState.handleOpenBreadcrumb,
    handleGoParent: viewState.handleGoParent,
    handleSelectRow,
    handleDoubleClickRow,
    handleDatasetDragStart: viewState.handleDatasetDragStart,
    handleDatasetDragEnd: viewState.handleDatasetDragEnd,
    handleDeleteSelectedKb: mutations.handleDeleteSelectedKb,
    handleTreeDragOver: viewState.handleTreeDragOver,
    handleTreeDrop,
    handleTreeDragLeave: viewState.handleTreeDragLeave,
  };
}
