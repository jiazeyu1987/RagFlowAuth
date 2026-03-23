import React, { useEffect, useState } from 'react';
import FolderTree from '../features/permissionGroups/management/components/FolderTree';
import GroupContentTable from '../features/permissionGroups/management/components/GroupContentTable';
import GroupEditorForm from '../features/permissionGroups/management/components/GroupEditorForm';
import { ROOT } from '../features/permissionGroups/management/constants';
import usePermissionGroupManagement from '../features/permissionGroups/management/usePermissionGroupManagement';

const panelStyle = {
  border: '1px solid #e5e7eb',
  borderRadius: 10,
  background: '#fff',
};

const MOBILE_BREAKPOINT = 768;

export default function PermissionGroupManagement() {
  const [isMobile, setIsMobile] = useState(() => {
    if (typeof window === 'undefined') return false;
    return window.innerWidth <= MOBILE_BREAKPOINT;
  });
  const [pendingDeleteGroup, setPendingDeleteGroup] = useState(null);

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
    knowledgeNodeTreeNodes,
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
    toggleToolAuth,
    openFolder,
    onDragOverFolder,
    onDropFolder,
    onDragLeaveFolder,
    startGroupDrag,
    endGroupDrag,
  } = usePermissionGroupManagement();

  useEffect(() => {
    if (typeof window === 'undefined') return undefined;

    const handleResize = () => setIsMobile(window.innerWidth <= MOBILE_BREAKPOINT);
    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  return (
    <div style={{ padding: isMobile ? 10 : 12 }}>
      <div
        style={{
          display: 'flex',
          flexDirection: isMobile ? 'column' : 'row',
          justifyContent: 'space-between',
          gap: 10,
          alignItems: isMobile ? 'stretch' : 'center',
          marginBottom: 10,
        }}
      >
        <h2 style={{ margin: 0 }}>权限组管理</h2>
      </div>

      <section style={{ ...panelStyle, marginBottom: 12 }}>
        <div
          style={{
            padding: '10px 12px',
            borderBottom: '1px solid #e5e7eb',
            display: 'flex',
            flexDirection: isMobile ? 'column' : 'row',
            gap: 8,
            flexWrap: 'wrap',
            alignItems: isMobile ? 'stretch' : 'center',
          }}
        >
          <input
            value={searchKeyword}
            onChange={(event) => setSearchKeyword(event.target.value)}
            placeholder="筛选当前目录内容"
            style={{
              width: isMobile ? '100%' : 260,
              maxWidth: '100%',
              padding: '9px 10px',
              border: '1px solid #d1d5db',
              borderRadius: 8,
            }}
          />
          <button
            onClick={fetchAll}
            style={{
              border: '1px solid #d1d5db',
              borderRadius: 8,
              background: '#fff',
              cursor: 'pointer',
              padding: '9px 12px',
              width: isMobile ? '100%' : 'auto',
            }}
          >
            刷新
          </button>
          <button
            onClick={createFolder}
            style={{
              border: '1px solid #2563eb',
              borderRadius: 8,
              background: '#2563eb',
              color: '#fff',
              cursor: 'pointer',
              padding: '9px 12px',
              width: isMobile ? '100%' : 'auto',
            }}
          >
            新建文件夹
          </button>
          <button
            onClick={renameFolder}
            disabled={!selectedFolderId || selectedFolderId === ROOT}
            style={{
              border: '1px solid #f59e0b',
              borderRadius: 8,
              background:
                !selectedFolderId || selectedFolderId === ROOT ? '#fde68a' : '#f59e0b',
              color: '#fff',
              cursor: !selectedFolderId || selectedFolderId === ROOT ? 'not-allowed' : 'pointer',
              padding: '9px 12px',
              width: isMobile ? '100%' : 'auto',
            }}
          >
            重命名文件夹
          </button>
          <button
            onClick={deleteFolder}
            disabled={!selectedFolderId || selectedFolderId === ROOT}
            style={{
              border: '1px solid #ef4444',
              borderRadius: 8,
              background:
                !selectedFolderId || selectedFolderId === ROOT ? '#fecaca' : '#ef4444',
              color: '#fff',
              cursor: !selectedFolderId || selectedFolderId === ROOT ? 'not-allowed' : 'pointer',
              padding: '9px 12px',
              width: isMobile ? '100%' : 'auto',
            }}
          >
            删除文件夹
          </button>
          <button
            data-testid="pg-create-open"
            onClick={() => {
              setPendingDeleteGroup(null);
              startCreateGroup();
            }}
            style={{
              border: '1px solid #10b981',
              borderRadius: 8,
              background: '#10b981',
              color: '#fff',
              cursor: 'pointer',
              padding: '9px 12px',
              width: isMobile ? '100%' : 'auto',
            }}
          >
            新建分组
          </button>
          <div style={{ color: '#6b7280', fontSize: 12 }}>分组总数: {groups.length}</div>
        </div>
      </section>

      <div
        style={{ display: 'grid', gridTemplateColumns: isMobile ? '1fr' : '320px 1fr', gap: 12 }}
      >
        <section style={panelStyle}>
          <div
            style={{
              padding: '10px 12px',
              borderBottom: '1px solid #e5e7eb',
              fontWeight: 800,
            }}
          >
            文件夹树
          </div>
          <div style={{ padding: 10, maxHeight: isMobile ? 280 : 700, overflowY: 'auto' }}>
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

        <section style={panelStyle}>
          <div style={{ padding: '10px 12px', borderBottom: '1px solid #e5e7eb' }}>
            <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 8 }}>
              <span style={{ color: '#6b7280', fontSize: 13 }}>路径:</span>
              {folderPath.map((folder, index) => (
                <React.Fragment key={folder.id || '__root__'}>
                  <button
                    type="button"
                    onClick={() => openFolder(folder.id)}
                    style={{
                      border: 'none',
                      background: 'transparent',
                      cursor: 'pointer',
                      color: currentFolderId === folder.id ? '#1d4ed8' : '#374151',
                      fontWeight: currentFolderId === folder.id ? 700 : 500,
                      padding: 0,
                    }}
                  >
                    {folder.name}
                  </button>
                  {index < folderPath.length - 1 && <span style={{ color: '#9ca3af' }}>{'>'}</span>}
                </React.Fragment>
              ))}
            </div>
            <div style={{ color: '#6b7280', fontSize: 12 }}>
              可从表格中拖拽分组，并拖放到左侧任意文件夹中。
            </div>
            {error && <div style={{ color: '#b91c1c', marginTop: 8 }}>{error}</div>}
            {hint && <div style={{ color: '#047857', marginTop: 8 }}>{hint}</div>}
          </div>

          <div style={{ maxHeight: 280, overflowY: 'auto' }}>
            <GroupContentTable
              rows={filteredRows}
              groups={groups}
              selectedItem={selectedItem}
              dragGroupId={dragGroupId}
              onSelectItem={setSelectedItem}
              onSelectFolder={setSelectedFolderId}
              onOpenFolder={openFolder}
              onStartEditGroup={(group) => {
                setPendingDeleteGroup(null);
                startEditGroup(group);
              }}
              onRequestDeleteGroup={setPendingDeleteGroup}
              onStartGroupDrag={startGroupDrag}
              onEndGroupDrag={endGroupDrag}
            />
          </div>

          {pendingDeleteGroup && (
            <div
              style={{
                borderTop: '1px solid #e5e7eb',
                padding: 12,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                gap: 12,
                background: '#fff7ed',
              }}
            >
              <span style={{ color: '#7c2d12', fontSize: 13 }}>
                确认删除权限组“{pendingDeleteGroup.group_name}”？
              </span>
              <div style={{ display: 'flex', gap: 8 }}>
                <button
                  type="button"
                  onClick={() => setPendingDeleteGroup(null)}
                  style={{
                    border: '1px solid #d1d5db',
                    borderRadius: 8,
                    background: '#fff',
                    cursor: 'pointer',
                    padding: '6px 10px',
                  }}
                >
                  取消
                </button>
                <button
                  type="button"
                  data-testid="pg-delete-confirm"
                  onClick={async () => {
                    const group = pendingDeleteGroup;
                    setPendingDeleteGroup(null);
                    const rawConfirm = window.confirm;
                    window.confirm = () => true;
                    try {
                      await removeGroup(group);
                    } finally {
                      window.confirm = rawConfirm;
                    }
                  }}
                  style={{
                    border: '1px solid #ef4444',
                    borderRadius: 8,
                    background: '#ef4444',
                    color: '#fff',
                    cursor: 'pointer',
                    padding: '6px 10px',
                  }}
                >
                  确认删除
                </button>
              </div>
            </div>
          )}

          <div style={{ borderTop: '1px solid #e5e7eb', padding: 12 }}>
            <div data-testid="pg-modal">
              <GroupEditorForm
                loading={loading}
                formData={formData}
                editingGroup={editingGroup}
                saving={saving}
                knowledgeNodeTreeNodes={knowledgeNodeTreeNodes}
                knowledgeDatasetItems={knowledgeDatasetItems}
                chatAgents={chatAgents}
                onSetFormData={setFormData}
                onToggleNodeAuth={toggleNodeAuth}
                onToggleKbAuth={toggleKbAuth}
                onToggleChatAuth={toggleChatAuth}
                onToggleToolAuth={toggleToolAuth}
                onSaveForm={saveForm}
                onCancelEdit={cancelEdit}
              />
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
