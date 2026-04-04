import React, { useEffect, useMemo, useState } from 'react';
import FolderTree from '../features/permissionGroups/management/components/FolderTree';
import GroupEditorForm from '../features/permissionGroups/management/components/GroupEditorForm';
import { ROOT } from '../features/permissionGroups/management/constants';
import usePermissionGroupManagement from '../features/permissionGroups/management/usePermissionGroupManagement';

const panelStyle = {
  border: '1px solid #e5e7eb',
  borderRadius: 10,
  background: '#fff',
};

const MOBILE_BREAKPOINT = 768;

const iconButtonPalette = {
  neutral: {
    borderColor: '#d1d5db',
    background: '#ffffff',
    color: '#475569',
    shadow: 'rgba(148, 163, 184, 0.2)',
  },
  blue: {
    borderColor: '#2563eb',
    background: 'linear-gradient(135deg, #3b82f6 0%, #2563eb 100%)',
    color: '#ffffff',
    shadow: 'rgba(37, 99, 235, 0.28)',
  },
  orange: {
    borderColor: '#f59e0b',
    background: 'linear-gradient(135deg, #fbbf24 0%, #f59e0b 100%)',
    color: '#ffffff',
    shadow: 'rgba(245, 158, 11, 0.28)',
  },
  red: {
    borderColor: '#ef4444',
    background: 'linear-gradient(135deg, #f87171 0%, #ef4444 100%)',
    color: '#ffffff',
    shadow: 'rgba(239, 68, 68, 0.28)',
  },
};

function IconBase({ children }) {
  return (
    <svg
      viewBox="0 0 24 24"
      width="20"
      height="20"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.9"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {children}
    </svg>
  );
}

function RefreshIcon() {
  return (
    <IconBase>
      <path d="M20 11a8 8 0 1 0 2 5.5" />
      <path d="M20 4v7h-7" />
    </IconBase>
  );
}

function FolderAddIcon() {
  return (
    <IconBase>
      <path d="M3.5 7.5h6l2 2H20a1.5 1.5 0 0 1 1.5 1.5v6A2.5 2.5 0 0 1 19 19.5H5A2.5 2.5 0 0 1 2.5 17V9A1.5 1.5 0 0 1 4 7.5Z" />
      <path d="M12 11.5v5" />
      <path d="M9.5 14h5" />
    </IconBase>
  );
}

function RenameIcon() {
  return (
    <IconBase>
      <path d="M4 20h4.5l9.8-9.8a1.9 1.9 0 0 0 0-2.7l-1.8-1.8a1.9 1.9 0 0 0-2.7 0L4 15.5V20Z" />
      <path d="m12.5 7.5 4 4" />
    </IconBase>
  );
}

function DeleteIcon() {
  return (
    <IconBase>
      <path d="M4.5 7.5h15" />
      <path d="M9 7.5V5.8A1.8 1.8 0 0 1 10.8 4h2.4A1.8 1.8 0 0 1 15 5.8v1.7" />
      <path d="M7 7.5 8 19a2 2 0 0 0 2 1.8h4a2 2 0 0 0 2-1.8l1-11.5" />
      <path d="M10 11v5" />
      <path d="M14 11v5" />
    </IconBase>
  );
}

