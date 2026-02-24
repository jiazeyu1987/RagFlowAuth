import React, { useEffect, useMemo, useState } from 'react';
import { useAuth } from '../hooks/useAuth';
import { knowledgeApi } from '../features/knowledge/api';
import { ChatConfigsPanel } from './ChatConfigsPanel';

const DATASET_CREATE_ALLOWED_KEYS = ['description', 'chunk_method', 'embedding_model', 'avatar'];
const DATASET_UPDATE_ALLOWED_KEYS = ['name', ...DATASET_CREATE_ALLOWED_KEYS, 'pagerank'];

function pickAllowed(obj, allowedKeys) {
  if (!obj || typeof obj !== 'object' || Array.isArray(obj)) return {};
  const out = {};
  for (const key of allowedKeys) {
    if (Object.prototype.hasOwnProperty.call(obj, key)) out[key] = obj[key];
  }
  return out;
}

function normalizeListResponse(res) {
  if (!res) return [];
  if (Array.isArray(res.datasets)) return res.datasets;
  if (res.data && Array.isArray(res.data.datasets)) return res.data.datasets;
  if (Array.isArray(res.data)) return res.data;
  return [];
}

function datasetIsEmpty(ds) {
  const docCount = ds?.document_count;
  const chunkCount = ds?.chunk_count;
  const hasDocCount = typeof docCount === 'number' && Number.isFinite(docCount);
  const hasChunkCount = typeof chunkCount === 'number' && Number.isFinite(chunkCount);
  if (!hasDocCount && !hasChunkCount) return { known: false, empty: false };
  const nonEmpty = (hasDocCount && docCount > 0) || (hasChunkCount && chunkCount > 0);
  return { known: true, empty: !nonEmpty };
}

