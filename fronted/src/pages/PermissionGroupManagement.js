import React, { useEffect, useMemo, useState } from 'react';
import { permissionGroupsApi } from '../features/permissionGroups/api';

const ROOT = '';

const emptyForm = {
  group_name: '',
  description: '',
  folder_id: null,
  accessible_kbs: [],
  accessible_kb_nodes: [],
  accessible_chats: [],
  can_upload: false,
  can_review: false,
  can_download: true,
  can_delete: false,
};

function normalizeGroups(rawGroups, groupBindings = {}) {
  return (rawGroups || []).map((g) => {
    const key = String(g?.group_id ?? '');
    const bound = Object.prototype.hasOwnProperty.call(groupBindings || {}, key) ? groupBindings[key] : undefined;
    const folderId = g?.folder_id ?? bound ?? null;
    return {
      ...g,
      folder_id: typeof folderId === 'string' && folderId ? folderId : null,
      accessible_kbs: Array.isArray(g?.accessible_kbs) ? g.accessible_kbs : [],
      accessible_kb_nodes: Array.isArray(g?.accessible_kb_nodes) ? g.accessible_kb_nodes : [],
      accessible_chats: Array.isArray(g?.accessible_chats) ? g.accessible_chats : [],
    };
  });
}

function buildFolderIndexes(folders) {
  const byId = new Map();
  const childrenByParent = new Map();
  (folders || []).forEach((f) => {
    if (!f?.id) return;
    byId.set(f.id, f);
    const parent = f.parent_id || ROOT;
    if (!childrenByParent.has(parent)) childrenByParent.set(parent, []);
    childrenByParent.get(parent).push(f);
  });
  for (const arr of childrenByParent.values()) {
    arr.sort((a, b) => String(a.name || '').localeCompare(String(b.name || ''), 'zh-Hans-CN'));
  }
  return { byId, childrenByParent };
}

function pathFolders(folderId, byId) {
  if (!folderId) return [];
  const out = [];
  const seen = new Set();
  let cur = folderId;
  while (cur && !seen.has(cur)) {
    seen.add(cur);
    const folder = byId.get(cur);
    if (!folder) break;
    out.push(folder);
    cur = folder.parent_id || ROOT;
  }
  return out.reverse();
}

function toggleInArray(values, item) {
  const list = Array.isArray(values) ? values : [];
  return list.includes(item) ? list.filter((v) => v !== item) : [...list, item];
}

function FolderTree({
  indexes,
  currentFolderId,
  selectedFolderId,
  expanded,
  dropTargetFolderId,
  onToggleExpand,
  onOpenFolder,
  onDragOverFolder,
  onDropFolder,
  onDragLeaveFolder,
}) {
  const renderFolder = (folder, depth) => {
    const id = folder.id;
    const children = indexes.childrenByParent.get(id) || [];
    const hasChildren = children.length > 0;
    const isExpanded = expanded.includes(id);
    const isCurrent = currentFolderId === id;
    const isSelected = selectedFolderId === id;
    return (
      <div key={id}>
        <div
          style={{
            marginLeft: depth * 16,
            borderRadius: 6,
            display: 'flex',
            alignItems: 'center',
            gap: 6,
            padding: '3px 6px',
            background:
              dropTargetFolderId === id
                ? '#dcfce7'
                : isCurrent
                  ? '#dbeafe'
                  : isSelected
                    ? '#eff6ff'
                    : 'transparent',
          }}
          onDragOver={(e) => onDragOverFolder(e, id)}
          onDrop={(e) => onDropFolder(e, id)}
          onDragLeave={(e) => onDragLeaveFolder(e, id)}
        >
          <button
            type="button"
            onClick={() => hasChildren && onToggleExpand(id)}
            style={{ width: 14, border: 'none', background: 'transparent', cursor: hasChildren ? 'pointer' : 'default', color: '#6b7280', padding: 0 }}
          >
            {hasChildren ? (isExpanded ? '▾' : '▸') : ''}
          </button>
          <button
            type="button"
            onClick={() => onOpenFolder(id)}
            style={{ border: 'none', background: 'transparent', cursor: 'pointer', width: '100%', textAlign: 'left', padding: 0 }}
            title={folder.path || folder.name}
          >
            📁 {folder.name || '(未命名文件夹)'}
          </button>
        </div>
        {isExpanded && children.map((c) => renderFolder(c, depth + 1))}
      </div>
    );
  };

  const roots = indexes.childrenByParent.get(ROOT) || [];
  return (
    <div>
      <div
        style={{
          borderRadius: 6,
          padding: '3px 6px',
          marginBottom: 6,
          background: dropTargetFolderId === ROOT ? '#dcfce7' : currentFolderId === ROOT ? '#dbeafe' : 'transparent',
        }}
        onDragOver={(e) => onDragOverFolder(e, ROOT)}
        onDrop={(e) => onDropFolder(e, ROOT)}
        onDragLeave={(e) => onDragLeaveFolder(e, ROOT)}
      >
        <button type="button" onClick={() => onOpenFolder(ROOT)} style={{ border: 'none', background: 'transparent', cursor: 'pointer', width: '100%', textAlign: 'left', padding: 0 }}>
          🖥️ 根目录
        </button>
      </div>
      {roots.map((f) => renderFolder(f, 0))}
      {!roots.length && <div style={{ color: '#6b7280', fontSize: 13 }}>暂无文件夹</div>}
    </div>
  );
}

