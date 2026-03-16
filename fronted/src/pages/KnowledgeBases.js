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
import '../features/knowledge/knowledgeBases/kbMedical.css';

function normalizeDisplayError(message, fallback) {
  const text = String(message || '').trim();
  if (!text) return fallback;
  return /[\u4e00-\u9fff]/.test(text) ? text : fallback;
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
  const [selectedItem, setSelectedItem] = useState(null);
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

  const indexes = useMemo(() => buildIndexes(directoryTree), [directoryTree]);
  const datasetsByNode = useMemo(() => buildDatasetsByNode(directoryTree), [directoryTree]);

  const datasetNodeMap = useMemo(() => {
    const map = new Map();
    (directoryTree?.datasets || []).forEach((dataset) => {
      if (dataset?.id) map.set(dataset.id, dataset.node_id || ROOT);
    });
    return map;
  }, [directoryTree]);

  const kbById = useMemo(() => {
    const map = new Map();
    kbList.forEach((item) => {
      if (item?.id) map.set(item.id, item);
    });
    return map;
  }, [kbList]);

  const breadcrumb = useMemo(
    () => [
      { id: ROOT, name: '根目录' },
      ...pathNodes(currentDirId, indexes.byId).map((node) => ({
        id: node.id,
        name: node.name || '未命名目录',
      })),
    ],
    [currentDirId, indexes.byId]
  );

  const dirOptions = useMemo(() => {
    const options = [{ id: ROOT, label: '根目录' }];
    const nodes = [...(directoryTree?.nodes || [])].sort((a, b) =>
      String(a.path || '').localeCompare(String(b.path || ''), 'zh-Hans-CN')
    );
    nodes.forEach((node) => {
      options.push({ id: node.id, label: node.path || node.name || node.id });
    });
    return options;
  }, [directoryTree]);

  const rows = useMemo(() => {
    const result = [];
    (indexes.childrenByParent.get(currentDirId) || []).forEach((node) => {
      result.push({
        kind: 'dir',
        id: node.id,
        name: node.name || '未命名目录',
        modified: fmtTime(node.updated_at_ms),
        type: '目录',
      });
    });
    (datasetsByNode.get(currentDirId) || []).forEach((dataset) => {
      result.push({
        kind: 'dataset',
        id: dataset.id,
        name: dataset.name || '未命名知识库',
        modified: '-',
        type: '知识库',
      });
    });
    return result;
  }, [currentDirId, datasetsByNode, indexes.childrenByParent]);

  const filteredRows = useMemo(() => {
    const normalizedKeyword = String(keyword || '').trim().toLowerCase();
    if (!normalizedKeyword) return rows;
    return rows.filter(
      (row) =>
        String(row.name || '').toLowerCase().includes(normalizedKeyword) ||
        String(row.id || '').toLowerCase().includes(normalizedKeyword)
    );
  }, [keyword, rows]);

  function ensureExpanded(nodeId) {
    if (!nodeId) return;
    const ids = pathNodes(nodeId, indexes.byId).map((node) => node.id);
    setExpanded((prev) => {
      const next = new Set(prev);
      ids.forEach((id) => next.add(id));
      return Array.from(next);
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
    const response = await knowledgeApi.listRagflowDatasets();
    setKbList(normalizeListResponse(response));
  }

  async function fetchTree() {
    setTreeError('');
    try {
      const response = await knowledgeApi.listKnowledgeDirectories();
      const next = response || { nodes: [], datasets: [] };
      setDirectoryTree(next);
      const validIds = new Set((next.nodes || []).map((item) => item.id));
      if (currentDirId && !validIds.has(currentDirId)) setCurrentDirId(ROOT);
      if (selectedNodeId && selectedNodeId !== ROOT && !validIds.has(selectedNodeId)) {
        setSelectedNodeId(ROOT);
      }
      setExpanded((prev) => prev.filter((id) => validIds.has(id)));
    } catch (error) {
      setTreeError(normalizeDisplayError(error?.message, '加载目录树失败'));
    }
  }

  async function loadKbDetail(datasetId) {
    if (!datasetId) return;
    setKbError('');
    try {
      const dataset = await knowledgeApi.getRagflowDataset(datasetId);
      if (!dataset?.id) throw new Error('未找到知识库');
      setKbSelected(dataset);
      setKbNameText(String(dataset.name || ''));
      const nodeId = (directoryTree?.datasets || []).find((item) => item.id === dataset.id)?.node_id || ROOT;
      setDatasetDirId(nodeId);
    } catch (error) {
      setKbSelected(null);
      setKbError(normalizeDisplayError(error?.message, '加载知识库详情失败'));
    }
  }

  async function refreshAll() {
    try {
      await Promise.all([fetchKbList(), fetchTree()]);
    } catch (error) {
      setKbError(normalizeDisplayError(error?.message, '刷新数据失败'));
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
      if (!name) throw new Error('请输入知识库名称');
      const updates = { ...pickAllowed(kbSelected, DATASET_UPDATE_ALLOWED_KEYS), name };
      const updated = await knowledgeApi.updateRagflowDataset(kbSelected.id, updates);
      if (!updated?.id) throw new Error('保存成功，但响应中缺少知识库信息');
      await knowledgeApi.assignDatasetDirectory(updated.id, datasetDirId || null);
      setKbSelected(updated);
      setKbNameText(String(updated.name || name));
      setKbSaveStatus('已保存');
      await refreshAll();
    } catch (error) {
      setKbError(normalizeDisplayError(error?.message, '保存知识库失败'));
    } finally {
      setKbBusy(false);
    }
  }

  async function deleteKb(dataset) {
    if (!isAdmin || !dataset?.id) return;
    if (!datasetEmpty(dataset)) {
      setKbError('仅可删除空知识库');
      return;
    }
    if (!window.confirm(`确认删除空知识库“${dataset.name || dataset.id}”吗？`)) return;
    setKbBusy(true);
    setKbError('');
    try {
      await knowledgeApi.deleteRagflowDataset(dataset.id);
      if (kbSelected?.id === dataset.id) setKbSelected(null);
      if (selectedItem?.kind === 'dataset' && selectedItem.id === dataset.id) setSelectedItem(null);
      await refreshAll();
    } catch (error) {
      setKbError(normalizeDisplayError(error?.message, '删除知识库失败'));
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
      const targetNode = indexes.byId.get(nextNodeId);
      setKbSaveStatus(
        `已将知识库 ${datasetId} 移动到 ${nextNodeId ? targetNode?.name || '目标目录' : '根目录'}`
      );
      await fetchTree();
      if (kbSelected?.id === datasetId) {
        setDatasetDirId(nextNodeId);
      }
    } catch (error) {
      setKbError(normalizeDisplayError(error?.message, '移动知识库失败'));
    }
  }

  function handleTreeDragOver(event, nodeId) {
    if (!dragDatasetId) return;
    event.preventDefault();
    if (event.dataTransfer) event.dataTransfer.dropEffect = 'move';
    setDropTargetNodeId(nodeId);
  }

  async function handleTreeDrop(event, nodeId) {
    if (!dragDatasetId) return;
    event.preventDefault();
    const datasetId = event.dataTransfer?.getData('application/x-kb-id') || dragDatasetId;
    setDropTargetNodeId(null);
    setDragDatasetId('');
    await moveDatasetToNode(datasetId, nodeId);
  }

  function handleTreeDragLeave(event, nodeId) {
    if (!dragDatasetId) return;
    const related = event.relatedTarget;
    if (related && event.currentTarget.contains(related)) return;
    if (dropTargetNodeId === nodeId) setDropTargetNodeId(null);
  }

  async function createDirectory() {
    if (!isAdmin) return;
    const name = window.prompt('请输入新目录名称');
    if (!name || !name.trim()) return;
    try {
      const response = await knowledgeApi.createKnowledgeDirectory({
        name: name.trim(),
        parent_id: currentDirId || null,
      });
      const newId = response?.node?.id;
      await fetchTree();
      if (newId) {
        openDir(newId);
        setSelectedItem({ kind: 'dir', id: newId });
      }
    } catch (error) {
      setTreeError(normalizeDisplayError(error?.message, '创建目录失败'));
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
    } catch (error) {
      setTreeError(normalizeDisplayError(error?.message, '重命名目录失败'));
    }
  }

  async function deleteDirectory() {
    if (!isAdmin || !selectedNodeId || selectedNodeId === ROOT) return;
    const node = indexes.byId.get(selectedNodeId);
    if (!window.confirm(`确认删除目录“${node?.name || selectedNodeId}”？\n如果目录下有子目录或知识库，删除将失败。`)) {
      return;
    }
    try {
      const parent = node?.parent_id || ROOT;
      await knowledgeApi.deleteKnowledgeDirectory(selectedNodeId);
      setSelectedNodeId(parent);
      setCurrentDirId(parent);
      setSelectedItem(null);
      await fetchTree();
    } catch (error) {
      setTreeError(normalizeDisplayError(error?.message, '删除目录失败'));
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
      const source = await knowledgeApi.getRagflowDataset(sourceId);
      if (!source?.id) throw new Error('未读取到来源知识库配置');
      setCreatePayload(pickAllowed(source, DATASET_CREATE_ALLOWED_KEYS));
      setCreateError('');
    } catch (error) {
      setCreatePayload({});
      setCreateError(normalizeDisplayError(error?.message, '加载来源配置失败'));
    }
  }

  async function createKb() {
    if (!isAdmin) return;
    setKbBusy(true);
    try {
      const name = String(createName || '').trim();
      if (!name) throw new Error('请输入知识库名称');
      const created = await knowledgeApi.createRagflowDataset({
        name,
        ...pickAllowed(createPayload, DATASET_CREATE_ALLOWED_KEYS),
      });
      if (!created?.id) throw new Error('创建成功，但响应中缺少知识库信息');
      await knowledgeApi.assignDatasetDirectory(created.id, createDirId || null);
      setCreateOpen(false);
      await refreshAll();
      await loadKbDetail(created.id);
      setSelectedItem({ kind: 'dataset', id: created.id });
    } catch (error) {
      setCreateError(normalizeDisplayError(error?.message, '创建知识库失败'));
    } finally {
      setKbBusy(false);
    }
  }

  return (
    <div className="kb-med-page">
      <div className="kb-med-tabs">
        <button
          data-testid="kbs-subtab-kbs"
          onClick={() => setSubtab('kbs')}
          type="button"
          className={subtab === 'kbs' ? 'medui-btn medui-btn--primary' : 'medui-btn medui-btn--secondary'}
        >
          知识库管理
        </button>
        <button
          data-testid="kbs-subtab-chats"
          onClick={() => setSubtab('chats')}
          type="button"
          className={subtab === 'chats' ? 'medui-btn medui-btn--primary' : 'medui-btn medui-btn--secondary'}
        >
          问答配置
        </button>
      </div>

      {subtab === 'kbs' ? (
        <div className="kb-med-layout">
          <section className="kb-med-tree">
            <div className="kb-med-pane-head">目录树</div>
            <div className="kb-med-tree-body">
              {treeError ? <div className="kb-med-error" style={{ marginBottom: 8 }}>{treeError}</div> : null}
              <DirectoryTreeView
                indexes={indexes}
                currentDirId={currentDirId}
                selectedNodeId={selectedNodeId}
                expanded={expanded}
                onToggle={(id) => setExpanded((prev) => (prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]))}
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

          <section className="kb-med-main">
            <div style={{ padding: '10px 12px', borderBottom: '1px solid #deebf8' }}>
              <div className="kb-med-actions">
                <button data-testid="kbs-refresh-all" onClick={refreshAll} type="button" className="medui-btn medui-btn--neutral">
                  刷新
                </button>
                <button
                  data-testid="kbs-go-parent"
                  onClick={() => openDir(indexes.byId.get(currentDirId)?.parent_id || ROOT)}
                  disabled={currentDirId === ROOT}
                  type="button"
                  className="medui-btn medui-btn--secondary"
                >
                  返回上级
                </button>
                {isAdmin && (
                  <>
                    <button data-testid="kbs-create-dir" onClick={createDirectory} type="button" className="medui-btn medui-btn--primary">
                      新建目录
                    </button>
                    <button
                      data-testid="kbs-rename-dir"
                      onClick={renameDirectory}
                      disabled={!selectedNodeId || selectedNodeId === ROOT}
                      type="button"
                      className="medui-btn medui-btn--warn"
                    >
                      重命名目录
                    </button>
                    <button
                      data-testid="kbs-delete-dir"
                      onClick={deleteDirectory}
                      disabled={!selectedNodeId || selectedNodeId === ROOT}
                      type="button"
                      className="medui-btn medui-btn--danger"
                    >
                      删除目录
                    </button>
                    <button data-testid="kbs-create-kb" onClick={openCreateKb} type="button" className="medui-btn medui-btn--success">
                      创建知识库
                    </button>
                  </>
                )}
              </div>

              <div className="kb-med-breadcrumb">
                <span className="medui-subtitle">路径：</span>
                {breadcrumb.map((item, index) => (
                  <React.Fragment key={item.id || '__root__'}>
                    <button type="button" onClick={() => openDir(item.id)} className={currentDirId === item.id ? 'is-current' : ''}>
                      {item.name}
                    </button>
                    {index < breadcrumb.length - 1 && <span style={{ color: '#9ca3af' }}>{'>'}</span>}
                  </React.Fragment>
                ))}
              </div>

              <input
                value={keyword}
                onChange={(event) => setKeyword(event.target.value)}
                placeholder="筛选当前目录"
                className="medui-input"
                style={{ width: 320, maxWidth: '100%' }}
              />
              <div className="kb-med-hint">支持拖拽：将右侧知识库拖到左侧目录即可调整挂载位置。</div>
              {kbError ? <div className="kb-med-error" style={{ marginTop: 8 }}>{kbError}</div> : null}
              {kbSaveStatus ? <div style={{ color: '#146c42', marginTop: 8 }}>{kbSaveStatus}</div> : null}
            </div>

            <div className="kb-med-table-wrap">
              <table className="medui-table" style={{ minWidth: '100%' }}>
                <thead>
                  <tr>
                    <th style={{ padding: '8px 10px' }}>名称</th>
                    <th style={{ padding: '8px 10px' }}>更新时间</th>
                    <th style={{ padding: '8px 10px' }}>类型</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredRows.map((row) => {
                    const selected = selectedItem?.kind === row.kind && selectedItem?.id === row.id;
                    const safeRowId = String(row.id || '').replace(/[^a-zA-Z0-9_-]/g, '_');
                    return (
                      <tr
                        key={`${row.kind}_${row.id}`}
                        data-testid={`kbs-row-${row.kind}-${safeRowId}`}
                        draggable={row.kind === 'dataset'}
                        onDragStart={(event) => {
                          if (row.kind !== 'dataset') return;
                          event.dataTransfer.setData('application/x-kb-id', row.id);
                          event.dataTransfer.setData('text/plain', row.id);
                          event.dataTransfer.effectAllowed = 'move';
                          setDragDatasetId(row.id);
                          setDropTargetNodeId(null);
                        }}
                        onDragEnd={() => {
                          setDragDatasetId('');
                          setDropTargetNodeId(null);
                        }}
                        onClick={() => {
                          setSelectedItem({ kind: row.kind, id: row.id });
                          if (row.kind === 'dir') setSelectedNodeId(row.id);
                          if (row.kind === 'dataset') loadKbDetail(row.id);
                        }}
                        onDoubleClick={() => {
                          if (row.kind === 'dir') openDir(row.id);
                          if (row.kind === 'dataset') loadKbDetail(row.id);
                        }}
                        className={selected ? 'kb-med-row-selected' : ''}
                        style={{
                          cursor: row.kind === 'dataset' ? 'grab' : 'pointer',
                          opacity: dragDatasetId && row.kind === 'dataset' && dragDatasetId === row.id ? 0.5 : 1,
                        }}
                      >
                        <td style={{ padding: '8px 10px' }}>{row.kind === 'dir' ? '[目录] ' : '[知识库] '}{row.name}</td>
                        <td style={{ padding: '8px 10px', color: '#4b5563' }}>{row.modified}</td>
                        <td style={{ padding: '8px 10px', color: '#4b5563' }}>{row.type}</td>
                      </tr>
                    );
                  })}
                  {!filteredRows.length ? (
                    <tr>
                      <td colSpan={3} style={{ padding: 18, color: '#6b7280', textAlign: 'center' }}>当前目录暂无内容</td>
                    </tr>
                  ) : null}
                </tbody>
              </table>
            </div>

            {selectedItem?.kind === 'dataset' && kbSelected?.id === selectedItem.id ? (
              <div className="kb-med-detail">
                <div style={{ fontWeight: 700, marginBottom: 8, color: '#173d60' }}>知识库详情</div>
                <div className="kb-med-detail-grid">
                  <label>名称</label>
                  <input
                    data-testid="kbs-detail-name"
                    value={kbNameText}
                    onChange={(event) => setKbNameText(event.target.value)}
                    disabled={!isAdmin}
                    className="medui-input"
                    style={{ background: isAdmin ? '#fff' : '#f7fbff' }}
                  />
                  {isAdmin ? (
                    <button data-testid="kbs-detail-save" onClick={saveKb} disabled={kbBusy} type="button" className="medui-btn medui-btn--success">
                      保存
                    </button>
                  ) : <div />}
                </div>
                <div className="kb-med-detail-grid" style={{ marginBottom: 0 }}>
                  <label>所属目录</label>
                  <select
                    value={datasetDirId}
                    onChange={(event) => setDatasetDirId(event.target.value)}
                    disabled={!isAdmin}
                    className="medui-select"
                    style={{ background: isAdmin ? '#fff' : '#f7fbff' }}
                  >
                    {dirOptions.map((option) => (
                      <option key={option.id || '__root__'} value={option.id}>{option.label}</option>
                    ))}
                  </select>
                  {isAdmin ? (
                    <button
                      data-testid="kbs-detail-delete"
                      onClick={() => deleteKb(kbById.get(kbSelected.id))}
                      disabled={kbBusy || !datasetEmpty(kbById.get(kbSelected.id))}
                      type="button"
                      className="medui-btn medui-btn--danger"
                    >
                      删除知识库
                    </button>
                  ) : <div />}
                </div>
              </div>
            ) : null}
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