export default function KnowledgeBases() {
  const { user } = useAuth();
  const isAdmin = (user?.role || '') === 'admin';

  const [subtab, setSubtab] = useState('kbs'); // kbs | chats
  const [kbList, setKbList] = useState([]);
  const [kbLoading, setKbLoading] = useState(false);
  const [kbError, setKbError] = useState('');
  const [kbFilter, setKbFilter] = useState('');
  const [kbSelected, setKbSelected] = useState(null);
  const [kbDetailLoading, setKbDetailLoading] = useState(false);
  const [kbDetailError, setKbDetailError] = useState('');
  const [kbNameText, setKbNameText] = useState('');
  const [kbSaveStatus, setKbSaveStatus] = useState('');
  const [kbBusy, setKbBusy] = useState(false);

  const [createOpen, setCreateOpen] = useState(false);
  const [createName, setCreateName] = useState('');
  const [createFromId, setCreateFromId] = useState('');
  const [createPayload, setCreatePayload] = useState({});
  const [createError, setCreateError] = useState('');

  const filteredKbList = useMemo(() => {
    const kw = String(kbFilter || '').trim().toLowerCase();
    if (!kw) return kbList;
    return kbList.filter((ds) => {
      const id = String(ds?.id || '').toLowerCase();
      const name = String(ds?.name || '').toLowerCase();
      const desc = String(ds?.description || '').toLowerCase();
      return id.includes(kw) || name.includes(kw) || desc.includes(kw);
    });
  }, [kbFilter, kbList]);

  async function fetchKbList() {
    setKbError('');
    setKbLoading(true);
    try {
      const res = await knowledgeApi.listRagflowDatasets();
      setKbList(normalizeListResponse(res));
    } catch (e) {
      setKbList([]);
      setKbError(e?.message || '加载知识库失败');
    } finally {
      setKbLoading(false);
    }
  }

  async function loadKbDetail(datasetRef) {
    if (!datasetRef) return;
    setKbDetailError('');
    setKbSaveStatus('');
    setKbDetailLoading(true);
    try {
      const ds = await knowledgeApi.getRagflowDataset(datasetRef);
      if (!ds || !ds.id) throw new Error('dataset_not_found');
      setKbSelected(ds);
      setKbNameText(String(ds?.name || ''));
    } catch (e) {
      setKbSelected(null);
      setKbDetailError(e?.message || '加载失败');
    } finally {
      setKbDetailLoading(false);
    }
  }

  useEffect(() => {
    fetchKbList();
  }, []);

  useEffect(() => {
    if (!kbSelected && kbList.length) loadKbDetail(kbList[0]?.id || '');
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [kbList]);

  async function saveKb() {
    if (!kbSelected?.id) return;
    setKbDetailError('');
    setKbSaveStatus('');

    const name = String(kbNameText || '').trim();
    if (!name) {
      setKbDetailError('名称不能为空');
      return;
    }

    setKbBusy(true);
    try {
      const updates = { ...pickAllowed(kbSelected, DATASET_UPDATE_ALLOWED_KEYS), name };
      const updated = await knowledgeApi.updateRagflowDataset(kbSelected.id, updates);
      if (!updated || !updated.id) throw new Error('保存成功但未返回知识库信息');
      setKbSelected(updated);
      setKbNameText(String(updated?.name || name));
      setKbSaveStatus('已保存');
      await fetchKbList();
    } catch (e) {
      setKbDetailError(e?.message || '保存失败');
    } finally {
      setKbBusy(false);
    }
  }

  async function deleteKb(ds) {
    if (!ds?.id) return;
    const state = datasetIsEmpty(ds);
    if (!state.known) {
      setKbError('无法判断是否为空，已禁用删除（请先进入详情确认）');
      return;
    }
    if (!state.empty) {
      setKbError('该知识库不是空的，禁止删除（请先清空文档/Chunk）');
      return;
    }

    const ok = window.confirm('确认删除空知识库：' + (ds.name || ds.id) + '\n\n仅允许删除空知识库。');
    if (!ok) return;

    setKbBusy(true);
    try {
      await knowledgeApi.deleteRagflowDataset(ds.id);
      if (kbSelected?.id === ds.id) setKbSelected(null);
      await fetchKbList();
    } catch (e) {
      setKbError(e?.message || '删除失败');
    } finally {
      setKbBusy(false);
    }
  }

  function openCreate() {
    setCreateName('');
    const firstId = String(kbList[0]?.id || '');
    setCreateFromId(firstId);
    setCreatePayload({});
    setCreateError('');
    if (firstId) syncCreateFromCopy(firstId);
    setCreateOpen(true);
  }

  async function syncCreateFromCopy(sourceId) {
    if (!sourceId) return;
    setCreateError('');
    try {
      const src = await knowledgeApi.getRagflowDataset(sourceId);
      if (!src || !src.id) throw new Error('未获取到源知识库配置');
      setCreatePayload(pickAllowed(src, DATASET_CREATE_ALLOWED_KEYS));
    } catch (e) {
      setCreatePayload({});
      setCreateError(e?.message || '读取源知识库配置失败');
    }
  }

  async function createKb() {
    if (!isAdmin) return;
    setCreateError('');

    const name = String(createName || '').trim();
    if (!name) {
      setCreateError('请输入知识库名称');
      return;
    }

    const payload = { name, ...pickAllowed(createPayload, DATASET_CREATE_ALLOWED_KEYS) };
    setKbBusy(true);
    try {
      const created = await knowledgeApi.createRagflowDataset(payload);
      if (!created || !created.id) throw new Error('新建成功但未返回知识库信息');
      setCreateOpen(false);
      await fetchKbList();
      await loadKbDetail(created.id);
    } catch (e) {
      setCreateError(e?.message || '创建失败');
    } finally {
      setKbBusy(false);
    }
  }

  const shellStyle = {
    padding: '16px',
    display: 'grid',
    gridTemplateColumns: '360px 1fr',
    gap: '14px',
    alignItems: 'start',
  };

  const panelStyle = {
    background: '#ffffff',
    border: '1px solid #e5e7eb',
    borderRadius: '12px',
    overflow: 'hidden',
    boxShadow: '0 6px 18px rgba(15, 23, 42, 0.06)',
  };

  const headerBtn = (active) => ({
    flex: '1 1 140px',
    padding: '10px 12px',
    borderRadius: '10px',
    border: '1px solid ' + (active ? '#1d4ed8' : '#e5e7eb'),
    background: active ? '#1d4ed8' : '#ffffff',
    color: active ? '#ffffff' : '#111827',
    cursor: 'pointer',
    fontWeight: 900,
  });

  return (
    <div style={{ padding: '12px 14px' }}>
      <div style={{ padding: '10px 12px', borderBottom: '1px solid #e5e7eb', background: '#f8fafc' }}>
        <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
          <button onClick={() => setSubtab('kbs')} style={headerBtn(subtab === 'kbs')}>
            知识库配置
          </button>
          <button onClick={() => setSubtab('chats')} style={headerBtn(subtab === 'chats')}>
            对话配置
          </button>
        </div>
      </div>

      {subtab === 'kbs' ? (
        <div style={shellStyle}>
          <section style={panelStyle}>
            <div style={{ padding: '14px 16px', borderBottom: '1px solid #e5e7eb' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', gap: '10px' }}>
                <div style={{ fontSize: '1rem', fontWeight: 950, color: '#111827' }}>知识库</div>
                <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
                  <div style={{ fontSize: '0.85rem', color: '#6b7280' }}>{kbLoading ? '加载中...' : String(kbList.length) + ' 个'}</div>
                  {isAdmin && (
                    <button
                      onClick={openCreate}
                      style={{
                        padding: '6px 10px',
                        borderRadius: '10px',
                        border: '1px solid #1d4ed8',
                        background: '#1d4ed8',
                        color: '#ffffff',
                        cursor: 'pointer',
                        fontWeight: 900,
                      }}
                    >
                      新建
                    </button>
                  )}
                </div>
              </div>

              <div style={{ display: 'flex', gap: '8px', marginTop: '10px' }}>
                <input
                  value={kbFilter}
                  onChange={(e) => setKbFilter(e.target.value)}
                  placeholder="按名称 / ID / 描述筛选"
                  style={{ flex: 1, padding: '10px 12px', border: '1px solid #e5e7eb', borderRadius: '10px', outline: 'none' }}
                />
                <button
                  onClick={fetchKbList}
                  disabled={kbLoading}
                  style={{
                    padding: '10px 12px',
                    borderRadius: '10px',
                    border: '1px solid #e5e7eb',
                    background: kbLoading ? '#f3f4f6' : '#ffffff',
                    cursor: kbLoading ? 'not-allowed' : 'pointer',
                    fontWeight: 800,
                  }}
                >
                  刷新
                </button>
              </div>

              {kbError && <div style={{ marginTop: '10px', color: '#b91c1c', fontSize: '0.9rem' }}>{kbError}</div>}
            </div>

            <div style={{ padding: '12px' }}>
              {filteredKbList.map((ds) => {
                const id = String(ds?.id || '');
                const name = String(ds?.name || '');
                const isSelected = String(kbSelected?.id || '') === id;
                const deleteDisabled = !isAdmin || kbBusy;
                const emptyInfo = datasetIsEmpty(ds);
                const canDelete = emptyInfo.known && emptyInfo.empty;

                return (
                  <div key={id} style={{ position: 'relative', marginBottom: '10px' }}>
                    <button
                      onClick={() => loadKbDetail(id)}
                      style={{
                        width: '100%',
                        textAlign: 'left',
                        padding: '12px 56px 12px 12px',
                        borderRadius: '10px',
                        border: '1px solid ' + (isSelected ? '#60a5fa' : '#e5e7eb'),
                        background: isSelected ? '#eff6ff' : '#ffffff',
                        cursor: 'pointer',
                      }}
                      title={id}
                    >
                      <div style={{ fontWeight: 950, color: '#111827', fontSize: '0.95rem', lineHeight: 1.2 }}>{name || '(未命名)'}</div>
                      <div style={{ marginTop: '6px', color: '#6b7280', fontSize: '0.8rem' }}>{id ? 'ID: ' + id : 'ID: (unknown)'}</div>
                    </button>

                    {isAdmin && (
                      <button
                        onClick={(e) => {
                          e.preventDefault();
                          e.stopPropagation();
                          deleteKb(ds);
                        }}
                        disabled={deleteDisabled || !canDelete}
                        style={{
                          position: 'absolute',
                          right: '10px',
                          top: '10px',
                          width: '44px',
                          height: '36px',
                          borderRadius: '10px',
                          border: '1px solid ' + (deleteDisabled || !canDelete ? '#e5e7eb' : '#fecaca'),
                          background: deleteDisabled || !canDelete ? '#f9fafb' : '#fff1f2',
                          color: deleteDisabled || !canDelete ? '#9ca3af' : '#b91c1c',
                          cursor: deleteDisabled || !canDelete ? 'not-allowed' : 'pointer',
                          fontWeight: 900,
                        }}
                        title={canDelete ? '删除空知识库' : '非空知识库，禁止删除'}
                      >
                        删除
                      </button>
                    )}
                  </div>
                );
              })}
            </div>
          </section>

          <section style={panelStyle}>
            <div style={{ padding: '14px 16px', borderBottom: '1px solid #e5e7eb' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', gap: '10px' }}>
                <div style={{ fontSize: '1rem', fontWeight: 950, color: '#111827' }}>配置</div>
                <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
                  {kbSaveStatus && <div style={{ color: '#047857', fontWeight: 900 }}>{kbSaveStatus}</div>}
                  {isAdmin && (
                    <button
                      onClick={saveKb}
                      disabled={!kbSelected?.id || kbBusy || kbDetailLoading}
                      style={{
                        padding: '10px 14px',
                        borderRadius: '12px',
                        border: '1px solid #047857',
                        background: kbBusy ? '#6ee7b7' : '#10b981',
                        color: '#ffffff',
                        cursor: kbBusy ? 'not-allowed' : 'pointer',
                        fontWeight: 950,
                      }}
                    >
                      保存
                    </button>
                  )}
                </div>
              </div>
            </div>

            <div style={{ padding: '16px' }}>
              {kbDetailError && <div style={{ color: '#b91c1c', marginBottom: '10px' }}>{kbDetailError}</div>}
              {!kbSelected?.id ? (
                <div style={{ color: '#6b7280' }}>未加载</div>
              ) : (
                <div style={{ display: 'grid', gridTemplateColumns: '160px 1fr', gap: '10px', alignItems: 'center' }}>
                  <div style={{ fontWeight: 900, color: '#111827' }}>名称</div>
                  <input
                    value={kbNameText}
                    onChange={(e) => setKbNameText(e.target.value)}
                    disabled={!isAdmin}
                    style={{
                      width: '100%',
                      padding: '10px 12px',
                      borderRadius: '10px',
                      border: '1px solid #e5e7eb',
                      outline: 'none',
                      background: isAdmin ? '#ffffff' : '#f9fafb',
                    }}
                  />
                </div>
              )}
            </div>
          </section>

          {createOpen && (
            <div
              role="dialog"
              aria-modal="true"
              onMouseDown={(e) => {
                if (e.target === e.currentTarget) setCreateOpen(false);
              }}
              style={{
                position: 'fixed',
                inset: 0,
                background: 'rgba(17, 24, 39, 0.55)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                padding: '20px',
                zIndex: 1000,
              }}
            >
              <div
                style={{
                  width: 'min(980px, 96vw)',
                  background: 'white',
                  borderRadius: '14px',
                  border: '1px solid #e5e7eb',
                  overflow: 'hidden',
                  boxShadow: '0 20px 50px rgba(0,0,0,0.35)',
                }}
              >
                <div style={{ padding: '14px 16px', borderBottom: '1px solid #e5e7eb', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div style={{ fontWeight: 950, color: '#111827' }}>新建知识库</div>
                  <button
                    onClick={() => setCreateOpen(false)}
                    style={{ border: '1px solid #e5e7eb', background: '#ffffff', borderRadius: '10px', padding: '8px 10px', cursor: 'pointer', fontWeight: 900 }}
                  >
                    关闭
                  </button>
                </div>

                <div style={{ padding: '14px 16px' }}>
                  <div style={{ display: 'grid', gridTemplateColumns: '160px 1fr', gap: '10px', alignItems: 'center' }}>
                    <div style={{ fontWeight: 900, color: '#111827' }}>名称</div>
                    <input
                      value={createName}
                      onChange={(e) => setCreateName(e.target.value)}
                      placeholder="输入新知识库名称"
                      style={{ width: '100%', padding: '10px 12px', borderRadius: '10px', border: '1px solid #e5e7eb', outline: 'none' }}
                    />
                  </div>

                  <div style={{ marginTop: '12px', display: 'grid', gridTemplateColumns: '160px 1fr', gap: '10px' }}>
                    <div style={{ fontWeight: 900, color: '#111827' }}>复制配置</div>
                    <select
                      value={createFromId}
                      onChange={(e) => {
                        const val = e.target.value;
                        setCreateFromId(val);
                        syncCreateFromCopy(val);
                      }}
                      style={{ padding: '10px 12px', borderRadius: '10px', border: '1px solid #e5e7eb' }}
                      disabled={!kbList.length}
                    >
                      {kbList.map((ds) => (
                        <option key={String(ds?.id || '')} value={String(ds?.id || '')}>
                          {String(ds?.name || ds?.id || '')}
                        </option>
                      ))}
                    </select>
                  </div>
                  {!kbList.length && <div style={{ marginTop: '8px', color: '#6b7280' }}>暂无可复制来源知识库</div>}

                  {createError && <div style={{ marginTop: '10px', color: '#b91c1c' }}>{createError}</div>}
                </div>

                <div style={{ padding: '14px 16px', borderTop: '1px solid #e5e7eb', display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
                  <button
                    onClick={() => setCreateOpen(false)}
                    style={{ padding: '10px 14px', borderRadius: '12px', border: '1px solid #e5e7eb', background: '#ffffff', cursor: 'pointer', fontWeight: 900 }}
                  >
                    取消
                  </button>
                  <button
                    onClick={createKb}
                    disabled={!isAdmin || kbBusy}
                    style={{
                      padding: '10px 14px',
                      borderRadius: '12px',
                      border: '1px solid #1d4ed8',
                      background: kbBusy ? '#93c5fd' : '#2563eb',
                      color: '#ffffff',
                      cursor: kbBusy ? 'not-allowed' : 'pointer',
                      fontWeight: 950,
                    }}
                  >
                    创建
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      ) : (
        <ChatConfigsPanel />
      )}
    </div>
  );
}
