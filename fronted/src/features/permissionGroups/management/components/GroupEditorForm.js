import React from 'react';
import { ChatSelection, FolderSelectionList } from './SelectionLists';

const LOADING_TEXT = '\u52a0\u8f7d\u4e2d...';
const EMPTY_HINT =
  '\u8bf7\u5148\u4ece\u5de6\u4fa7\u9009\u62e9\u6743\u9650\u7ec4\u67e5\u770b\uff0c\u6216\u70b9\u51fb\u201c\u65b0\u5efa\u5206\u7ec4\u201d\u3002';
const VIEW_HINT =
  '\u5f53\u524d\u4e3a\u67e5\u770b\u6a21\u5f0f\uff0c\u70b9\u51fb\u5de6\u4fa7\u201c\u4fee\u6539\u201d\u53ef\u8fdb\u5165\u7f16\u8f91\u3002';
const GROUP_NAME_LABEL = '\u6743\u9650\u7ec4\u540d\u79f0';
const DESCRIPTION_LABEL = '\u63cf\u8ff0';
const KB_PERMISSION_LABEL = '\u77e5\u8bc6\u5e93\u6743\u9650';
const KB_EMPTY_TEXT = '\u6682\u65e0\u77e5\u8bc6\u5e93';
const ACTION_PERMISSION_LABEL = '\u64cd\u4f5c\u6743\u9650';
const CANCEL_LABEL = '\u53d6\u6d88';
const SAVE_LABEL = '\u4fdd\u5b58';

const fieldRowStyle = {
  display: 'grid',
  gridTemplateColumns: '130px 1fr',
  gap: 10,
};

export default function GroupEditorForm({
  loading,
  mode,
  formData,
  editingGroup,
  saving,
  knowledgeDatasetItems,
  chatAgents,
  onSetFormData,
  onToggleKbAuth,
  onToggleChatAuth,
  onSaveForm,
  onCancelEdit,
}) {
  const isReadOnly = mode !== 'edit' && mode !== 'create';
  const isSystemGroup = editingGroup?.is_system === 1;

  if (loading && !editingGroup && mode !== 'create') {
    return <div style={{ color: '#6b7280' }}>{LOADING_TEXT}</div>;
  }

  if (!editingGroup && mode !== 'create') {
    return <div style={{ color: '#6b7280' }}>{EMPTY_HINT}</div>;
  }

  return (
    <form onSubmit={onSaveForm}>
      {isReadOnly ? (
        <div
          style={{
            marginBottom: 12,
            padding: '10px 12px',
            borderRadius: 8,
            background: '#eff6ff',
            color: '#1d4ed8',
            fontSize: 13,
          }}
        >
          {VIEW_HINT}
        </div>
      ) : null}

      <div
        style={{
          ...fieldRowStyle,
          alignItems: 'center',
          marginBottom: 10,
        }}
      >
        <label>{GROUP_NAME_LABEL}</label>
        <input
          data-testid="pg-form-group-name"
          value={formData.group_name}
          onChange={(event) =>
            onSetFormData((previous) => ({
              ...previous,
              group_name: event.target.value,
            }))
          }
          required
          disabled={isReadOnly || isSystemGroup}
          style={{
            padding: '9px 10px',
            border: '1px solid #d1d5db',
            borderRadius: 8,
            background: isReadOnly || isSystemGroup ? '#f8fafc' : '#fff',
          }}
        />
      </div>

      <div
        style={{
          ...fieldRowStyle,
          alignItems: 'start',
          marginBottom: 10,
        }}
      >
        <label>{DESCRIPTION_LABEL}</label>
        <textarea
          data-testid="pg-form-description"
          value={formData.description}
          onChange={(event) =>
            onSetFormData((previous) => ({
              ...previous,
              description: event.target.value,
            }))
          }
          rows={2}
          disabled={isReadOnly}
          style={{
            padding: '9px 10px',
            border: '1px solid #d1d5db',
            borderRadius: 8,
            background: isReadOnly ? '#f8fafc' : '#fff',
          }}
        />
      </div>

      <FolderSelectionList
        title={KB_PERMISSION_LABEL}
        items={knowledgeDatasetItems}
        selected={formData.accessible_kbs || []}
        onToggle={onToggleKbAuth}
        disabled={isReadOnly}
        emptyText={KB_EMPTY_TEXT}
        itemTestIdPrefix="pg-form-kb"
        emptyTestId="pg-form-kb-empty"
      />
      <ChatSelection
        chatAgents={chatAgents || []}
        selected={formData.accessible_chats || []}
        onToggle={onToggleChatAuth}
        disabled={isReadOnly}
      />

      <div style={{ marginBottom: 12 }}>
        <div style={{ fontWeight: 700, marginBottom: 8 }}>{ACTION_PERMISSION_LABEL}</div>
        <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
          <label>
            <input
              type="checkbox"
              data-testid="pg-form-can-upload"
              checked={!!formData.can_upload}
              disabled={isReadOnly}
              onChange={(event) =>
                onSetFormData((previous) => ({
                  ...previous,
                  can_upload: event.target.checked,
                }))
              }
            />{' '}
            {'\u4e0a\u4f20'}
          </label>
          <label>
            <input
              type="checkbox"
              data-testid="pg-form-can-download"
              checked={!!formData.can_download}
              disabled={isReadOnly}
              onChange={(event) =>
                onSetFormData((previous) => ({
                  ...previous,
                  can_download: event.target.checked,
                }))
              }
            />{' '}
            {'\u4e0b\u8f7d'}
          </label>
          <label>
            <input
              type="checkbox"
              data-testid="pg-form-can-copy"
              checked={!!formData.can_copy}
              disabled={isReadOnly}
              onChange={(event) =>
                onSetFormData((previous) => ({
                  ...previous,
                  can_copy: event.target.checked,
                }))
              }
            />{' '}
            {'\u590d\u5236'}
          </label>
          <label>
            <input
              type="checkbox"
              data-testid="pg-form-can-delete"
              checked={!!formData.can_delete}
              disabled={isReadOnly}
              onChange={(event) =>
                onSetFormData((previous) => ({
                  ...previous,
                  can_delete: event.target.checked,
                }))
              }
            />{' '}
            {'\u5220\u9664'}
          </label>
        </div>
      </div>

      {!isReadOnly ? (
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10 }}>
          <button
            type="button"
            data-testid="pg-form-cancel"
            onClick={onCancelEdit}
            style={{
              border: '1px solid #d1d5db',
              borderRadius: 8,
              background: '#fff',
              cursor: 'pointer',
              padding: '8px 14px',
            }}
          >
            {CANCEL_LABEL}
          </button>
          <button
            type="submit"
            data-testid="pg-form-submit"
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
            {SAVE_LABEL}
          </button>
        </div>
      ) : null}
    </form>
  );
}
