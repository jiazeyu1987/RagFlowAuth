import React from 'react';
import { ChatSelection, FolderSelectionList } from './SelectionLists';

export default function GroupEditorForm({
  loading,
  formData,
  editingGroup,
  saving,
  knowledgeNodeItems,
  knowledgeDatasetItems,
  chatAgents,
  onSetFormData,
  onToggleNodeAuth,
  onToggleKbAuth,
  onToggleChatAuth,
  onSaveForm,
  onCancelEdit,
}) {
  if (loading) return <div style={{ color: '#6b7280' }}>Loading...</div>;

  return (
    <form onSubmit={onSaveForm}>
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: '130px 1fr',
          gap: 10,
          alignItems: 'center',
          marginBottom: 10,
        }}
      >
        <label>Group Name</label>
        <input
          value={formData.group_name}
          onChange={(event) =>
            onSetFormData((previous) => ({
              ...previous,
              group_name: event.target.value,
            }))
          }
          required
          disabled={editingGroup?.is_system === 1}
          style={{
            padding: '9px 10px',
            border: '1px solid #d1d5db',
            borderRadius: 8,
          }}
        />
      </div>

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: '130px 1fr',
          gap: 10,
          alignItems: 'start',
          marginBottom: 10,
        }}
      >
        <label>Description</label>
        <textarea
          value={formData.description}
          onChange={(event) =>
            onSetFormData((previous) => ({
              ...previous,
              description: event.target.value,
            }))
          }
          rows={2}
          style={{
            padding: '9px 10px',
            border: '1px solid #d1d5db',
            borderRadius: 8,
          }}
        />
      </div>

      <FolderSelectionList
        title="Knowledge Folder Access"
        items={knowledgeNodeItems}
        selected={formData.accessible_kb_nodes || []}
        onToggle={onToggleNodeAuth}
        emptyText="No knowledge folders"
      />
      <FolderSelectionList
        title="Knowledge Base Access"
        items={knowledgeDatasetItems}
        selected={formData.accessible_kbs || []}
        onToggle={onToggleKbAuth}
        emptyText="No knowledge bases"
      />
      <ChatSelection
        chatAgents={chatAgents || []}
        selected={formData.accessible_chats || []}
        onToggle={onToggleChatAuth}
      />

      <div style={{ marginBottom: 12 }}>
        <div style={{ fontWeight: 700, marginBottom: 8 }}>Operation Permissions</div>
        <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
          <label>
            <input
              type="checkbox"
              checked={formData.can_upload}
              onChange={(event) =>
                onSetFormData((previous) => ({
                  ...previous,
                  can_upload: event.target.checked,
                }))
              }
            />{' '}
            Upload
          </label>
          <label>
            <input
              type="checkbox"
              checked={formData.can_review}
              onChange={(event) =>
                onSetFormData((previous) => ({
                  ...previous,
                  can_review: event.target.checked,
                }))
              }
            />{' '}
            Review
          </label>
          <label>
            <input
              type="checkbox"
              checked={formData.can_download}
              onChange={(event) =>
                onSetFormData((previous) => ({
                  ...previous,
                  can_download: event.target.checked,
                }))
              }
            />{' '}
            Download
          </label>
          <label>
            <input
              type="checkbox"
              checked={formData.can_delete}
              onChange={(event) =>
                onSetFormData((previous) => ({
                  ...previous,
                  can_delete: event.target.checked,
                }))
              }
            />{' '}
            Delete
          </label>
        </div>
      </div>

      <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10 }}>
        <button
          type="button"
          onClick={onCancelEdit}
          style={{
            border: '1px solid #d1d5db',
            borderRadius: 8,
            background: '#fff',
            cursor: 'pointer',
            padding: '8px 14px',
          }}
        >
          Cancel
        </button>
        <button
          type="submit"
          disabled={saving}
          style={{
            border: '1px solid #2563eb',
            borderRadius: 8,
            background: saving ? '#93c5fd' : '#2563eb',
            color: '#fff',
            cursor: saving ? 'not-allowed' : 'pointer',
            padding: '8px 14px',
          }}
        >
          Save
        </button>
      </div>
    </form>
  );
}
