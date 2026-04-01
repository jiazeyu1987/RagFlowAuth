import React from 'react';
import { ChatSelection, FolderSelectionList, KnowledgeNodeTreeSelection } from './SelectionLists';
import { TOOL_PERMISSION_ITEMS } from '../constants';

export default function GroupEditorForm({
  loading,
  formData,
  editingGroup,
  saving,
  knowledgeNodeTreeNodes,
  knowledgeDatasetItems,
  chatAgents,
  onSetFormData,
  onToggleNodeAuth,
  onToggleKbAuth,
  onToggleChatAuth,
  onToggleToolAuth,
  onSaveForm,
  onCancelEdit,
}) {
  if (loading) return <div style={{ color: '#6b7280' }}>加载中...</div>;

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
        <label>权限组名称</label>
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
        <label>描述</label>
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
          style={{
            padding: '9px 10px',
            border: '1px solid #d1d5db',
            borderRadius: 8,
          }}
        />
      </div>

      <KnowledgeNodeTreeSelection
        title="知识目录权限"
        nodes={knowledgeNodeTreeNodes}
        selected={formData.accessible_kb_nodes || []}
        onToggle={onToggleNodeAuth}
        emptyText="暂无知识目录"
        itemTestIdPrefix="pg-form-kb-node"
      />
      <FolderSelectionList
        title="知识库权限"
        items={knowledgeDatasetItems}
        selected={formData.accessible_kbs || []}
        onToggle={onToggleKbAuth}
        emptyText="暂无知识库"
        itemTestIdPrefix="pg-form-kb"
        emptyTestId="pg-form-kb-empty"
      />
      <ChatSelection
        chatAgents={chatAgents || []}
        selected={formData.accessible_chats || []}
        onToggle={onToggleChatAuth}
      />
      <FolderSelectionList
        title="实用工具权限"
        items={TOOL_PERMISSION_ITEMS}
        selected={formData.accessible_tools || []}
        onToggle={onToggleToolAuth}
        emptyText="暂无工具"
        itemTestIdPrefix="pg-form-tool"
        emptyTestId="pg-form-tool-empty"
      />
      <div style={{ marginTop: '-4px', marginBottom: 10, color: '#6b7280', fontSize: 12 }}>
        留空表示可访问全部实用工具；勾选后仅可访问所选工具。
      </div>

      <div style={{ marginBottom: 12 }}>
        <div style={{ fontWeight: 700, marginBottom: 8 }}>操作权限</div>
        <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
          <label>
            <input
              type="checkbox"
              data-testid="pg-form-can-upload"
              checked={!!formData.can_upload}
              onChange={(event) =>
                onSetFormData((previous) => ({
                  ...previous,
                  can_upload: event.target.checked,
                }))
              }
            />{' '}
            上传
          </label>
          <label>
            <input
              type="checkbox"
              data-testid="pg-form-can-review"
              checked={!!formData.can_review}
              onChange={(event) =>
                onSetFormData((previous) => ({
                  ...previous,
                  can_review: event.target.checked,
                }))
              }
            />{' '}
            审核
          </label>
          <label>
            <input
              type="checkbox"
              data-testid="pg-form-can-download"
              checked={!!formData.can_download}
              onChange={(event) =>
                onSetFormData((previous) => ({
                  ...previous,
                  can_download: event.target.checked,
                }))
              }
            />{' '}
            下载
          </label>
          <label>
            <input
              type="checkbox"
              data-testid="pg-form-can-copy"
              checked={!!formData.can_copy}
              onChange={(event) =>
                onSetFormData((previous) => ({
                  ...previous,
                  can_copy: event.target.checked,
                }))
              }
            />{' '}
            {"\u590d\u5236"}
          </label>
          <label>
            <input
              type="checkbox"
              data-testid="pg-form-can-delete"
              checked={!!formData.can_delete}
              onChange={(event) =>
                onSetFormData((previous) => ({
                  ...previous,
                  can_delete: event.target.checked,
                }))
              }
            />{' '}
            删除
          </label>
          <label>
            <input
              type="checkbox"
              data-testid="pg-form-can-manage-kb-directory"
              checked={!!formData.can_manage_kb_directory}
              onChange={(event) =>
                onSetFormData((previous) => ({
                  ...previous,
                  can_manage_kb_directory: event.target.checked,
                }))
              }
            />{' '}
            目录操作与文件移动
          </label>
          <label>
            <input
              type="checkbox"
              data-testid="pg-form-can-view-kb-config"
              checked={formData.can_view_kb_config !== false}
              onChange={(event) =>
                onSetFormData((previous) => ({
                  ...previous,
                  can_view_kb_config: event.target.checked,
                }))
              }
            />{' '}
            可查看知识配置
          </label>
          <label>
            <input
              type="checkbox"
              data-testid="pg-form-can-view-tools"
              checked={formData.can_view_tools !== false}
              onChange={(event) =>
                onSetFormData((previous) => ({
                  ...previous,
                  can_view_tools: event.target.checked,
                }))
              }
            />{' '}
            可查看实用工具
          </label>
        </div>
      </div>

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
          取消
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
          保存
        </button>
      </div>
    </form>
  );
}
