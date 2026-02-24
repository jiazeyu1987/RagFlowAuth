import React, { useEffect, useMemo, useState } from 'react';
import { useAuth } from '../hooks/useAuth';
import { knowledgeApi } from '../features/knowledge/api';
import { ChatConfigsPanel } from './ChatConfigsPanel';

const DATASET_CREATE_ALLOWED_KEYS = ['description', 'chunk_method', 'embedding_model', 'avatar'];
const DATASET_UPDATE_ALLOWED_KEYS = ['name', ...DATASET_CREATE_ALLOWED_KEYS, 'pagerank'];

function pickAllowed(obj, allowedKeys) {
  if (!obj || typeof obj !== 'object' || Array.isArray(obj)) return {};
  const out = {};
  for (const k of allowedKeys) {
    if (Object.prototype.hasOwnProperty.call(obj, k)) out[k] = obj[k];
  }
  return out;
}

function prettyJson(obj) {
  return JSON.stringify(obj ?? {}, null, 2);
}

function parseJson(text) {
  try {
    const val = JSON.parse(text || '{}');
    if (!val || typeof val !== 'object' || Array.isArray(val)) return { ok: false, error: 'JSON must be an object' };
    return { ok: true, value: val };
  } catch (e) {
    return { ok: false, error: 'JSON parse failed: ' + (e?.message || String(e)) };
  }
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

function normalizeListResponse(res) {
  if (!res) return [];
  if (Array.isArray(res.datasets)) return res.datasets;
  if (res.data && Array.isArray(res.data.datasets)) return res.data.datasets;
  if (Array.isArray(res.data)) return res.data;
  return [];
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
  const [kbJsonText, setKbJsonText] = useState('{}');
  const [kbSaveStatus, setKbSaveStatus] = useState('');
  const [kbBusy, setKbBusy] = useState(false);

  const [createOpen, setCreateOpen] = useState(false);
  const [createMode, setCreateMode] = useState('blank'); // blank | copy
  const [createName, setCreateName] = useState('');
  const [createFromId, setCreateFromId] = useState('');
  const [createJsonText, setCreateJsonText] = useState('{}');
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
      setKbJsonText(prettyJson(pickAllowed(ds, DATASET_UPDATE_ALLOWED_KEYS)));
    } catch (e) {
      setKbSelected(null);
      setKbDetailError(e?.message || '鍔犺浇澶辫触');
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

    const parsed = parseJson(kbJsonText);
    if (!parsed.ok) {
      setKbDetailError(parsed.error);
      return;
    }

    const updates = {
      ...pickAllowed(parsed.value, DATASET_UPDATE_ALLOWED_KEYS),
      name: String(kbNameText || kbSelected.name || '').trim(),
    };
    if (!updates.name) {
      setKbDetailError('鍚嶇О涓嶈兘涓虹┖');
      return;
    }

    setKbBusy(true);
    try {
      const updated = await knowledgeApi.updateRagflowDataset(kbSelected.id, updates);
      if (!updated || !updated.id) throw new Error('Save succeeded but no dataset returned');
      setKbSelected(updated);
      setKbNameText(String(updated?.name || updates.name));
      setKbJsonText(prettyJson(pickAllowed(updated, DATASET_UPDATE_ALLOWED_KEYS)));
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
      setKbError('无法判断是否为空，已禁用删除（请先进入详情页确认）。');
      return;
    }
    if (!state.empty) {
      setKbError('该知识库不是空的，禁止删除（请先清空文档/Chunk）。');
      return;
    }
    const ok = window.confirm(
      '确认删除空知识库: ' + (ds.name || ds.id) + '\n\n只允许删除空知识库。',
    );
    if (!ok) return;

    setKbBusy(true);
    try {
      await knowledgeApi.deleteRagflowDataset(ds.id);
      if (kbSelected?.id === ds.id) setKbSelected(null);
      await fetchKbList();
    } catch (e) {
      setKbError(e?.message || '鍒犻櫎澶辫触');
    } finally {
      setKbBusy(false);
    }
  }

  function openCreate() {
    setCreateMode('blank');
    setCreateName('');
    setCreateFromId('');
    setCreateJsonText('{}');
    setCreateError('');
    setCreateOpen(true);
  }

  async function syncCreateJsonFromCopy(sourceId) {
    if (!sourceId) return;
    setCreateError('');
    try {
      const src = await knowledgeApi.getRagflowDataset(sourceId);
      if (!src || !src.id) throw new Error('鏈幏鍙栧埌婧愮煡璇嗗簱閰嶇疆');
      setCreateJsonText(prettyJson(pickAllowed(src, DATASET_CREATE_ALLOWED_KEYS)));
    } catch (e) {
      setCreateJsonText('{}');
      setCreateError(e?.message || '璇诲彇婧愮煡璇嗗簱閰嶇疆澶辫触');
    }
  }

  async function createKb() {
    if (!isAdmin) return;
    setCreateError('');

    const name = String(createName || '').trim();
    if (!name) {
      setCreateError('璇疯緭鍏ョ煡璇嗗簱鍚嶇О');
      return;
    }

    const parsed = parseJson(createJsonText);
    if (!parsed.ok) {
      setCreateError(parsed.error);
      return;
    }

    const payload = { name, ...pickAllowed(parsed.value, DATASET_CREATE_ALLOWED_KEYS) };
    setKbBusy(true);
    try {
      const created = await knowledgeApi.createRagflowDataset(payload);
      if (!created || !created.id) throw new Error('Create succeeded but no dataset returned');
      setCreateOpen(false);
      await fetchKbList();
      await loadKbDetail(created.id);
    } catch (e) {
      setCreateError(e?.message || '鍒涘缓澶辫触');
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
            鐭ヨ瘑搴撻厤缃?          </button>
          <button onClick={() => setSubtab('chats')} style={headerBtn(subtab === 'chats')}>
            瀵硅瘽閰嶇疆
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
                  <div style={{ fontSize: '0.85rem', color: '#6b7280' }}>
                    {kbLoading ? '加载中...' : String(kbList.length) + ' 个'}
                  </div>
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
                      鏂板缓
                    </button>
                  )}
                </div>
              </div>

              <div style={{ display: 'flex', gap: '8px', marginTop: '10px' }}>
                <input
                  value={kbFilter}
                  onChange={(e) => setKbFilter(e.target.value)}
                  placeholder="按名称 / ID / 描述筛选"
                  style={{
                    flex: 1,
                    padding: '10px 12px',
                    border: '1px solid #e5e7eb',
                    borderRadius: '10px',
                    outline: 'none',
                  }}
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
                  鍒锋柊
                </button>
              </div>

              {kbError && <div style={{ marginTop: '10px', color: '#b91c1c', fontSize: '0.9rem' }}>{kbError}</div>}
            </div>

            <div style={{ padding: '12px' }}>
              {filteredKbList.map((ds) => {
                const id = String(ds?.id || '');
                const name = String(ds?.name || '');
                const isSelected = String(kbSelected?.id || '') === id;
                const delState = datasetIsEmpty(ds);
                const deleteDisabled = !isAdmin || !delState.known || !delState.empty || kbBusy;

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
                      <div style={{ fontWeight: 950, color: '#111827', fontSize: '0.95rem', lineHeight: 1.2 }}>
                        {name || '(Unnamed)'}
                      </div>
                      <div style={{ marginTop: '6px', color: '#6b7280', fontSize: '0.8rem' }}>
                        {id ? 'ID: ' + id : 'ID: (unknown)'}
                      </div>
                    </button>

                    {isAdmin && (
                      <button
                        onClick={(e) => {
                          e.preventDefault();
                          e.stopPropagation();
                          deleteKb({ ...ds, id });
                        }}
                        disabled={deleteDisabled}
                        title={
                          !delState.known
                            ? 'Cannot determine whether empty; deletion disabled'
                            : delState.empty
                              ? 'Delete empty knowledge base'
                              : 'Non-empty knowledge base; deletion disabled'
                        }
                        style={{
                          position: 'absolute',
                          right: '10px',
                          top: '10px',
                          width: '44px',
                          height: '36px',
                          borderRadius: '10px',
                          border: '1px solid ' + (deleteDisabled ? '#e5e7eb' : '#fecaca'),
                          background: deleteDisabled ? '#f9fafb' : '#fff1f2',
                          color: deleteDisabled ? '#9ca3af' : '#b91c1c',
                          cursor: deleteDisabled ? 'not-allowed' : 'pointer',
                          fontWeight: 900,
                        }}
                      >
                        鍒犻櫎
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
                <div style={{ fontSize: '1rem', fontWeight: 950, color: '#111827' }}>閰嶇疆</div>
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
                      淇濆瓨
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
                <>
                  <div style={{ display: 'grid', gridTemplateColumns: '160px 1fr', gap: '10px', alignItems: 'center' }}>
                    <div style={{ fontWeight: 900, color: '#111827' }}>鍚嶇О</div>
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

                </>
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
                <div
                  style={{
                    padding: '14px 16px',
                    borderBottom: '1px solid #e5e7eb',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                  }}
                >
                  <div style={{ fontWeight: 950, color: '#111827' }}>新建知识库</div>
                  <button
                    onClick={() => setCreateOpen(false)}
                    style={{
                      border: '1px solid #e5e7eb',
                      background: '#ffffff',
                      borderRadius: '10px',
                      padding: '8px 10px',
                      cursor: 'pointer',
                      fontWeight: 900,
                    }}
                  >
                    鍏抽棴
                  </button>
                </div>

                <div style={{ padding: '14px 16px' }}>
                  <div style={{ display: 'grid', gridTemplateColumns: '160px 1fr', gap: '10px', alignItems: 'center' }}>
                    <div style={{ fontWeight: 900, color: '#111827' }}>鍚嶇О</div>
                    <input
                      value={createName}
                      onChange={(e) => setCreateName(e.target.value)}
                      placeholder="杈撳叆鏂扮煡璇嗗簱鍚嶇О"
                      style={{
                        width: '100%',
                        padding: '10px 12px',
                        borderRadius: '10px',
                        border: '1px solid #e5e7eb',
                        outline: 'none',
                      }}
                    />
                  </div>

                  <div style={{ marginTop: '12px', display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                    <button
                      onClick={() => {
                        setCreateMode('blank');
                        setCreateFromId('');
                        setCreateJsonText('{}');
                        setCreateError('');
                      }}
                      style={headerBtn(createMode === 'blank')}
                    >
                      鍗曠嫭鏂板缓
                    </button>
                    <button
                      onClick={() => {
                        setCreateMode('copy');
                        setCreateError('');
                        if (!createFromId && kbList.length) {
                          const firstId = String(kbList[0]?.id || '');
                          setCreateFromId(firstId);
                          syncCreateJsonFromCopy(firstId);
                        } else if (createFromId) {
                          syncCreateJsonFromCopy(createFromId);
                        }
                      }}
                      style={headerBtn(createMode === 'copy')}
                    >
                      澶嶅埗閰嶇疆
                    </button>
                  </div>

                  {createMode === 'copy' && (
                    <div style={{ marginTop: '12px', display: 'grid', gridTemplateColumns: '160px 1fr', gap: '10px' }}>
                      <div style={{ fontWeight: 900, color: '#111827' }}>来源知识库</div>
                      <select
                        value={createFromId}
                        onChange={(e) => {
                          const v = e.target.value;
                          setCreateFromId(v);
                          syncCreateJsonFromCopy(v);
                        }}
                        style={{ padding: '10px 12px', borderRadius: '10px', border: '1px solid #e5e7eb' }}
                      >
                        <option value="">璇烽€夋嫨...</option>
                        {kbList.map((ds) => (
                          <option key={String(ds?.id || '')} value={String(ds?.id || '')}>
                            {String(ds?.name || ds?.id || '')}
                          </option>
                        ))}
                      </select>
                    </div>
                  )}


                  {createError && <div style={{ marginTop: '10px', color: '#b91c1c' }}>{createError}</div>}
                </div>

                <div
                  style={{
                    padding: '14px 16px',
                    borderTop: '1px solid #e5e7eb',
                    display: 'flex',
                    justifyContent: 'flex-end',
                    gap: '10px',
                  }}
                >
                  <button
                    onClick={() => setCreateOpen(false)}
                    style={{
                      padding: '10px 14px',
                      borderRadius: '12px',
                      border: '1px solid #e5e7eb',
                      background: '#ffffff',
                      cursor: 'pointer',
                      fontWeight: 900,
                    }}
                  >
                    鍙栨秷
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
                    鍒涘缓
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