function FolderSelectionList({ title, items, selected, onToggle, emptyText }) {
  return (
    <div style={{ marginBottom: 12 }}>
      <div style={{ fontWeight: 700, marginBottom: 8 }}>{title}</div>
      {!items.length ? (
        <div style={{ color: '#6b7280', fontSize: 13 }}>{emptyText}</div>
      ) : (
        <div style={{ maxHeight: 170, overflowY: 'auto', border: '1px solid #e5e7eb', borderRadius: 8, padding: 8 }}>
          {items.map((item) => (
            <label key={item.id} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '4px 2px', cursor: 'pointer' }}>
              <input type="checkbox" checked={selected.includes(item.id)} onChange={() => onToggle(item.id)} />
              <span>{item.name}</span>
            </label>
          ))}
        </div>
      )}
    </div>
  );
}

function ChatSelection({ chatAgents, selected, onToggle }) {
  return (
    <div style={{ marginBottom: 12 }}>
      <div style={{ fontWeight: 700, marginBottom: 8 }}>聊天授权</div>
      {!chatAgents.length ? (
        <div style={{ color: '#6b7280', fontSize: 13 }}>暂无聊天体</div>
      ) : (
        <div style={{ maxHeight: 170, overflowY: 'auto', border: '1px solid #e5e7eb', borderRadius: 8, padding: 8 }}>
          {chatAgents.map((chat) => (
            <label key={chat.id} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '4px 2px', cursor: 'pointer' }}>
              <input type="checkbox" checked={selected.includes(chat.id)} onChange={() => onToggle(chat.id)} />
              <span>{chat.name} ({chat.type || 'chat'})</span>
            </label>
          ))}
        </div>
      )}
    </div>
  );
}