function ToolbarIconButton({
  label,
  icon,
  onClick,
  disabled = false,
  tone = 'neutral',
  testId,
}) {
  const palette = iconButtonPalette[tone] || iconButtonPalette.neutral;
  return (
    <button
      type="button"
      title={label}
      aria-label={label}
      data-testid={testId}
      onClick={onClick}
      disabled={disabled}
      style={{
        width: 46,
        height: 46,
        borderRadius: 14,
        border: `1px solid ${palette.borderColor}`,
        background: disabled ? '#e5e7eb' : palette.background,
        color: disabled ? '#94a3b8' : palette.color,
        boxShadow: disabled ? 'none' : `0 8px 18px ${palette.shadow}`,
        display: 'inline-flex',
        alignItems: 'center',
        justifyContent: 'center',
        cursor: disabled ? 'not-allowed' : 'pointer',
        transition: 'transform 120ms ease, box-shadow 120ms ease, opacity 120ms ease',
        opacity: disabled ? 0.75 : 1,
        padding: 0,
      }}
    >
      {icon}
    </button>
  );
}

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
    startCreateGroup,
    viewGroup,
    activateGroup,
    saveForm,
    cancelEdit,
    removeGroup,
    toggleKbAuth,
    toggleChatAuth,
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

  const hasEditableFolder = !!selectedFolderId && selectedFolderId !== ROOT;

  const toolbarButtons = useMemo(
    () => [
      {
        label: '刷新',
        icon: <RefreshIcon />,
        onClick: fetchAll,
        tone: 'neutral',
        testId: 'pg-toolbar-refresh',
      },
      {
        label: '新建文件夹',
        icon: <FolderAddIcon />,
        onClick: createFolder,
        tone: 'blue',
        testId: 'pg-toolbar-create-folder',
      },
      {
        label: '重命名文件夹',
        icon: <RenameIcon />,
        onClick: renameFolder,
        disabled: !hasEditableFolder,
        tone: 'orange',
        testId: 'pg-toolbar-rename-folder',
      },
      {
        label: '删除文件夹',
        icon: <DeleteIcon />,
        onClick: deleteFolder,
        disabled: !hasEditableFolder,
        tone: 'red',
        testId: 'pg-toolbar-delete-folder',
      },
    ],
    [createFolder, deleteFolder, fetchAll, hasEditableFolder, renameFolder]
  );

  return (
    <div style={{ padding: isMobile ? 10 : 12 }}>
      <div
        style={{ display: 'grid', gridTemplateColumns: isMobile ? '1fr' : '320px 1fr', gap: 12 }}
      >
        <section style={panelStyle}>
          <div
            style={{
              padding: '10px 12px',
              borderBottom: '1px solid #e5e7eb',
              display: 'flex',
              flexDirection: 'column',
              gap: 8,
            }}
          >
            <input
              value={searchKeyword}
              onChange={(event) => setSearchKeyword(event.target.value)}
              placeholder="筛选当前目录内容"
              style={{
                width: '100%',
                maxWidth: '100%',
                padding: '9px 10px',
                border: '1px solid #d1d5db',
                borderRadius: 8,
                boxSizing: 'border-box',
              }}
            />
            <div
              data-testid="pg-toolbar-actions"
              style={{
                display: 'flex',
                gap: 10,
                flexWrap: 'wrap',
                alignItems: 'center',
              }}
            >
              {toolbarButtons.map((button) => (
                <ToolbarIconButton
                  key={button.label}
                  label={button.label}
                  icon={button.icon}
                  onClick={button.onClick}
                  disabled={button.disabled}
                  tone={button.tone}
                  testId={button.testId}
                />
              ))}
            </div>
            <div style={{ color: '#6b7280', fontSize: 12 }}>分组总数: {groups.length}</div>
          </div>
          <div style={{ padding: 10, maxHeight: isMobile ? 280 : 700, overflowY: 'auto' }}>
            <FolderTree
              indexes={folderIndexes}
              groups={groups}
              currentFolderId={currentFolderId}
              selectedFolderId={selectedFolderId}
              selectedItem={selectedItem}
              expanded={expandedFolderIds}
              dropTargetFolderId={dropTargetFolderId}
              onSelectItem={setSelectedItem}
              onToggleExpand={(id) =>
                setExpandedFolderIds((previous) =>
                  previous.includes(id)
                    ? previous.filter((value) => value !== id)
                    : [...previous, id]
                )
              }
              onOpenFolder={openFolder}
              onDragOverFolder={onDragOverFolder}
              onDropFolder={onDropFolder}
              onDragLeaveFolder={onDragLeaveFolder}
              onViewGroup={(group) => {
                setPendingDeleteGroup(null);
                viewGroup(group);
              }}
              onStartEditGroup={(group) => {
                setPendingDeleteGroup(null);
                activateGroup(group);
              }}
              onRequestDeleteGroup={setPendingDeleteGroup}
              onStartGroupDrag={startGroupDrag}
              onEndGroupDrag={endGroupDrag}
            />
          </div>
        </section>

        <section style={panelStyle}>
          <div
            style={{
              padding: '10px 12px 0',
              display: 'flex',
              justifyContent: isMobile ? 'stretch' : 'flex-end',
            }}
          >
            <button
              type="button"
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
                padding: '8px 16px',
                fontSize: 14,
                fontWeight: 600,
                minWidth: isMobile ? '100%' : 'auto',
              }}
            >
              新建分组
            </button>
          </div>

          {(error || hint) && (
            <div style={{ padding: '10px 12px', borderBottom: '1px solid #e5e7eb' }}>
              {error && <div style={{ color: '#b91c1c' }}>{error}</div>}
              {hint && <div style={{ color: '#047857', marginTop: error ? 8 : 0 }}>{hint}</div>}
            </div>
          )}

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
                mode={mode}
                formData={formData}
                editingGroup={editingGroup}
                saving={saving}
                knowledgeDatasetItems={knowledgeDatasetItems}
                chatAgents={chatAgents}
                onSetFormData={setFormData}
                onToggleKbAuth={toggleKbAuth}
                onToggleChatAuth={toggleChatAuth}
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
