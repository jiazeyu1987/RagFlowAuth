import React, { useEffect, useMemo, useState } from 'react';
import { useAuth } from '../hooks/useAuth';
import { knowledgeApi } from '../features/knowledge/api';
import { ChatConfigsPanel } from './ChatConfigsPanel';

const ROOT = '';
const DATASET_CREATE_ALLOWED_KEYS = ['description', 'chunk_method', 'embedding_model', 'avatar'];
const DATASET_UPDATE_ALLOWED_KEYS = ['name', ...DATASET_CREATE_ALLOWED_KEYS, 'pagerank'];

function pickAllowed(obj, keys) {
  if (!obj || typeof obj !== 'object' || Array.isArray(obj)) return {};
  const out = {};
  keys.forEach((k) => {
    if (Object.prototype.hasOwnProperty.call(obj, k)) out[k] = obj[k];
  });
  return out;
}

function normalizeListResponse(res) {
  if (!res) return [];
  if (Array.isArray(res.datasets)) return res.datasets;
  if (res.data && Array.isArray(res.data.datasets)) return res.data.datasets;
  if (Array.isArray(res.data)) return res.data;
  return [];
}

function fmtTime(ms) {
  const v = Number(ms || 0);
  if (!v) return '-';
  const d = new Date(v);
  return Number.isNaN(d.getTime()) ? '-' : d.toLocaleString('zh-CN', { hour12: false });
}

function buildIndexes(tree) {
  const nodes = (tree?.nodes || []).filter((n) => n && n.id);
  const byId = new Map();
  const childrenByParent = new Map();
  nodes.forEach((n) => {
    byId.set(n.id, n);
    const parent = n.parent_id || ROOT;
    if (!childrenByParent.has(parent)) childrenByParent.set(parent, []);
    childrenByParent.get(parent).push(n);
  });
  for (const arr of childrenByParent.values()) {
    arr.sort((a, b) => String(a.name || '').localeCompare(String(b.name || ''), 'zh-Hans-CN'));
  }
  return { byId, childrenByParent };
}

function buildDatasetsByNode(tree) {
  const out = new Map();
  (tree?.datasets || []).forEach((d) => {
    if (!d?.id) return;
    const nodeId = d.node_id || ROOT;
    if (!out.has(nodeId)) out.set(nodeId, []);
    out.get(nodeId).push(d);
  });
  for (const arr of out.values()) {
    arr.sort((a, b) => String(a.name || '').localeCompare(String(b.name || ''), 'zh-Hans-CN'));
  }
  return out;
}

function pathNodes(nodeId, byId) {
  if (!nodeId) return [];
  const out = [];
  const guard = new Set();
  let cur = nodeId;
  while (cur && !guard.has(cur)) {
    guard.add(cur);
    const node = byId.get(cur);
    if (!node) break;
    out.push(node);
    cur = node.parent_id || ROOT;
  }
  return out.reverse();
}