export default function PermissionGroupManagement() {
  const [groups, setGroups] = useState([]);
  const [groupFolders, setGroupFolders] = useState([]);
  const [knowledgeTree, setKnowledgeTree] = useState({ nodes: [], datasets: [] });
  const [chatAgents, setChatAgents] = useState([]);

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [hint, setHint] = useState('');

  const [currentFolderId, setCurrentFolderId] = useState(ROOT);
  const [selectedFolderId, setSelectedFolderId] = useState(ROOT);
  const [expandedFolderIds, setExpandedFolderIds] = useState([]);
  const [searchKeyword, setSearchKeyword] = useState('');
  const [selectedItem, setSelectedItem] = useState(null); // { kind: 'folder'|'group', id: string|number }
  const [dragGroupId, setDragGroupId] = useState(null);
  const [dropTargetFolderId, setDropTargetFolderId] = useState(null);

  const [mode, setMode] = useState('');
  const [editingGroupId, setEditingGroupId] = useState(null);
  const [formData, setFormData] = useState({ ...emptyForm });

  const folderIndexes = useMemo(() => buildFolderIndexes(groupFolders), [groupFolders]);

  const folderPath = useMemo(
    () => [{ id: ROOT, name: '根目录' }, ...pathFolders(currentFolderId, folderIndexes.byId).map((f) => ({ id: f.id, name: f.name || '(未命名文件夹)' }))],
    [currentFolderId, folderIndexes.byId]
  );

  const groupsInCurrentFolder = useMemo(
    () => groups.filter((g) => (g.folder_id || ROOT) === currentFolderId),
    [groups, currentFolderId]
  );

  const contentRows = useMemo(() => {
    const rows = [];
    (folderIndexes.childrenByParent.get(currentFolderId) || []).forEach((folder) => {
      rows.push({ kind: 'folder', id: folder.id, name: folder.name || '(未命名文件夹)', type: '文件夹' });
    });
    groupsInCurrentFolder.forEach((group) => {
      rows.push({ kind: 'group', id: group.group_id, name: group.group_name || '(未命名权限组)', type: '权限组' });
    });
    return rows;
  }, [currentFolderId, folderIndexes.childrenByParent, groupsInCurrentFolder]);

  const filteredRows = useMemo(() => {
    const kw = String(searchKeyword || '').trim().toLowerCase();
    if (!kw) return contentRows;
    return contentRows.filter((r) => String(r.name || '').toLowerCase().includes(kw) || String(r.id || '').toLowerCase().includes(kw));
  }, [contentRows, searchKeyword]);

  const editingGroup = useMemo(
    () => groups.find((g) => g.group_id === editingGroupId) || null,
    [groups, editingGroupId]
  );

  const knowledgeNodeItems = useMemo(
    () => (knowledgeTree?.nodes || []).map((n) => ({ id: n.id, name: `${n.name || '(未命名目录)'} (${n.path || '/'})` })),
    [knowledgeTree?.nodes]
  );

  const knowledgeDatasetItems = useMemo(
    () => (knowledgeTree?.datasets || []).map((d) => ({ id: d.id, name: `${d.name || '(未命名知识库)'}${d.node_path && d.node_path !== '/' ? ` (${d.node_path})` : ''}` })),
    [knowledgeTree?.datasets]
  );

  function fillFormFromGroup(group) {
    return {
      ...emptyForm,
      group_name: group?.group_name || '',
      description: group?.description || '',
      folder_id: group?.folder_id || null,
      accessible_kbs: group?.accessible_kbs || [],
      accessible_kb_nodes: group?.accessible_kb_nodes || [],
      accessible_chats: group?.accessible_chats || [],
      can_upload: !!group?.can_upload,
      can_review: !!group?.can_review,
      can_download: group?.can_download !== false,
      can_delete: !!group?.can_delete,
    };
  }

  function ensureFolderExpanded(folderId) {
    if (!folderId) return;
    const ids = pathFolders(folderId, folderIndexes.byId).map((f) => f.id);
    setExpandedFolderIds((prev) => {
      const set = new Set(prev);
      ids.forEach((id) => set.add(id));
      return Array.from(set);
    });
  }

  function openFolder(folderId) {
    const next = folderId || ROOT;
    setCurrentFolderId(next);
    setSelectedFolderId(next);
    if (next) ensureFolderExpanded(next);
  }

  function startCreateGroup() {
    setMode('create');
    setEditingGroupId(null);
    setFormData({ ...emptyForm, folder_id: currentFolderId || null });
  }

  function startEditGroup(group) {
    if (!group) return;
    setMode('edit');
    setEditingGroupId(group.group_id);
    setFormData(fillFormFromGroup(group));
  }

  async function fetchAll() {
    setLoading(true);
    setError('');
    try {
      const [groupsRes, folderRes, knowledgeRes, chatsRes] = await Promise.all([
        permissionGroupsApi.list(),
        permissionGroupsApi.listGroupFolders(),
        permissionGroupsApi.listKnowledgeTree(),
        permissionGroupsApi.listChats(),
      ]);
      const folderData = folderRes?.data || { folders: [], group_bindings: {}, root_group_count: 0 };
      const normalizedGroups = normalizeGroups(groupsRes?.data || [], folderData.group_bindings || {});
      setGroups(normalizedGroups);
      setGroupFolders(folderData.folders || []);
      setKnowledgeTree(knowledgeRes?.data || { nodes: [], datasets: [] });
      setChatAgents(chatsRes?.data || []);
      return normalizedGroups;
    } catch (e) {
      setError(e?.message || '加载失败');
      return [];
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchAll().then((list) => {
      if (list.length) startEditGroup(list[0]);
      else startCreateGroup();
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function saveForm(e) {
    e.preventDefault();
    setSaving(true);
    setError('');
    setHint('');
    try {
      if (mode === 'create') {
        const res = await permissionGroupsApi.create(formData);
        const newId = res?.data?.group_id;
        const nextGroups = await fetchAll();
        const created = nextGroups.find((g) => g.group_id === newId) || null;
        if (created) {
          startEditGroup(created);
          setHint('权限组已创建');
        }
      } else if (mode === 'edit' && editingGroupId != null) {
        await permissionGroupsApi.update(editingGroupId, formData);
        const nextGroups = await fetchAll();
        const updated = nextGroups.find((g) => g.group_id === editingGroupId) || null;
        if (updated) {
          startEditGroup(updated);
          setHint('权限组已保存');
        }
      }
    } catch (e2) {
      setError(e2?.message || '保存失败');
    } finally {
      setSaving(false);
    }
  }

  function cancelEdit() {
    if (mode === 'edit' && editingGroup) {
      setFormData(fillFormFromGroup(editingGroup));
      return;
    }
    startCreateGroup();
  }

  async function removeGroup(group) {
    if (!group?.group_id) return;
    if (!window.confirm(`确认删除权限组「${group.group_name}」吗？`)) return;
    setError('');
    setHint('');
    try {
      await permissionGroupsApi.remove(group.group_id);
      const nextGroups = await fetchAll();
      if (editingGroupId === group.group_id) {
        if (nextGroups.length) startEditGroup(nextGroups[0]);
        else startCreateGroup();
      }
      setHint('权限组已删除');
    } catch (e) {
      setError(e?.message || '删除失败');
    }
  }

  async function createFolder() {
    const name = window.prompt('请输入新文件夹名称');
    if (!name || !name.trim()) return;
    setError('');
    setHint('');
    try {
      const res = await permissionGroupsApi.createFolder({ name: name.trim(), parent_id: currentFolderId || null });
      const newId = res?.data?.id || '';
      await fetchAll();
      if (newId) {
        openFolder(newId);
        setSelectedItem({ kind: 'folder', id: newId });
      }
      setHint('文件夹已创建');
    } catch (e) {
      setError(e?.message || '创建文件夹失败');
    }
  }

  async function renameFolder() {
    const targetId = selectedFolderId || ROOT;
    if (!targetId || targetId === ROOT) return;
    const folder = folderIndexes.byId.get(targetId);
    const next = window.prompt('请输入新文件夹名称', folder?.name || '');
    if (!next || !next.trim()) return;
    setError('');
    setHint('');
    try {
      await permissionGroupsApi.updateFolder(targetId, { name: next.trim() });
      await fetchAll();
      ensureFolderExpanded(targetId);
      setHint('文件夹已重命名');
    } catch (e) {
      setError(e?.message || '重命名文件夹失败');
    }
  }

  async function deleteFolder() {
    const targetId = selectedFolderId || ROOT;
    if (!targetId || targetId === ROOT) return;
    const folder = folderIndexes.byId.get(targetId);
    if (!window.confirm(`确认删除文件夹「${folder?.name || targetId}」吗？\n必须先清空子文件夹和权限组。`)) return;
    setError('');
    setHint('');
    try {
      await permissionGroupsApi.removeFolder(targetId);
      const parent = folder?.parent_id || ROOT;
      openFolder(parent);
      setSelectedItem(null);
      await fetchAll();
      setHint('文件夹已删除');
    } catch (e) {
      setError(e?.message || '删除文件夹失败');
    }
  }

  function toggleNodeAuth(nodeId) {
    setFormData((prev) => ({ ...prev, accessible_kb_nodes: toggleInArray(prev.accessible_kb_nodes, nodeId) }));
  }

  function toggleKbAuth(kbId) {
    setFormData((prev) => ({ ...prev, accessible_kbs: toggleInArray(prev.accessible_kbs, kbId) }));
  }

  function toggleChatAuth(chatId) {
    setFormData((prev) => ({ ...prev, accessible_chats: toggleInArray(prev.accessible_chats, chatId) }));
  }

  async function moveGroupToFolder(groupId, folderId) {
    if (!groupId) return;
    setError('');
    setHint('');
    try {
      await permissionGroupsApi.update(groupId, { folder_id: folderId || null });
      const nextGroups = await fetchAll();
      const moved = nextGroups.find((g) => g.group_id === groupId);
      if (editingGroupId === groupId && moved) {
        setFormData((prev) => ({ ...prev, folder_id: moved.folder_id || null }));
      }
      setHint('权限组已移动');
    } catch (e) {
      setError(e?.message || '移动权限组失败');
    }
  }

  function onDragOverFolder(e, folderId) {
    if (!dragGroupId) return;
    e.preventDefault();
    if (e.dataTransfer) e.dataTransfer.dropEffect = 'move';
    setDropTargetFolderId(folderId);
  }

  function onDragLeaveFolder(e, folderId) {
    if (!dragGroupId) return;
    const related = e.relatedTarget;
    if (related && e.currentTarget.contains(related)) return;
    if (dropTargetFolderId === folderId) setDropTargetFolderId(null);
  }

  async function onDropFolder(e, folderId) {
    if (!dragGroupId) return;
    e.preventDefault();
    const raw = e.dataTransfer?.getData('application/x-pg-group-id');
    const droppedId = Number(raw || dragGroupId);
    setDropTargetFolderId(null);
    setDragGroupId(null);
    if (!Number.isFinite(droppedId)) return;
    await moveGroupToFolder(droppedId, folderId);
  }

  const panelStyle = {
    border: '1px solid #e5e7eb',
    borderRadius: 10,
    background: '#fff',
  };

  return (
    <div style={{ padding: 12 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 10, alignItems: 'center', marginBottom: 10 }}>
        <h2 style={{ margin: 0 }}>权限组管理</h2>
      </div>

      <section style={{ ...panelStyle, marginBottom: 12 }}>
        <div style={{ padding: '10px 12px', borderBottom: '1px solid #e5e7eb', display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
          <input
            value={searchKeyword}
            onChange={(e) => setSearchKeyword(e.target.value)}
            placeholder="筛选当前文件夹内容"
            style={{ width: 260, maxWidth: '100%', padding: '9px 10px', border: '1px solid #d1d5db', borderRadius: 8 }}
          />
          <button onClick={fetchAll} style={{ border: '1px solid #d1d5db', borderRadius: 8, background: '#fff', cursor: 'pointer', padding: '9px 12px' }}>
            刷新
          </button>
          <button onClick={createFolder} style={{ border: '1px solid #2563eb', borderRadius: 8, background: '#2563eb', color: '#fff', cursor: 'pointer', padding: '9px 12px' }}>
            新建文件夹
          </button>
          <button
            onClick={renameFolder}
            disabled={!selectedFolderId || selectedFolderId === ROOT}
            style={{
              border: '1px solid #f59e0b',
              borderRadius: 8,
              background: !selectedFolderId || selectedFolderId === ROOT ? '#fde68a' : '#f59e0b',
              color: '#fff',
              cursor: !selectedFolderId || selectedFolderId === ROOT ? 'not-allowed' : 'pointer',
              padding: '9px 12px',
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
              background: !selectedFolderId || selectedFolderId === ROOT ? '#fecaca' : '#ef4444',
              color: '#fff',
              cursor: !selectedFolderId || selectedFolderId === ROOT ? 'not-allowed' : 'pointer',
              padding: '9px 12px',
            }}
          >
            删除文件夹
          </button>
          <button onClick={startCreateGroup} style={{ border: '1px solid #10b981', borderRadius: 8, background: '#10b981', color: '#fff', cursor: 'pointer', padding: '9px 12px' }}>
            新建权限组
          </button>
          <div style={{ color: '#6b7280', fontSize: 12 }}>权限组总数: {groups.length}</div>
        </div>
      </section>

      <div style={{ display: 'grid', gridTemplateColumns: '320px 1fr', gap: 12 }}>
        <section style={panelStyle}>
          <div style={{ padding: '10px 12px', borderBottom: '1px solid #e5e7eb', fontWeight: 800 }}>文件夹</div>
          <div style={{ padding: 10, maxHeight: 700, overflowY: 'auto' }}>
            <FolderTree
              indexes={folderIndexes}
              currentFolderId={currentFolderId}
              selectedFolderId={selectedFolderId}
              expanded={expandedFolderIds}
              dropTargetFolderId={dropTargetFolderId}
              onToggleExpand={(id) => setExpandedFolderIds((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]))}
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
              {folderPath.map((f, idx) => (
                <React.Fragment key={f.id || '__root__'}>
                  <button
                    type="button"
                    onClick={() => openFolder(f.id)}
                    style={{ border: 'none', background: 'transparent', cursor: 'pointer', color: currentFolderId === f.id ? '#1d4ed8' : '#374151', fontWeight: currentFolderId === f.id ? 700 : 500, padding: 0 }}
                  >
                    {f.name}
                  </button>
                  {idx < folderPath.length - 1 && <span style={{ color: '#9ca3af' }}>{'>'}</span>}
                </React.Fragment>
              ))}
            </div>
            <div style={{ color: '#6b7280', fontSize: 12 }}>
              支持拖拽：把右侧权限组拖到左侧任意文件夹，可直接移动权限组所属文件夹。
            </div>
            {error && <div style={{ color: '#b91c1c', marginTop: 8 }}>{error}</div>}
            {hint && <div style={{ color: '#047857', marginTop: 8 }}>{hint}</div>}
          </div>

          <div style={{ maxHeight: 280, overflowY: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ background: '#f8fafc', borderBottom: '1px solid #e5e7eb' }}>
                  <th style={{ textAlign: 'left', padding: '8px 10px' }}>名称</th>
                  <th style={{ textAlign: 'left', padding: '8px 10px', width: 90 }}>类型</th>
                  <th style={{ textAlign: 'left', padding: '8px 10px', width: 120 }}>操作</th>
                </tr>
              </thead>
              <tbody>
                {filteredRows.map((row) => {
                  const selected = selectedItem?.kind === row.kind && selectedItem?.id === row.id;
                  return (
                    <tr
                      key={`${row.kind}_${row.id}`}
                      draggable={row.kind === 'group'}
                      onDragStart={(e) => {
                        if (row.kind !== 'group') return;
                        e.dataTransfer.setData('application/x-pg-group-id', String(row.id));
                        e.dataTransfer.effectAllowed = 'move';
                        setDragGroupId(row.id);
                        setDropTargetFolderId(null);
                      }}
                      onDragEnd={() => {
                        setDragGroupId(null);
                        setDropTargetFolderId(null);
                      }}
                      onClick={() => {
                        setSelectedItem({ kind: row.kind, id: row.id });
                        if (row.kind === 'folder') setSelectedFolderId(row.id);
                      }}
                      onDoubleClick={() => {
                        if (row.kind === 'folder') openFolder(row.id);
                        if (row.kind === 'group') {
                          const group = groups.find((g) => g.group_id === row.id);
                          if (group) startEditGroup(group);
                        }
                      }}
                      style={{
                        borderBottom: '1px solid #f1f5f9',
                        background: selected ? '#eff6ff' : '#fff',
                        cursor: row.kind === 'group' ? 'grab' : 'pointer',
                        opacity: dragGroupId && row.kind === 'group' && dragGroupId === row.id ? 0.5 : 1,
                      }}
                    >
                      <td style={{ padding: '8px 10px' }}>{row.kind === 'folder' ? '📁 ' : '👤 '}{row.name}</td>
                      <td style={{ padding: '8px 10px', color: '#4b5563' }}>{row.type}</td>
                      <td style={{ padding: '8px 10px' }}>
                        {row.kind === 'group' && (
                          <>
                            <button
                              type="button"
                              onClick={(e) => {
                                e.stopPropagation();
                                const group = groups.find((g) => g.group_id === row.id);
                                if (group) startEditGroup(group);
                              }}
                              style={{ border: '1px solid #3b82f6', borderRadius: 8, background: '#3b82f6', color: '#fff', cursor: 'pointer', padding: '4px 8px', marginRight: 6, fontSize: 12 }}
                            >
                              编辑
                            </button>
                            <button
                              type="button"
                              onClick={(e) => {
                                e.stopPropagation();
                                const group = groups.find((g) => g.group_id === row.id);
                                if (group) removeGroup(group);
                              }}
                              style={{ border: '1px solid #ef4444', borderRadius: 8, background: '#ef4444', color: '#fff', cursor: 'pointer', padding: '4px 8px', fontSize: 12 }}
                            >
                              删除
                            </button>
                          </>
                        )}
                      </td>
                    </tr>
                  );
                })}
                {!filteredRows.length && (
                  <tr>
                    <td colSpan={3} style={{ padding: 18, color: '#6b7280', textAlign: 'center' }}>当前文件夹为空</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          <div style={{ borderTop: '1px solid #e5e7eb', padding: 12 }}>
            {loading ? (
              <div style={{ color: '#6b7280' }}>加载中...</div>
            ) : (
              <form onSubmit={saveForm}>
                <div style={{ display: 'grid', gridTemplateColumns: '130px 1fr', gap: 10, alignItems: 'center', marginBottom: 10 }}>
                  <label>权限组名称</label>
                  <input
                    value={formData.group_name}
                    onChange={(e) => setFormData((prev) => ({ ...prev, group_name: e.target.value }))}
                    required
                    disabled={editingGroup?.is_system === 1}
                    style={{ padding: '9px 10px', border: '1px solid #d1d5db', borderRadius: 8 }}
                  />
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '130px 1fr', gap: 10, alignItems: 'start', marginBottom: 10 }}>
                  <label>描述</label>
                  <textarea
                    value={formData.description}
                    onChange={(e) => setFormData((prev) => ({ ...prev, description: e.target.value }))}
                    rows={2}
                    style={{ padding: '9px 10px', border: '1px solid #d1d5db', borderRadius: 8 }}
                  />
                </div>

                <FolderSelectionList
                  title="知识目录授权"
                  items={knowledgeNodeItems}
                  selected={formData.accessible_kb_nodes || []}
                  onToggle={toggleNodeAuth}
                  emptyText="暂无知识目录"
                />
                <FolderSelectionList
                  title="单知识库授权"
                  items={knowledgeDatasetItems}
                  selected={formData.accessible_kbs || []}
                  onToggle={toggleKbAuth}
                  emptyText="暂无知识库"
                />
                <ChatSelection chatAgents={chatAgents || []} selected={formData.accessible_chats || []} onToggle={toggleChatAuth} />

                <div style={{ marginBottom: 12 }}>
                  <div style={{ fontWeight: 700, marginBottom: 8 }}>操作权限</div>
                  <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
                    <label><input type="checkbox" checked={formData.can_upload} onChange={(e) => setFormData((prev) => ({ ...prev, can_upload: e.target.checked }))} /> 上传</label>
                    <label><input type="checkbox" checked={formData.can_review} onChange={(e) => setFormData((prev) => ({ ...prev, can_review: e.target.checked }))} /> 审核</label>
                    <label><input type="checkbox" checked={formData.can_download} onChange={(e) => setFormData((prev) => ({ ...prev, can_download: e.target.checked }))} /> 下载</label>
                    <label><input type="checkbox" checked={formData.can_delete} onChange={(e) => setFormData((prev) => ({ ...prev, can_delete: e.target.checked }))} /> 删除</label>
                  </div>
                </div>

                <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10 }}>
                  <button type="button" onClick={cancelEdit} style={{ border: '1px solid #d1d5db', borderRadius: 8, background: '#fff', cursor: 'pointer', padding: '8px 14px' }}>
                    取消
                  </button>
                  <button type="submit" disabled={saving} style={{ border: '1px solid #2563eb', borderRadius: 8, background: saving ? '#93c5fd' : '#2563eb', color: '#fff', cursor: saving ? 'not-allowed' : 'pointer', padding: '8px 14px' }}>
                    保存
                  </button>
                </div>
              </form>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}
