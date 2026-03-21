import React, { useEffect, useMemo, useState } from 'react';
import CreateKnowledgeBaseDialog from '../features/knowledge/knowledgeBases/components/CreateKnowledgeBaseDialog';
import DirectoryTreeView from '../features/knowledge/knowledgeBases/components/DirectoryTreeView';
import {
  DATASET_CREATE_ALLOWED_KEYS,
  DATASET_UPDATE_ALLOWED_KEYS,
  ROOT,
} from '../features/knowledge/knowledgeBases/constants';
import {
  buildDatasetsByNode,
  buildIndexes,
  datasetEmpty,
  fmtTime,
  normalizeListResponse,
  pathNodes,
  pickAllowed,
} from '../features/knowledge/knowledgeBases/utils';
import { useAuth } from '../hooks/useAuth';
import { knowledgeApi } from '../features/knowledge/api';
import { ChatConfigsPanel } from './ChatConfigsPanel';

const MOBILE_BREAKPOINT = 768;

export default function KnowledgeBases() {
  const { user, canManageKbDirectory } = useAuth();
  const isAdmin = (user?.role || '') === 'admin';
  const canManageDirectory = canManageKbDirectory();
  const [subtab, setSubtab] = useState('kbs');
  const [isMobile, setIsMobile] = useState(() => {
    if (typeof window === 'undefined') return false;
    return window.innerWidth <= MOBILE_BREAKPOINT;
  });

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
  const [createDirId, setCreateDirId] = useState(ROOT);
  const [createError, setCreateError] = useState('');

  useEffect(() => {
    if (typeof window === 'undefined') return undefined;

    const handleResize = () => setIsMobile(window.innerWidth <= MOBILE_BREAKPOINT);
    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

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
    () => [{ id: ROOT, name: '\u6839\u76ee\u5f55' }, ...pathNodes(currentDirId, indexes.byId).map((n) => ({ id: n.id, name: n.name || '(\u672a\u547d\u540d\u76ee\u5f55)' }))],
    [currentDirId, indexes.byId]
  );
  const dirOptions = useMemo(() => {
    const opts = [{ id: ROOT, label: '(\u6302\u8f7d\u5230\u6839\u76ee\u5f55)' }];
    const nodes = [...(directoryTree?.nodes || [])].sort((a, b) => String(a.path || '').localeCompare(String(b.path || ''), 'zh-Hans-CN'));
    nodes.forEach((n) => opts.push({ id: n.id, label: n.path || n.name || n.id }));
    return opts;
  }, [directoryTree]);

  const rows = useMemo(() => {
    const out = [];
    (indexes.childrenByParent.get(currentDirId) || []).forEach((n) => out.push({ kind: 'dir', id: n.id, name: n.name || '(\u672a\u547d\u540d\u76ee\u5f55)', modified: fmtTime(n.updated_at_ms), type: '\u6587\u4ef6\u5939' }));
    (datasetsByNode.get(currentDirId) || []).forEach((d) => out.push({ kind: 'dataset', id: d.id, name: d.name || '(\u672a\u547d\u540d\u77e5\u8bc6\u5e93)', modified: '-', type: '\u77e5\u8bc6\u5e93' }));
    return out;
  }, [currentDirId, indexes.childrenByParent, datasetsByNode]);

  const filteredRows = useMemo(() => {
    const kw = String(keyword || '').trim().toLowerCase();
    if (!kw) return rows;
    return rows.filter((r) => String(r.name || '').toLowerCase().includes(kw) || String(r.id || '').toLowerCase().includes(kw));
  }, [rows, keyword]);

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
      setTreeError(e?.message || '\u52a0\u8f7d\u76ee\u5f55\u6811\u5931\u8d25');
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
      setKbError(e?.message || '\u52a0\u8f7d\u77e5\u8bc6\u5e93\u8be6\u60c5\u5931\u8d25');
    }
  }

  async function refreshAll() {
    try {
      await Promise.all([fetchKbList(), fetchTree()]);
    } catch (e) {
      setKbError(e?.message || '\u5237\u65b0\u5931\u8d25');
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
      if (!name) throw new Error('\u77e5\u8bc6\u5e93\u540d\u79f0\u4e0d\u80fd\u4e3a\u7a7a');
      const updates = { ...pickAllowed(kbSelected, DATASET_UPDATE_ALLOWED_KEYS), name };
      const updated = await knowledgeApi.updateRagflowDataset(kbSelected.id, updates);
      if (!updated?.id) throw new Error('\u77e5\u8bc6\u5e93\u66f4\u65b0\u5931\u8d25');
      await knowledgeApi.assignDatasetDirectory(updated.id, datasetDirId || null);
      setKbSelected(updated);
      setKbNameText(String(updated.name || name));
      setKbSaveStatus('\u4fdd\u5b58\u6210\u529f');
      await refreshAll();
    } catch (e) {
      setKbError(e?.message || '\u4fdd\u5b58\u77e5\u8bc6\u5e93\u5931\u8d25');
    } finally {
      setKbBusy(false);
    }
  }

  async function deleteKb(ds) {
    if (!isAdmin || !ds?.id) return;
    if (!datasetEmpty(ds)) {
      setKbError('\u77e5\u8bc6\u5e93\u975e\u7a7a\uff0c\u65e0\u6cd5\u5220\u9664');
      return;
    }
    if (!window.confirm(`\u786e\u8ba4\u5220\u9664\u77e5\u8bc6\u5e93\u201c${ds.name || ds.id}\u201d\uff1f`)) return;
    setKbBusy(true);
    setKbError('');
    try {
      await knowledgeApi.deleteRagflowDataset(ds.id);
      if (kbSelected?.id === ds.id) setKbSelected(null);
      if (selectedItem?.kind === 'dataset' && selectedItem.id === ds.id) setSelectedItem(null);
      await refreshAll();
    } catch (e) {
      setKbError(e?.message || '\u5220\u9664\u77e5\u8bc6\u5e93\u5931\u8d25');
    } finally {
      setKbBusy(false);
    }
  }

  async function moveDatasetToNode(datasetId, targetNodeId) {
    if (!canManageDirectory) return;
    if (!datasetId) return;
    const fromNodeId = datasetNodeMap.get(datasetId) || ROOT;
    const nextNodeId = targetNodeId || ROOT;
    if (fromNodeId === nextNodeId) return;
    setKbError('');
    try {
      await knowledgeApi.assignDatasetDirectory(datasetId, nextNodeId || null);
      setKbSaveStatus(`\u5df2\u5c06\u77e5\u8bc6\u5e93 ${datasetId} \u79fb\u52a8\u5230${nextNodeId ? '\u76ee\u6807\u76ee\u5f55' : '\u6839\u76ee\u5f55'}`);
      await fetchTree();
      if (kbSelected?.id === datasetId) {
        setDatasetDirId(nextNodeId);
      }
    } catch (e) {
      setKbError(e?.message || '\u79fb\u52a8\u77e5\u8bc6\u5e93\u5931\u8d25');
    }
  }

  function handleTreeDragOver(e, nodeId) {
    if (!canManageDirectory) return;
    if (!dragDatasetId) return;
    e.preventDefault();
    if (e.dataTransfer) e.dataTransfer.dropEffect = 'move';
    setDropTargetNodeId(nodeId);
  }

  async function handleTreeDrop(e, nodeId) {
    if (!canManageDirectory) return;
    if (!dragDatasetId) return;
    e.preventDefault();
    const datasetId = e.dataTransfer?.getData('application/x-kb-id') || dragDatasetId;
    setDropTargetNodeId(null);
    setDragDatasetId('');
    await moveDatasetToNode(datasetId, nodeId);
  }

  function handleTreeDragLeave(e, nodeId) {
    if (!canManageDirectory) return;
    if (!dragDatasetId) return;
    const rel = e.relatedTarget;
    if (rel && e.currentTarget.contains(rel)) return;
    if (dropTargetNodeId === nodeId) setDropTargetNodeId(null);
  }

  async function createDirectory() {
    if (!canManageDirectory) return;
    const name = window.prompt('\u8bf7\u8f93\u5165\u65b0\u76ee\u5f55\u540d\u79f0');
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
      setTreeError(e?.message || '\u521b\u5efa\u76ee\u5f55\u5931\u8d25');
    }
  }

  async function renameDirectory() {
    if (!canManageDirectory || !selectedNodeId || selectedNodeId === ROOT) return;
    const node = indexes.byId.get(selectedNodeId);
    const next = window.prompt('\u8bf7\u8f93\u5165\u65b0\u7684\u76ee\u5f55\u540d\u79f0', node?.name || '');
    if (!next || !next.trim()) return;
    try {
      await knowledgeApi.updateKnowledgeDirectory(selectedNodeId, { name: next.trim() });
      await fetchTree();
    } catch (e) {
      setTreeError(e?.message || '\u91cd\u547d\u540d\u76ee\u5f55\u5931\u8d25');
    }
  }

  async function deleteDirectory() {
    if (!canManageDirectory || !selectedNodeId || selectedNodeId === ROOT) return;
    const node = indexes.byId.get(selectedNodeId);
    if (!window.confirm(`\u786e\u8ba4\u5220\u9664\u76ee\u5f55\u201c${node?.name || selectedNodeId}\u201d\uff1f\u5220\u9664\u540e\u5b50\u76ee\u5f55\u4e5f\u4f1a\u4e00\u5e76\u79fb\u9664\u3002`)) return;
    try {
      const parent = node?.parent_id || ROOT;
      await knowledgeApi.deleteKnowledgeDirectory(selectedNodeId);
      setSelectedNodeId(parent);
      setCurrentDirId(parent);
      setSelectedItem(null);
      await fetchTree();
    } catch (e) {
      setTreeError(e?.message || '\u5220\u9664\u76ee\u5f55\u5931\u8d25');
    }
  }

  function openCreateKb() {
    const preferredDirId = selectedItem?.kind === 'dir' ? selectedItem.id : currentDirId;
    setCreateOpen(true);
    setCreateName('');
    setCreateFromId(String(kbList[0]?.id || ''));
    setCreatePayload({});
    setCreateDirId(preferredDirId || ROOT);
    setCreateError('');
  }

  async function syncCreateFromCopy(sourceId) {
    if (!sourceId) return;
    try {
      const src = await knowledgeApi.getRagflowDataset(sourceId);
      if (!src?.id) throw new Error('\u8bf7\u9009\u62e9\u8981\u590d\u5236\u7684\u77e5\u8bc6\u5e93');
      setCreatePayload(pickAllowed(src, DATASET_CREATE_ALLOWED_KEYS));
      setCreateError('');
    } catch (e) {
      setCreatePayload({});
      setCreateError(e?.message || '\u521b\u5efa\u5931\u8d25');
    }
  }

  async function createKb() {
    if (!isAdmin) return;
    setKbBusy(true);
    try {
      const name = String(createName || '').trim();
      if (!name) throw new Error('\u8bf7\u8f93\u5165\u77e5\u8bc6\u5e93\u540d\u79f0');
      const created = await knowledgeApi.createRagflowDataset({ name, ...pickAllowed(createPayload, DATASET_CREATE_ALLOWED_KEYS) });
      if (!created?.id) throw new Error('\u77e5\u8bc6\u5e93\u521b\u5efa\u5931\u8d25');
      await knowledgeApi.assignDatasetDirectory(created.id, createDirId || null);
      setCreateOpen(false);
      await refreshAll();
      await loadKbDetail(created.id);
      setSelectedItem({ kind: 'dataset', id: created.id });
    } catch (e) {
      setCreateError(e?.message || '\u521b\u5efa\u5931\u8d25');
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
    <div style={{ padding: isMobile ? 10 : 14 }}>
      <div style={{ marginBottom: 10, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
        <button data-testid="kbs-subtab-kbs" onClick={() => setSubtab('kbs')} style={subtabBtn(subtab === 'kbs')}>{'\u77e5\u8bc6\u914d\u7f6e'}</button>
        <button data-testid="kbs-subtab-chats" onClick={() => setSubtab('chats')} style={subtabBtn(subtab === 'chats')}>{'\u5bf9\u8bdd\u914d\u7f6e'}</button>
      </div>

      {subtab === 'kbs' ? (
        <div style={{ display: 'grid', gridTemplateColumns: isMobile ? '1fr' : '320px 1fr', gap: 14 }}>
          <section style={{ border: '1px solid #e5e7eb', borderRadius: 12, background: '#fff' }}>
            <div style={{ padding: '10px 12px', borderBottom: '1px solid #e5e7eb', fontWeight: 800 }}>{'\u76ee\u5f55\u6811'}</div>
            <div style={{ padding: 12, maxHeight: isMobile ? 280 : 720, overflowY: 'auto' }}>
              {treeError && <div style={{ color: '#b91c1c', marginBottom: 8 }}>{treeError}</div>}
              <DirectoryTreeView
                indexes={indexes}
                currentDirId={currentDirId}
                selectedNodeId={selectedNodeId}
                expanded={expanded}
                onToggle={(id) => setExpanded((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]))}
                onOpen={(id) => {
                  openDir(id);
                  setSelectedItem(id ? { kind: 'dir', id } : null);
                }}
                dropTargetNodeId={canManageDirectory ? dropTargetNodeId : null}
                onDragOverNode={handleTreeDragOver}
                onDropNode={handleTreeDrop}
                onDragLeaveNode={handleTreeDragLeave}
                allowDatasetDrop={canManageDirectory}
              />
            </div>
          </section>

          <section style={{ border: '1px solid #e5e7eb', borderRadius: 12, background: '#fff' }}>
            <div style={{ padding: '10px 12px', borderBottom: '1px solid #e5e7eb' }}>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 10 }}>
                <button data-testid="kbs-refresh-all" onClick={refreshAll} style={{ border: '1px solid #d1d5db', borderRadius: 8, background: '#fff', cursor: 'pointer', padding: '6px 9px' }}>{'\u5237\u65b0'}</button>
                <button data-testid="kbs-go-parent" onClick={() => openDir(indexes.byId.get(currentDirId)?.parent_id || ROOT)} disabled={currentDirId === ROOT} style={{ border: '1px solid #d1d5db', borderRadius: 8, background: currentDirId === ROOT ? '#f3f4f6' : '#fff', cursor: currentDirId === ROOT ? 'not-allowed' : 'pointer', padding: '6px 9px' }}>{'\u8fd4\u56de\u4e0a\u7ea7'}</button>
                {canManageDirectory && (
                  <>
                    <button data-testid="kbs-create-dir" onClick={createDirectory} style={{ border: '1px solid #2563eb', borderRadius: 8, background: '#2563eb', color: '#fff', cursor: 'pointer', padding: '6px 9px' }}>{'\u65b0\u5efa\u76ee\u5f55'}</button>
                    <button data-testid="kbs-rename-dir" onClick={renameDirectory} disabled={!selectedNodeId || selectedNodeId === ROOT} style={{ border: '1px solid #f59e0b', borderRadius: 8, background: !selectedNodeId || selectedNodeId === ROOT ? '#fde68a' : '#f59e0b', color: '#fff', cursor: !selectedNodeId || selectedNodeId === ROOT ? 'not-allowed' : 'pointer', padding: '6px 9px' }}>{'\u91cd\u547d\u540d\u76ee\u5f55'}</button>
                    <button data-testid="kbs-delete-dir" onClick={deleteDirectory} disabled={!selectedNodeId || selectedNodeId === ROOT} style={{ border: '1px solid #ef4444', borderRadius: 8, background: !selectedNodeId || selectedNodeId === ROOT ? '#fecaca' : '#ef4444', color: '#fff', cursor: !selectedNodeId || selectedNodeId === ROOT ? 'not-allowed' : 'pointer', padding: '6px 9px' }}>{'\u5220\u9664\u76ee\u5f55'}</button>
                  </>
                )}
                {isAdmin && (
                  <button data-testid="kbs-create-kb" onClick={openCreateKb} style={{ border: '1px solid #059669', borderRadius: 8, background: '#10b981', color: '#fff', cursor: 'pointer', padding: '6px 9px' }}>{'\u65b0\u5efa\u77e5\u8bc6\u5e93'}</button>
                )}
              </div>

              <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 10 }}>
                <span style={{ color: '#6b7280', fontSize: 13 }}>{'\u8def\u5f84:'}</span>
                {breadcrumb.map((b, i) => (
                  <React.Fragment key={b.id || '__root__'}>
                    <button type="button" onClick={() => openDir(b.id)} style={{ border: 'none', background: 'transparent', cursor: 'pointer', color: currentDirId === b.id ? '#1d4ed8' : '#374151', fontWeight: currentDirId === b.id ? 700 : 500, padding: 0 }}>{b.name}</button>
                    {i < breadcrumb.length - 1 && <span style={{ color: '#9ca3af' }}>{'>'}</span>}
                  </React.Fragment>
                ))}
              </div>

              <input value={keyword} onChange={(e) => setKeyword(e.target.value)} placeholder="\u7b5b\u9009\u5f53\u524d\u76ee\u5f55\u5185\u5bb9" style={{ width: isMobile ? '100%' : 320, maxWidth: '100%', border: '1px solid #d1d5db', borderRadius: 8, padding: '8px 10px', boxSizing: 'border-box' }} />
              {canManageDirectory && (
                <div data-testid="kbs-drag-tip" style={{ marginTop: 6, color: '#6b7280', fontSize: 12 }}>
                  {'\u652f\u6301\u62d6\u62fd\uff1a\u5c06\u53f3\u4fa7\u201c\u77e5\u8bc6\u5e93\u201d\u884c\u62d6\u5230\u5de6\u4fa7\u4efb\u610f\u76ee\u5f55\uff0c\u53ef\u5feb\u901f\u79fb\u52a8\u6302\u8f7d\u4f4d\u7f6e\u3002'}
                </div>
              )}
              {kbError && <div style={{ color: '#b91c1c', marginTop: 8 }}>{kbError}</div>}
              {kbSaveStatus && <div style={{ color: '#047857', marginTop: 8 }}>{kbSaveStatus}</div>}
            </div>

            <div style={{ maxHeight: 420, overflowY: 'auto', overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr style={{ background: '#f8fafc', borderBottom: '1px solid #e5e7eb' }}>
                    <th style={{ textAlign: 'left', padding: '8px 10px' }}>{'\u540d\u79f0'}</th>
                    <th style={{ textAlign: 'left', padding: '8px 10px' }}>{'\u4fee\u6539\u65e5\u671f'}</th>
                    <th style={{ textAlign: 'left', padding: '8px 10px' }}>{'\u7c7b\u578b'}</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredRows.map((r) => {
                    const selected = selectedItem?.kind === r.kind && selectedItem?.id === r.id;
                    const safeRowId = String(r.id || '').replace(/[^a-zA-Z0-9_-]/g, '_');
                    return (
                      <tr
                        key={`${r.kind}_${r.id}`}
                        data-testid={`kbs-row-${r.kind}-${safeRowId}`}
                        draggable={canManageDirectory && r.kind === 'dataset'}
                        onDragStart={(e) => {
                          if (!canManageDirectory || r.kind !== 'dataset') return;
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
                          cursor: canManageDirectory && r.kind === 'dataset' ? 'grab' : 'pointer',
                          opacity: dragDatasetId && r.kind === 'dataset' && dragDatasetId === r.id ? 0.5 : 1,
                        }}
                      >
                        <td style={{ padding: '8px 10px' }}>{r.kind === 'dir' ? '📁 ' : '📄 '}{r.name}</td>
                        <td style={{ padding: '8px 10px', color: '#4b5563' }}>{r.modified}</td>
                        <td style={{ padding: '8px 10px', color: '#4b5563' }}>{r.type}</td>
                      </tr>
                    );
                  })}
                  {!filteredRows.length && <tr><td colSpan={3} style={{ padding: 18, color: '#6b7280', textAlign: 'center' }}>{'\u5f53\u524d\u76ee\u5f55\u4e3a\u7a7a'}</td></tr>}
                </tbody>
              </table>
            </div>

            {selectedItem?.kind === 'dataset' && kbSelected?.id === selectedItem.id && (
              <div style={{ borderTop: '1px solid #e5e7eb', padding: 12 }}>
                <div style={{ fontWeight: 700, marginBottom: 8 }}>{'\u77e5\u8bc6\u5e93\u5c5e\u6027'}</div>
                <div style={{ display: 'grid', gridTemplateColumns: isMobile ? '1fr' : '100px 1fr 130px', gap: 8, alignItems: 'center', marginBottom: 8 }}>
                  <label>{'\u540d\u79f0'}</label>
                  <input value={kbNameText} onChange={(e) => setKbNameText(e.target.value)} disabled={!isAdmin} style={{ border: '1px solid #d1d5db', borderRadius: 8, padding: '8px 10px', background: isAdmin ? '#fff' : '#f9fafb' }} />
                  {isAdmin && <button onClick={saveKb} disabled={kbBusy} style={{ border: '1px solid #059669', borderRadius: 8, background: kbBusy ? '#6ee7b7' : '#10b981', color: '#fff', cursor: kbBusy ? 'not-allowed' : 'pointer', padding: '8px 10px', width: isMobile ? '100%' : 'auto' }}>{'\u4fdd\u5b58'}</button>}
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: isMobile ? '1fr' : '100px 1fr 130px', gap: 8, alignItems: 'center' }}>
                  <label>{'\u6302\u8f7d\u76ee\u5f55'}</label>
                  <select value={datasetDirId} onChange={(e) => setDatasetDirId(e.target.value)} disabled={!isAdmin} style={{ border: '1px solid #d1d5db', borderRadius: 8, padding: '8px 10px', background: isAdmin ? '#fff' : '#f9fafb' }}>
                    {dirOptions.map((o) => <option key={o.id || '__root__'} value={o.id}>{o.label}</option>)}
                  </select>
                  {isAdmin && (
                    <button
                      onClick={() => deleteKb(kbById.get(kbSelected.id))}
                      disabled={kbBusy || !datasetEmpty(kbById.get(kbSelected.id))}
                      style={{ border: '1px solid #ef4444', borderRadius: 8, background: kbBusy || !datasetEmpty(kbById.get(kbSelected.id)) ? '#fecaca' : '#ef4444', color: '#fff', cursor: kbBusy || !datasetEmpty(kbById.get(kbSelected.id)) ? 'not-allowed' : 'pointer', padding: '8px 10px', width: isMobile ? '100%' : 'auto' }}
                    >
                      {'\u5220\u9664\u77e5\u8bc6\u5e93'}
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

      <CreateKnowledgeBaseDialog
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        createName={createName}
        onCreateNameChange={setCreateName}
        createFromId={createFromId}
        onCreateFromIdChange={(value) => {
          setCreateFromId(value);
          syncCreateFromCopy(value);
        }}
        kbList={kbList}
        createDirId={createDirId}
        onCreateDirIdChange={setCreateDirId}
        dirOptions={dirOptions}
        createError={createError}
        onCreate={createKb}
        isAdmin={isAdmin}
        kbBusy={kbBusy}
      />
    </div>
  );
}