function TreeView({
  indexes,
  currentDirId,
  selectedNodeId,
  expanded,
  onToggle,
  onOpen,
  dropTargetNodeId,
  onDragOverNode,
  onDropNode,
  onDragLeaveNode,
}) {
  const renderNode = (node, depth) => {
    const id = node.id;
    const children = indexes.childrenByParent.get(id) || [];
    const hasChildren = children.length > 0;
    const isExpanded = expanded.includes(id);
    return (
      <div key={id}>
        <div
          style={{
            marginLeft: depth * 16,
            borderRadius: 6,
            background:
              dropTargetNodeId === id
                ? '#dcfce7'
                : currentDirId === id
                  ? '#dbeafe'
                  : selectedNodeId === id
                    ? '#eff6ff'
                    : 'transparent',
            display: 'flex',
            alignItems: 'center',
            gap: 6,
            padding: '3px 6px',
          }}
          onDragOver={(e) => onDragOverNode(e, id)}
          onDrop={(e) => onDropNode(e, id)}
          onDragLeave={(e) => onDragLeaveNode(e, id)}
        >
          <button
            type="button"
            onClick={() => hasChildren && onToggle(id)}
            style={{ width: 14, border: 'none', background: 'transparent', cursor: hasChildren ? 'pointer' : 'default', color: '#6b7280', padding: 0 }}
          >
            {hasChildren ? (isExpanded ? '▾' : '▸') : ''}
          </button>
          <button
            type="button"
            onClick={() => onOpen(id)}
            style={{ border: 'none', background: 'transparent', padding: 0, textAlign: 'left', cursor: 'pointer', width: '100%' }}
            title={node.path || node.name}
          >
            📁 {node.name || '(未命名目录)'}
          </button>
        </div>
        {isExpanded && children.map((c) => renderNode(c, depth + 1))}
      </div>
    );
  };

  const roots = indexes.childrenByParent.get(ROOT) || [];
  return (
    <div>
      <div
        style={{
          borderRadius: 6,
          background: dropTargetNodeId === ROOT ? '#dcfce7' : currentDirId === ROOT ? '#dbeafe' : 'transparent',
          padding: '3px 6px',
          marginBottom: 6,
        }}
        onDragOver={(e) => onDragOverNode(e, ROOT)}
        onDrop={(e) => onDropNode(e, ROOT)}
        onDragLeave={(e) => onDragLeaveNode(e, ROOT)}
      >
        <button type="button" onClick={() => onOpen(ROOT)} style={{ border: 'none', background: 'transparent', padding: 0, cursor: 'pointer', width: '100%', textAlign: 'left' }}>
          🖥️ 根目录
        </button>
      </div>
      {roots.map((n) => renderNode(n, 0))}
      {!roots.length && <div style={{ color: '#6b7280', fontSize: 13 }}>暂无目录</div>}
    </div>
  );
}

