import React from 'react';

import CreateKnowledgeBaseDialog from '../features/knowledge/knowledgeBases/components/CreateKnowledgeBaseDialog';
import KnowledgeBasesTreePanel from '../features/knowledge/knowledgeBases/components/KnowledgeBasesTreePanel';
import KnowledgeBasesWorkspacePanel from '../features/knowledge/knowledgeBases/components/KnowledgeBasesWorkspacePanel';
import useKnowledgeBasesPage from '../features/knowledge/knowledgeBases/useKnowledgeBasesPage';
import { ChatConfigsPanel } from './ChatConfigsPanel';

const getSubtabButtonStyle = (active) => ({
  border: `1px solid ${active ? '#1d4ed8' : '#e5e7eb'}`,
  borderRadius: 10,
  background: active ? '#1d4ed8' : '#fff',
  color: active ? '#fff' : '#111827',
  cursor: 'pointer',
  padding: '9px 12px',
  fontWeight: 700,
});

export default function KnowledgeBases() {
  const page = useKnowledgeBasesPage();

  return (
    <div style={{ padding: page.isMobile ? 10 : 14 }}>
      <div style={{ marginBottom: 10, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
        <button
          data-testid="kbs-subtab-kbs"
          onClick={() => page.setSubtab('kbs')}
          style={getSubtabButtonStyle(page.subtab === 'kbs')}
        >
          {'\u77e5\u8bc6\u914d\u7f6e'}
        </button>
        <button
          data-testid="kbs-subtab-chats"
          onClick={() => page.setSubtab('chats')}
          style={getSubtabButtonStyle(page.subtab === 'chats')}
        >
          {'\u5bf9\u8bdd\u914d\u7f6e'}
        </button>
      </div>

      {page.subtab === 'kbs' ? (
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: page.isMobile ? '1fr' : '320px 1fr',
            gap: 14,
          }}
        >
          <KnowledgeBasesTreePanel
            isMobile={page.isMobile}
            treeError={page.treeError}
            indexes={page.indexes}
            currentDirId={page.currentDirId}
            selectedNodeId={page.selectedNodeId}
            expanded={page.expanded}
            handleToggleExpanded={page.handleToggleExpanded}
            handleTreeNodeOpen={page.handleTreeNodeOpen}
            canManageDirectory={page.canManageDirectory}
            dropTargetNodeId={page.dropTargetNodeId}
            handleTreeDragOver={page.handleTreeDragOver}
            handleTreeDrop={page.handleTreeDrop}
            handleTreeDragLeave={page.handleTreeDragLeave}
          />
          <KnowledgeBasesWorkspacePanel
            ROOT={page.ROOT}
            isMobile={page.isMobile}
            canManageDirectory={page.canManageDirectory}
            canManageDatasets={page.canManageDatasets}
            currentDirId={page.currentDirId}
            selectedNodeId={page.selectedNodeId}
            breadcrumb={page.breadcrumb}
            keyword={page.keyword}
            setKeyword={page.setKeyword}
            kbError={page.kbError}
            kbSaveStatus={page.kbSaveStatus}
            filteredRows={page.filteredRows}
            selectedItem={page.selectedItem}
            dragDatasetId={page.dragDatasetId}
            handleDatasetDragStart={page.handleDatasetDragStart}
            handleDatasetDragEnd={page.handleDatasetDragEnd}
            handleSelectRow={page.handleSelectRow}
            handleDoubleClickRow={page.handleDoubleClickRow}
            refreshAll={page.refreshAll}
            handleGoParent={page.handleGoParent}
            createDirectory={page.createDirectory}
            renameDirectory={page.renameDirectory}
            deleteDirectory={page.deleteDirectory}
            openCreateKb={page.openCreateKb}
            showSelectedDatasetDetails={page.showSelectedDatasetDetails}
            kbNameText={page.kbNameText}
            setKbNameText={page.setKbNameText}
            saveKb={page.saveKb}
            kbBusy={page.kbBusy}
            datasetDirId={page.datasetDirId}
            setDatasetDirId={page.setDatasetDirId}
            dirOptions={page.dirOptions}
            handleDeleteSelectedKb={page.handleDeleteSelectedKb}
            canDeleteSelectedKb={page.canDeleteSelectedKb}
            handleOpenBreadcrumb={page.handleOpenBreadcrumb}
          />
        </div>
      ) : (
        <ChatConfigsPanel />
      )}

      <CreateKnowledgeBaseDialog
        open={page.createOpen}
        onClose={page.closeCreateKb}
        createName={page.createName}
        onCreateNameChange={page.setCreateName}
        createFromId={page.createFromId}
        onCreateFromIdChange={page.handleCreateFromIdChange}
        kbList={page.kbList}
        createDirId={page.createDirId}
        onCreateDirIdChange={page.setCreateDirId}
        dirOptions={page.dirOptions}
        createError={page.createError}
        onCreate={page.createKb}
        isAdmin={page.canManageDatasets}
        kbBusy={page.kbBusy}
      />
    </div>
  );
}
