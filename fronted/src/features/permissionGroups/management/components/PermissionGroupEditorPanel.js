import React from 'react';

import GroupEditorForm from './GroupEditorForm';
import { panelStyle } from '../permissionGroupManagementView';

export default function PermissionGroupEditorPanel({
  isMobile,
  pendingDeleteGroup,
  loading,
  saving,
  error,
  hint,
  mode,
  formData,
  editingGroup,
  knowledgeDatasetItems,
  chatAgents,
  setFormData,
  saveForm,
  cancelEdit,
  toggleKbAuth,
  toggleChatAuth,
  handleCreateGroup,
  handleCancelDeleteGroup,
  handleConfirmDeleteGroup,
}) {
  return (
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
          onClick={handleCreateGroup}
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

      {(error || hint) ? (
        <div style={{ padding: '10px 12px', borderBottom: '1px solid #e5e7eb' }}>
          {error ? <div style={{ color: '#b91c1c' }}>{error}</div> : null}
          {hint ? (
            <div style={{ color: '#047857', marginTop: error ? 8 : 0 }}>{hint}</div>
          ) : null}
        </div>
      ) : null}

      {pendingDeleteGroup ? (
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
              onClick={handleCancelDeleteGroup}
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
              onClick={handleConfirmDeleteGroup}
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
      ) : null}

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
  );
}