export default function KnowledgeBases() {
  const { user } = useAuth();
  const isAdmin = (user?.role || '') === 'admin';
  const [subtab, setSubtab] = useState('kbs');

  const [kbList, setKbList] = useState([]);
  const [directoryTree, setDirectoryTree] = useState({ nodes: [], datasets: [] });
  const [kbError, setKbError] = useState('');
  const [treeError, setTreeError] = useState('');
  const [kbBusy, setKbBusy] = useState(false);
  const [kbSaveStatus, setKbSaveStatus] = useState('');

  const [currentDirId, setCurrentDirId] = useState(ROOT);
  const [selectedNodeId, setSelectedNodeId] = useState(ROOT);
  const [expanded, setExpanded] = useState([]);
  const [keyword, setKeyword] = useState('');
  const [selectedItem, setSelectedItem] = useState(null); // {kind, id}
  const [dragDatasetId, setDragDatasetId] = useState('');
  const [dropTargetNodeId, setDropTargetNodeId] = useState(null);

  const [kbSelected, setKbSelected] = useState(null);
  const [kbNameText, setKbNameText] = useState('');
  const [datasetDirId, setDatasetDirId] = useState(ROOT);

  const [createOpen, setCreateOpen] = useState(false);
  const [createName, setCreateName] = useState('');
  const [createFromId, setCreateFromId] = useState('');
  const [createPayload, setCreatePayload] = useState({});
  const [createError, setCreateError] = useState('');

  const indexes = useMemo(() => buildIndexes(directoryTree), [directoryTree]);
  const datasetsByNode = useMemo(() => buildDatasetsByNode(directoryTree), [directoryTree]);
  const datasetNodeMap = useMemo(() => {
    const map = new Map();
    (directoryTree?.datasets || []).forEach((d) => {
      if (d?.id) map.set(d.id, d.node_id || ROOT);
    });
    return map;
  }, [directoryTree]);
  const kbById = useMemo(() => {
    const m = new Map();
    kbList.forEach((x) => x?.id && m.set(x.id, x));
    return m;
  }, [kbList]);
  const breadcrumb = useMemo(
    () => [{ id: ROOT, name: '根目录' }, ...pathNodes(currentDirId, indexes.byId).map((n) => ({ id: n.id, name: n.name || '(未命名目录)' }))],
    [currentDirId, indexes.byId]
  );
  const dirOptions = useMemo(() => {
    const opts = [{ id: ROOT, label: '(挂载到根目录)' }];
    const nodes = [...(directoryTree?.nodes || [])].sort((a, b) => String(a.path || '').localeCompare(String(b.path || ''), 'zh-Hans-CN'));
    nodes.forEach((n) => opts.push({ id: n.id, label: n.path || n.name || n.id }));
    return opts;
  }, [directoryTree]);

  const rows = useMemo(() => {
    const out = [];
    (indexes.childrenByParent.get(currentDirId) || []).forEach((n) => out.push({ kind: 'dir', id: n.id, name: n.name || '(未命名目录)', modified: fmtTime(n.updated_at_ms), type: '文件夹' }));
    (datasetsByNode.get(currentDirId) || []).forEach((d) => out.push({ kind: 'dataset', id: d.id, name: d.name || '(未命名知识库)', modified: '-', type: '知识库' }));
    return out;
  }, [currentDirId, indexes.childrenByParent, datasetsByNode]);

  const filteredRows = useMemo(() => {
    const kw = String(keyword || '').trim().toLowerCase();
    if (!kw) return rows;
    return rows.filter((r) => String(r.name || '').toLowerCase().includes(kw) || String(r.id || '').toLowerCase().includes(kw));
  }, [rows, keyword]);

  function datasetEmpty(ds) {
    return Number(ds?.document_count || 0) <= 0 && Number(ds?.chunk_count || 0) <= 0;
  }

  function ensureExpanded(nodeId) {
    if (!nodeId) return;
    const ids = pathNodes(nodeId, indexes.byId).map((n) => n.id);
    setExpanded((prev) => {
      const s = new Set(prev);
      ids.forEach((id) => s.add(id));
      return Array.from(s);
    });
  }

  function openDir(id) {
    const next = id || ROOT;
    setCurrentDirId(next);
    setSelectedNodeId(next);
    if (next) ensureExpanded(next);
  }

  async function fetchKbList() {
    setKbError('');
    const res = await knowledgeApi.listRagflowDatasets();
    setKbList(normalizeListResponse(res));
  }

  async function fetchTree() {
    setTreeError('');
    try {
      const res = await knowledgeApi.listKnowledgeDirectories();
      const next = res || { nodes: [], datasets: [] };
      setDirectoryTree(next);
      const validIds = new Set((next.nodes || []).map((x) => x.id));
      if (currentDirId && !validIds.has(currentDirId)) setCurrentDirId(ROOT);
      if (selectedNodeId && selectedNodeId !== ROOT && !validIds.has(selectedNodeId)) setSelectedNodeId(ROOT);
      setExpanded((prev) => prev.filter((id) => validIds.has(id)));
    } catch (e) {
      setTreeError(e?.message || '加载目录失败');
    }
  }

  async function loadKbDetail(datasetId) {
    if (!datasetId) return;
    setKbError('');
    try {
      const ds = await knowledgeApi.getRagflowDataset(datasetId);
      if (!ds?.id) throw new Error('dataset_not_found');
      setKbSelected(ds);
      setKbNameText(String(ds.name || ''));
      const nodeId = ((directoryTree?.datasets || []).find((x) => x.id === ds.id)?.node_id) || ROOT;
      setDatasetDirId(nodeId);
    } catch (e) {
      setKbSelected(null);
      setKbError(e?.message || '加载知识库详情失败');
    }
  }

  async function refreshAll() {
    try {
      await Promise.all([fetchKbList(), fetchTree()]);
    } catch (e) {
      setKbError(e?.message || '刷新失败');
    }
  }

  useEffect(() => {
    refreshAll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function saveKb() {
    if (!isAdmin || !kbSelected?.id) return;
    setKbBusy(true);
    setKbError('');
    setKbSaveStatus('');
    try {
      const name = String(kbNameText || '').trim();
      if (!name) throw new Error('知识库名称不能为空');
      const updates = { ...pickAllowed(kbSelected, DATASET_UPDATE_ALLOWED_KEYS), name };
      const updated = await knowledgeApi.updateRagflowDataset(kbSelected.id, updates);
      if (!updated?.id) throw new Error('保存成功但未返回知识库信息');
      await knowledgeApi.assignDatasetDirectory(updated.id, datasetDirId || null);
      setKbSelected(updated);
      setKbNameText(String(updated.name || name));
      setKbSaveStatus('已保存');
      await refreshAll();
    } catch (e) {
      setKbError(e?.message || '保存失败');
    } finally {
      setKbBusy(false);
    }
  }

  async function deleteKb(ds) {
    if (!isAdmin || !ds?.id) return;
    if (!datasetEmpty(ds)) {
      setKbError('仅允许删除空知识库');
      return;
    }
    if (!window.confirm(`确认删除空知识库「${ds.name || ds.id}」吗？`)) return;
    setKbBusy(true);
    setKbError('');
    try {
      await knowledgeApi.deleteRagflowDataset(ds.id);
      if (kbSelected?.id === ds.id) setKbSelected(null);
      if (selectedItem?.kind === 'dataset' && selectedItem.id === ds.id) setSelectedItem(null);
      await refreshAll();
    } catch (e) {
      setKbError(e?.message || '删除失败');
    } finally {
      setKbBusy(false);
    }
  }

  async function moveDatasetToNode(datasetId, targetNodeId) {
    if (!datasetId) return;
    const fromNodeId = datasetNodeMap.get(datasetId) || ROOT;
    const nextNodeId = targetNodeId || ROOT;
    if (fromNodeId === nextNodeId) return;
    setKbError('');
    try {
      await knowledgeApi.assignDatasetDirectory(datasetId, nextNodeId || null);
      setKbSaveStatus(`已移动知识库 ${datasetId} 到 ${nextNodeId ? '目标目录' : '根目录'}`);
      await fetchTree();
      if (kbSelected?.id === datasetId) {
        setDatasetDirId(nextNodeId);
      }
    } catch (e) {
      setKbError(e?.message || '拖拽移动失败');
    }
  }

  function handleTreeDragOver(e, nodeId) {
    if (!dragDatasetId) return;
    e.preventDefault();
    if (e.dataTransfer) e.dataTransfer.dropEffect = 'move';
    setDropTargetNodeId(nodeId);
  }

  async function handleTreeDrop(e, nodeId) {
    if (!dragDatasetId) return;
    e.preventDefault();
    const datasetId = e.dataTransfer?.getData('application/x-kb-id') || dragDatasetId;
    setDropTargetNodeId(null);
    setDragDatasetId('');
    await moveDatasetToNode(datasetId, nodeId);
  }

  function handleTreeDragLeave(e, nodeId) {
    if (!dragDatasetId) return;
    const rel = e.relatedTarget;
    if (rel && e.currentTarget.contains(rel)) return;
    if (dropTargetNodeId === nodeId) setDropTargetNodeId(null);
  }

  async function createDirectory() {
    if (!isAdmin) return;
    const name = window.prompt('请输入新目录名称');
    if (!name || !name.trim()) return;
    try {
      const res = await knowledgeApi.createKnowledgeDirectory({ name: name.trim(), parent_id: currentDirId || null });
      const newId = res?.node?.id;
      await fetchTree();
      if (newId) {
        openDir(newId);
        setSelectedItem({ kind: 'dir', id: newId });
      }
    } catch (e) {
      setTreeError(e?.message || '创建目录失败');
    }
  }

  async function renameDirectory() {
    if (!isAdmin || !selectedNodeId || selectedNodeId === ROOT) return;
    const node = indexes.byId.get(selectedNodeId);
    const next = window.prompt('请输入新目录名称', node?.name || '');
    if (!next || !next.trim()) return;
    try {
      await knowledgeApi.updateKnowledgeDirectory(selectedNodeId, { name: next.trim() });
      await fetchTree();
    } catch (e) {
      setTreeError(e?.message || '重命名目录失败');
    }
  }

  async function deleteDirectory() {
    if (!isAdmin || !selectedNodeId || selectedNodeId === ROOT) return;
    const node = indexes.byId.get(selectedNodeId);
    if (!window.confirm(`确认删除目录「${node?.name || selectedNodeId}」吗？\n目录下有子目录或知识库时会失败。`)) return;
    try {
      const parent = node?.parent_id || ROOT;
      await knowledgeApi.deleteKnowledgeDirectory(selectedNodeId);
      setSelectedNodeId(parent);
      setCurrentDirId(parent);
      setSelectedItem(null);
      await fetchTree();
    } catch (e) {
      setTreeError(e?.message || '删除目录失败');
    }
  }

  function openCreateKb() {
    setCreateOpen(true);
    setCreateName('');
    setCreateFromId(String(kbList[0]?.id || ''));
    setCreatePayload({});
    setCreateError('');
  }

  async function syncCreateFromCopy(sourceId) {
    if (!sourceId) return;
    try {
      const src = await knowledgeApi.getRagflowDataset(sourceId);
      if (!src?.id) throw new Error('未读取到源知识库配置');
      setCreatePayload(pickAllowed(src, DATASET_CREATE_ALLOWED_KEYS));
      setCreateError('');
    } catch (e) {
      setCreatePayload({});
      setCreateError(e?.message || '读取源配置失败');
    }
  }

  async function createKb() {
    if (!isAdmin) return;
    setKbBusy(true);
    try {
      const name = String(createName || '').trim();
      if (!name) throw new Error('请输入知识库名称');
      const created = await knowledgeApi.createRagflowDataset({ name, ...pickAllowed(createPayload, DATASET_CREATE_ALLOWED_KEYS) });
      if (!created?.id) throw new Error('创建成功但未返回知识库信息');
      await knowledgeApi.assignDatasetDirectory(created.id, currentDirId || null);
      setCreateOpen(false);
      await refreshAll();
      await loadKbDetail(created.id);
      setSelectedItem({ kind: 'dataset', id: created.id });
    } catch (e) {
      setCreateError(e?.message || '创建失败');
    } finally {
      setKbBusy(false);
    }
  }

  const subtabBtn = (active) => ({
    border: '1px solid ' + (active ? '#1d4ed8' : '#e5e7eb'),
    borderRadius: 10,
    background: active ? '#1d4ed8' : '#fff',
    color: active ? '#fff' : '#111827',
    cursor: 'pointer',
    padding: '9px 12px',
    fontWeight: 700,
  });

  return (
    <div style={{ padding: 14 }}>
      <div style={{ marginBottom: 10, display: 'flex', gap: 8 }}>
        <button onClick={() => setSubtab('kbs')} style={subtabBtn(subtab === 'kbs')}>知识配置</button>
        <button onClick={() => setSubtab('chats')} style={subtabBtn(subtab === 'chats')}>对话配置</button>
      </div>

      {subtab === 'kbs' ? (
        <div style={{ display: 'grid', gridTemplateColumns: '320px 1fr', gap: 14 }}>
          <section style={{ border: '1px solid #e5e7eb', borderRadius: 12, background: '#fff' }}>
            <div style={{ padding: '10px 12px', borderBottom: '1px solid #e5e7eb', fontWeight: 800 }}>目录树</div>
            <div style={{ padding: 12, maxHeight: 720, overflowY: 'auto' }}>
              {treeError && <div style={{ color: '#b91c1c', marginBottom: 8 }}>{treeError}</div>}
              <TreeView
                indexes={indexes}
                currentDirId={currentDirId}
                selectedNodeId={selectedNodeId}
                expanded={expanded}
                onToggle={(id) => setExpanded((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]))}
                onOpen={(id) => {
                  openDir(id);
                  setSelectedItem(id ? { kind: 'dir', id } : null);
                }}
                dropTargetNodeId={dropTargetNodeId}
                onDragOverNode={handleTreeDragOver}
                onDropNode={handleTreeDrop}
                onDragLeaveNode={handleTreeDragLeave}
              />
            </div>
          </section>

          <section style={{ border: '1px solid #e5e7eb', borderRadius: 12, background: '#fff' }}>
            <div style={{ padding: '10px 12px', borderBottom: '1px solid #e5e7eb' }}>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 10 }}>
                <button onClick={refreshAll} style={{ border: '1px solid #d1d5db', borderRadius: 8, background: '#fff', cursor: 'pointer', padding: '6px 9px' }}>刷新</button>
                <button onClick={() => openDir(indexes.byId.get(currentDirId)?.parent_id || ROOT)} disabled={currentDirId === ROOT} style={{ border: '1px solid #d1d5db', borderRadius: 8, background: currentDirId === ROOT ? '#f3f4f6' : '#fff', cursor: currentDirId === ROOT ? 'not-allowed' : 'pointer', padding: '6px 9px' }}>返回上级</button>
                {isAdmin && (
                  <>
                    <button onClick={createDirectory} style={{ border: '1px solid #2563eb', borderRadius: 8, background: '#2563eb', color: '#fff', cursor: 'pointer', padding: '6px 9px' }}>新建目录</button>
                    <button onClick={renameDirectory} disabled={!selectedNodeId || selectedNodeId === ROOT} style={{ border: '1px solid #f59e0b', borderRadius: 8, background: !selectedNodeId || selectedNodeId === ROOT ? '#fde68a' : '#f59e0b', color: '#fff', cursor: !selectedNodeId || selectedNodeId === ROOT ? 'not-allowed' : 'pointer', padding: '6px 9px' }}>重命名目录</button>
                    <button onClick={deleteDirectory} disabled={!selectedNodeId || selectedNodeId === ROOT} style={{ border: '1px solid #ef4444', borderRadius: 8, background: !selectedNodeId || selectedNodeId === ROOT ? '#fecaca' : '#ef4444', color: '#fff', cursor: !selectedNodeId || selectedNodeId === ROOT ? 'not-allowed' : 'pointer', padding: '6px 9px' }}>删除目录</button>
                    <button onClick={openCreateKb} style={{ border: '1px solid #059669', borderRadius: 8, background: '#10b981', color: '#fff', cursor: 'pointer', padding: '6px 9px' }}>新建知识库</button>
                  </>
                )}
              </div>

              <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 10 }}>
                <span style={{ color: '#6b7280', fontSize: 13 }}>路径:</span>
                {breadcrumb.map((b, i) => (
                  <React.Fragment key={b.id || '__root__'}>
                    <button type="button" onClick={() => openDir(b.id)} style={{ border: 'none', background: 'transparent', cursor: 'pointer', color: currentDirId === b.id ? '#1d4ed8' : '#374151', fontWeight: currentDirId === b.id ? 700 : 500, padding: 0 }}>{b.name}</button>
                    {i < breadcrumb.length - 1 && <span style={{ color: '#9ca3af' }}>{'>'}</span>}
                  </React.Fragment>
                ))}
              </div>

              <input value={keyword} onChange={(e) => setKeyword(e.target.value)} placeholder="筛选当前目录内容" style={{ width: 320, maxWidth: '100%', border: '1px solid #d1d5db', borderRadius: 8, padding: '8px 10px' }} />
              <div style={{ marginTop: 6, color: '#6b7280', fontSize: 12 }}>
                支持拖拽：将右侧“知识库”行拖到左侧任意目录，可快速移动挂载位置。
              </div>
              {kbError && <div style={{ color: '#b91c1c', marginTop: 8 }}>{kbError}</div>}
              {kbSaveStatus && <div style={{ color: '#047857', marginTop: 8 }}>{kbSaveStatus}</div>}
            </div>

            <div style={{ maxHeight: 420, overflowY: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr style={{ background: '#f8fafc', borderBottom: '1px solid #e5e7eb' }}>
                    <th style={{ textAlign: 'left', padding: '8px 10px' }}>名称</th>
                    <th style={{ textAlign: 'left', padding: '8px 10px' }}>修改日期</th>
                    <th style={{ textAlign: 'left', padding: '8px 10px' }}>类型</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredRows.map((r) => {
                    const selected = selectedItem?.kind === r.kind && selectedItem?.id === r.id;
                    return (
                      <tr
                        key={`${r.kind}_${r.id}`}
                        draggable={r.kind === 'dataset'}
                        onDragStart={(e) => {
                          if (r.kind !== 'dataset') return;
                          e.dataTransfer.setData('application/x-kb-id', r.id);
                          e.dataTransfer.setData('text/plain', r.id);
                          e.dataTransfer.effectAllowed = 'move';
                          setDragDatasetId(r.id);
                          setDropTargetNodeId(null);
                        }}
                        onDragEnd={() => {
                          setDragDatasetId('');
                          setDropTargetNodeId(null);
                        }}
                        onClick={() => {
                          setSelectedItem({ kind: r.kind, id: r.id });
                          if (r.kind === 'dir') setSelectedNodeId(r.id);
                          if (r.kind === 'dataset') loadKbDetail(r.id);
                        }}
                        onDoubleClick={() => {
                          if (r.kind === 'dir') openDir(r.id);
                          if (r.kind === 'dataset') loadKbDetail(r.id);
                        }}
                        style={{
                          borderBottom: '1px solid #f1f5f9',
                          background: selected ? '#eff6ff' : '#fff',
                          cursor: r.kind === 'dataset' ? 'grab' : 'pointer',
                          opacity: dragDatasetId && r.kind === 'dataset' && dragDatasetId === r.id ? 0.5 : 1,
                        }}
                      >
                        <td style={{ padding: '8px 10px' }}>{r.kind === 'dir' ? '📁 ' : '📄 '}{r.name}</td>
                        <td style={{ padding: '8px 10px', color: '#4b5563' }}>{r.modified}</td>
                        <td style={{ padding: '8px 10px', color: '#4b5563' }}>{r.type}</td>
                      </tr>
                    );
                  })}
                  {!filteredRows.length && <tr><td colSpan={3} style={{ padding: 18, color: '#6b7280', textAlign: 'center' }}>当前目录为空</td></tr>}
                </tbody>
              </table>
            </div>

            {selectedItem?.kind === 'dataset' && kbSelected?.id === selectedItem.id && (
              <div style={{ borderTop: '1px solid #e5e7eb', padding: 12 }}>
                <div style={{ fontWeight: 700, marginBottom: 8 }}>知识库属性</div>
                <div style={{ display: 'grid', gridTemplateColumns: '100px 1fr 130px', gap: 8, alignItems: 'center', marginBottom: 8 }}>
                  <label>名称</label>
                  <input value={kbNameText} onChange={(e) => setKbNameText(e.target.value)} disabled={!isAdmin} style={{ border: '1px solid #d1d5db', borderRadius: 8, padding: '8px 10px', background: isAdmin ? '#fff' : '#f9fafb' }} />
                  {isAdmin && <button onClick={saveKb} disabled={kbBusy} style={{ border: '1px solid #059669', borderRadius: 8, background: kbBusy ? '#6ee7b7' : '#10b981', color: '#fff', cursor: kbBusy ? 'not-allowed' : 'pointer', padding: '8px 10px' }}>保存</button>}
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '100px 1fr 130px', gap: 8, alignItems: 'center' }}>
                  <label>挂载目录</label>
                  <select value={datasetDirId} onChange={(e) => setDatasetDirId(e.target.value)} disabled={!isAdmin} style={{ border: '1px solid #d1d5db', borderRadius: 8, padding: '8px 10px', background: isAdmin ? '#fff' : '#f9fafb' }}>
                    {dirOptions.map((o) => <option key={o.id || '__root__'} value={o.id}>{o.label}</option>)}
                  </select>
                  {isAdmin && (
                    <button
                      onClick={() => deleteKb(kbById.get(kbSelected.id))}
                      disabled={kbBusy || !datasetEmpty(kbById.get(kbSelected.id))}
                      style={{ border: '1px solid #ef4444', borderRadius: 8, background: kbBusy || !datasetEmpty(kbById.get(kbSelected.id)) ? '#fecaca' : '#ef4444', color: '#fff', cursor: kbBusy || !datasetEmpty(kbById.get(kbSelected.id)) ? 'not-allowed' : 'pointer', padding: '8px 10px' }}
                    >
                      删除知识库
                    </button>
                  )}
                </div>
              </div>
            )}
          </section>
        </div>
      ) : (
        <ChatConfigsPanel />
      )}

      {createOpen && (
        <div
          role="dialog"
          aria-modal="true"
          onMouseDown={(e) => e.target === e.currentTarget && setCreateOpen(false)}
          style={{ position: 'fixed', inset: 0, background: 'rgba(17,24,39,0.45)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}
        >
          <div style={{ width: 'min(680px, 95vw)', background: '#fff', borderRadius: 12, border: '1px solid #e5e7eb', overflow: 'hidden' }}>
            <div style={{ padding: '12px 14px', borderBottom: '1px solid #e5e7eb', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div style={{ fontWeight: 800 }}>新建知识库</div>
              <button onClick={() => setCreateOpen(false)} style={{ border: '1px solid #d1d5db', borderRadius: 8, background: '#fff', cursor: 'pointer', padding: '6px 10px' }}>关闭</button>
            </div>
            <div style={{ padding: 14 }}>
              <div style={{ display: 'grid', gridTemplateColumns: '110px 1fr', alignItems: 'center', gap: 10, marginBottom: 10 }}>
                <label>名称</label>
                <input value={createName} onChange={(e) => setCreateName(e.target.value)} style={{ padding: '9px 10px', border: '1px solid #d1d5db', borderRadius: 8 }} />
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '110px 1fr', alignItems: 'center', gap: 10 }}>
                <label>复制配置</label>
                <select
                  value={createFromId}
                  onChange={(e) => {
                    const v = e.target.value;
                    setCreateFromId(v);
                    syncCreateFromCopy(v);
                  }}
                  style={{ padding: '9px 10px', border: '1px solid #d1d5db', borderRadius: 8 }}
                  disabled={!kbList.length}
                >
                  {kbList.map((ds) => <option key={String(ds?.id || '')} value={String(ds?.id || '')}>{String(ds?.name || ds?.id || '')}</option>)}
                </select>
              </div>
              {createError && <div style={{ color: '#b91c1c', marginTop: 10 }}>{createError}</div>}
            </div>
            <div style={{ padding: '12px 14px', borderTop: '1px solid #e5e7eb', display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
              <button onClick={() => setCreateOpen(false)} style={{ border: '1px solid #d1d5db', borderRadius: 8, background: '#fff', cursor: 'pointer', padding: '8px 12px' }}>取消</button>
              <button onClick={createKb} disabled={!isAdmin || kbBusy} style={{ border: '1px solid #2563eb', borderRadius: 8, background: kbBusy ? '#93c5fd' : '#2563eb', color: '#fff', cursor: kbBusy ? 'not-allowed' : 'pointer', padding: '8px 12px' }}>创建</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
