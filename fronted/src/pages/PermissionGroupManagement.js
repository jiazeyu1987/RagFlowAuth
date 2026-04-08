import React from 'react';

import PermissionGroupEditorPanel from '../features/permissionGroups/management/components/PermissionGroupEditorPanel';
import PermissionGroupSidebar from '../features/permissionGroups/management/components/PermissionGroupSidebar';
import usePermissionGroupManagementPage from '../features/permissionGroups/management/usePermissionGroupManagementPage';

export default function PermissionGroupManagement() {
  const {
    isMobile,
    pendingDeleteGroup,
    hasEditableFolder,
    groups,
    loading,
    saving,
    error,
    hint,
    currentFolderId,
    selectedFolderId,
    expandedFolderIds,
    searchKeyword,
    selectedItem,
    dropTargetFolderId,
    mode,
    formData,
    editingGroup,
    folderIndexes,
    knowledgeDatasetItems,
    chatAgents,
    setSearchKeyword,
    setExpandedFolderIds,
    setSelectedItem,
    setFormData,
    fetchAll,
    createFolder,
    renameFolder,
    deleteFolder,
    saveForm,
    cancelEdit,
    toggleKbAuth,
    toggleChatAuth,
    openFolder,
    onDragOverFolder,
    onDropFolder,
    onDragLeaveFolder,
    startGroupDrag,
    endGroupDrag,
    handleCreateGroup,
    handleViewGroup,
    handleEditGroup,
    handleRequestDeleteGroup,
    handleCancelDeleteGroup,
    handleConfirmDeleteGroup,
  } = usePermissionGroupManagementPage();

  return (
    <div style={{ padding: isMobile ? 10 : 12 }}>
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: isMobile ? '1fr' : '320px 1fr',
          gap: 12,
        }}
      >
        <PermissionGroupSidebar
          isMobile={isMobile}
          hasEditableFolder={hasEditableFolder}
          groups={groups}
          currentFolderId={currentFolderId}
          selectedFolderId={selectedFolderId}
          expandedFolderIds={expandedFolderIds}
          searchKeyword={searchKeyword}
          selectedItem={selectedItem}
          dropTargetFolderId={dropTargetFolderId}
          folderIndexes={folderIndexes}
          setSearchKeyword={setSearchKeyword}
          setExpandedFolderIds={setExpandedFolderIds}
          setSelectedItem={setSelectedItem}
          fetchAll={fetchAll}
          createFolder={createFolder}
          renameFolder={renameFolder}
          deleteFolder={deleteFolder}
          openFolder={openFolder}
          onDragOverFolder={onDragOverFolder}
          onDropFolder={onDropFolder}
          onDragLeaveFolder={onDragLeaveFolder}
          startGroupDrag={startGroupDrag}
          endGroupDrag={endGroupDrag}
          handleViewGroup={handleViewGroup}
          handleEditGroup={handleEditGroup}
          handleRequestDeleteGroup={handleRequestDeleteGroup}
        />

        <PermissionGroupEditorPanel
          isMobile={isMobile}
          pendingDeleteGroup={pendingDeleteGroup}
          loading={loading}
          saving={saving}
          error={error}
          hint={hint}
          mode={mode}
          formData={formData}
          editingGroup={editingGroup}
          knowledgeDatasetItems={knowledgeDatasetItems}
          chatAgents={chatAgents}
          setFormData={setFormData}
          saveForm={saveForm}
          cancelEdit={cancelEdit}
          toggleKbAuth={toggleKbAuth}
          toggleChatAuth={toggleChatAuth}
          handleCreateGroup={handleCreateGroup}
          handleCancelDeleteGroup={handleCancelDeleteGroup}
          handleConfirmDeleteGroup={handleConfirmDeleteGroup}
        />
      </div>
    </div>
  );
}
