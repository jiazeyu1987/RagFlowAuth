import React from 'react';
import FolderTree from '../features/permissionGroups/management/components/FolderTree';
import GroupContentTable from '../features/permissionGroups/management/components/GroupContentTable';
import GroupEditorForm from '../features/permissionGroups/management/components/GroupEditorForm';
import { ROOT } from '../features/permissionGroups/management/constants';
import usePermissionGroupManagement from '../features/permissionGroups/management/usePermissionGroupManagement';

export default function PermissionGroupManagement() {
  const {
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
    dragGroupId,
    dropTargetFolderId,
    formData,
    editingGroup,
    folderIndexes,
    folderPath,
    filteredRows,
    knowledgeNodeItems,
    knowledgeDatasetItems,
    chatAgents,
    setSearchKeyword,
    setExpandedFolderIds,
    setSelectedItem,
    setSelectedFolderId,
    setFormData,
    fetchAll,
    createFolder,
    renameFolder,
    deleteFolder,
    startCreateGroup,
    startEditGroup,
    saveForm,
    cancelEdit,
    removeGroup,
    toggleNodeAuth,
    toggleKbAuth,
    toggleChatAuth,
    openFolder,
    onDragOverFolder,
    onDropFolder,
    onDragLeaveFolder,
    startGroupDrag,
    endGroupDrag,
  } = usePermissionGroupManagement();

  return (
    <div className="admin-med-page">
      <div className="admin-med-head">
        <h2 className="admin-med-title">权限组管理</h2>
      </div>

      <section className="medui-surface medui-card-pad">
        <div className="admin-med-actions" style={{ alignItems: 'center' }}>
          <input
            value={searchKeyword}
            onChange={(event) => setSearchKeyword(event.target.value)}
            placeholder="筛选当前目录内容"
            className="medui-input"
            style={{ width: 260, maxWidth: '100%' }}
          />
          <button onClick={fetchAll} type="button" className="medui-btn medui-btn--secondary">刷新</button>
          <button onClick={createFolder} type="button" className="medui-btn medui-btn--primary">新建目录</button>
          <button onClick={renameFolder} disabled={!selectedFolderId || selectedFolderId === ROOT} type="button" className="medui-btn medui-btn--warn">重命名目录</button>
          <button onClick={deleteFolder} disabled={!selectedFolderId || selectedFolderId === ROOT} type="button" className="medui-btn medui-btn--danger">删除目录</button>
          <button onClick={startCreateGroup} data-testid="pg-create-open" type="button" className="medui-btn medui-btn--success">新建权限组</button>
          <div className="admin-med-small">{`权限组总数：${groups.length}`}</div>
        </div>
      </section>

      <div className="admin-med-tree-layout">
        <section className="medui-surface">
          <div className="kb-med-pane-head">目录树</div>
          <div className="admin-med-tree-body">
            <FolderTree
              indexes={folderIndexes}
              currentFolderId={currentFolderId}
              selectedFolderId={selectedFolderId}
              expanded={expandedFolderIds}
              dropTargetFolderId={dropTargetFolderId}
              onToggleExpand={(id) =>
                setExpandedFolderIds((previous) =>
                  previous.includes(id)
                    ? previous.filter((value) => value !== id)
                    : [...previous, id]
                )
              }
              onOpenFolder={(id) => {
                openFolder(id);
                setSelectedItem(id ? { kind: 'folder', id } : null);
              }}
              onDragOverFolder={onDragOverFolder}
              onDropFolder={onDropFolder}
              onDragLeaveFolder={onDragLeaveFolder}
            />
          </div>
        </section>

        <section className="medui-surface">
          <div className="medui-card-pad" style={{ borderBottom: '1px solid #deebf8' }}>
            <div className="kb-med-breadcrumb">
              <span className="admin-med-small">路径：</span>
              {folderPath.map((folder, index) => (
                <React.Fragment key={folder.id || '__root__'}>
                  <button type="button" onClick={() => openFolder(folder.id)} className={currentFolderId === folder.id ? 'is-current' : ''}>{folder.name}</button>
                  {index < folderPath.length - 1 ? <span style={{ color: '#9ca3af' }}>{'>'}</span> : null}
                </React.Fragment>
              ))}
            </div>
            <div className="admin-med-small">可将表格中的权限组拖到左侧任意目录中。</div>
            {error ? <div className="admin-med-danger" style={{ marginTop: 8 }}>{error}</div> : null}
            {hint ? <div className="admin-med-success" style={{ marginTop: 8 }}>{hint}</div> : null}
          </div>

          <div className="admin-med-table-scroll" style={{ maxHeight: 280 }}>
            <GroupContentTable
              rows={filteredRows}
              groups={groups}
              selectedItem={selectedItem}
              dragGroupId={dragGroupId}
              onSelectItem={setSelectedItem}
              onSelectFolder={setSelectedFolderId}
              onOpenFolder={openFolder}
              onStartEditGroup={startEditGroup}
              onRemoveGroup={removeGroup}
              onStartGroupDrag={startGroupDrag}
              onEndGroupDrag={endGroupDrag}
            />
          </div>

          <div style={{ borderTop: '1px solid #deebf8', padding: 12 }}>
            <GroupEditorForm
              loading={loading}
              formData={formData}
              editingGroup={editingGroup}
              saving={saving}
              knowledgeNodeItems={knowledgeNodeItems}
              knowledgeDatasetItems={knowledgeDatasetItems}
              chatAgents={chatAgents}
              onSetFormData={setFormData}
              onToggleNodeAuth={toggleNodeAuth}
              onToggleKbAuth={toggleKbAuth}
              onToggleChatAuth={toggleChatAuth}
              onSaveForm={saveForm}
              onCancelEdit={cancelEdit}
            />
          </div>
        </section>
      </div>
    </div>
  );
}
