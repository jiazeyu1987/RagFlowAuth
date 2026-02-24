import React, { useEffect, useMemo, useState } from 'react';
import { useAuth } from '../hooks/useAuth';
import { knowledgeApi } from '../features/knowledge/api';

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

function sanitizeChatPayload(payload) {
  const body = payload && typeof payload === 'object' && !Array.isArray(payload) ? { ...payload } : {};

  delete body.id;
  delete body.chat_id;

  for (const k of ['tenant_id', 'create_time', 'update_time', 'status', 'token_num', 'document_count', 'chunk_count']) {
    delete body[k];
  }

  for (const k of Object.keys(body)) {
    if (k.endsWith('_task_id') || k.endsWith('_task_finish_at') || k.endsWith('_task_start_at')) delete body[k];
  }

  const derivedIds = getSelectedDatasetIdsFromChatJson(body);
  const hasExplicitIds = Array.isArray(body.dataset_ids) || Array.isArray(body.kb_ids);
  if (!hasExplicitIds && derivedIds.length) body.dataset_ids = derivedIds;

  delete body.datasets;
  return body;
}

function normalizeChatListResponse(res) {
  if (!res) return [];
  if (Array.isArray(res.chats)) return res.chats;
  if (res.data && Array.isArray(res.data.chats)) return res.data.chats;
  if (Array.isArray(res.data)) return res.data;
  return [];
}

function normalizeDatasetListResponse(res) {
  if (!res) return [];
  if (Array.isArray(res.datasets)) return res.datasets;
  if (res.data && Array.isArray(res.data.datasets)) return res.data.datasets;
  if (Array.isArray(res.data)) return res.data;
  return [];
}

function getSelectedDatasetIdsFromChatJson(val) {
  const obj = val && typeof val === 'object' && !Array.isArray(val) ? val : {};
  const candidates = [obj.dataset_ids, obj.kb_ids, obj.datasetIds, obj.kbIds];
  for (const arr of candidates) {
    if (Array.isArray(arr)) {
      const ids = arr.map((x) => String(x || '').trim()).filter(Boolean);
      if (ids.length) return ids;
    }
  }

  const one = [obj.dataset_id, obj.datasetId, obj.kb_id, obj.kbId]
    .map((x) => String(x || '').trim())
    .filter(Boolean);
  if (one.length) return one;

  if (Array.isArray(obj.datasets)) {
    const ids = [];
    for (const item of obj.datasets) {
      if (!item) continue;
      if (typeof item === 'string' || typeof item === 'number') {
        const s = String(item).trim();
        if (s) ids.push(s);
        continue;
      }
      if (typeof item === 'object') {
        const raw = item.id ?? item.dataset_id ?? item.kb_id ?? item.datasetId ?? item.kbId ?? '';
        const s = String(raw || '').trim();
        if (s) ids.push(s);
      }
    }
    return ids;
  }

  return [];
}

function getDatasetIdsKeyForUpdate(val) {
  const obj = val && typeof val === 'object' && !Array.isArray(val) ? val : {};
  if (Array.isArray(obj.dataset_ids)) return 'dataset_ids';
  if (Array.isArray(obj.kb_ids)) return 'kb_ids';
  return 'dataset_ids';
}

export function ChatConfigsPanel() {
  const { user } = useAuth();
  const isAdmin = (user?.role || '') === 'admin';

  const [chatList, setChatList] = useState([]);
  const [chatLoading, setChatLoading] = useState(false);
  const [chatError, setChatError] = useState('');
  const [chatFilter, setChatFilter] = useState('');

  const [chatSelected, setChatSelected] = useState(null);
  const [chatDetailLoading, setChatDetailLoading] = useState(false);
  const [chatDetailError, setChatDetailError] = useState('');
  const [chatNameText, setChatNameText] = useState('');
  const [chatJsonText, setChatJsonText] = useState('{}');
  const [chatSaveStatus, setChatSaveStatus] = useState('');
  const [chatLocked, setChatLocked] = useState(null);

  const [busy, setBusy] = useState(false);

  const [createOpen, setCreateOpen] = useState(false);
  const [createName, setCreateName] = useState('');
  const [createFromId, setCreateFromId] = useState('');
  const [createJsonText, setCreateJsonText] = useState('{}');
  const [createError, setCreateError] = useState('');

  const [kbList, setKbList] = useState([]);
  const [kbLoading, setKbLoading] = useState(false);
  const [kbError, setKbError] = useState('');

  const filteredChatList = useMemo(() => {
    const kw = String(chatFilter || '').trim().toLowerCase();
    if (!kw) return chatList;
    return chatList.filter((c) => {
      const id = String(c?.id || '').toLowerCase();
      const name = String(c?.name || '').toLowerCase();
      const desc = String(c?.description || '').toLowerCase();
      return id.includes(kw) || name.includes(kw) || desc.includes(kw);
    });
  }, [chatFilter, chatList]);

  async function fetchChatList() {
    setChatError('');
    setChatLoading(true);
    try {
      const res = await knowledgeApi.listRagflowChats({ page_size: 1000 });
      setChatList(normalizeChatListResponse(res));
    } catch (e) {
      setChatList([]);
      setChatError(e?.message || '加载对话失败');
    } finally {
      setChatLoading(false);
    }
  }

  async function fetchKbList() {
    setKbError('');
    setKbLoading(true);
    try {
      const res = await knowledgeApi.listRagflowDatasets();
      setKbList(normalizeDatasetListResponse(res));
    } catch (e) {
      setKbList([]);
      setKbError(e?.message || '加载知识库失败');
    } finally {
      setKbLoading(false);
    }
  }

  async function loadChatDetail(chatId) {
    if (!chatId) return;
    setChatDetailError('');
    setChatSaveStatus('');
    setChatLocked(null);
    setChatDetailLoading(true);
    try {
      const chat = await knowledgeApi.getRagflowChat(chatId);
      if (!chat || !chat.id) throw new Error('chat_not_found');
      setChatSelected(chat);
      setChatNameText(String(chat?.name || ''));
      setChatJsonText(prettyJson(sanitizeChatPayload(chat)));
    } catch (e) {
      setChatSelected(null);
      setChatDetailError(e?.message || '加载失败');
    } finally {
      setChatDetailLoading(false);
    }
  }

  const selectedDatasetIds = useMemo(() => {
    const parsed = parseJson(chatJsonText);
    if (!parsed.ok) return [];
    return getSelectedDatasetIdsFromChatJson(parsed.value);
  }, [chatJsonText]);

  function toggleDatasetSelection(datasetId) {
    if (!isAdmin || !datasetId) return;
    setChatDetailError('');
    setChatSaveStatus('');

    const parsed = parseJson(chatJsonText);
    if (!parsed.ok) {
      setChatDetailError(parsed.error);
      return;
    }

    const key = getDatasetIdsKeyForUpdate(parsed.value);
    const prev = Array.isArray(parsed.value?.[key]) ? parsed.value[key].map((x) => String(x || '').trim()) : [];
    const id = String(datasetId || '').trim();
    if (!id) return;

    const nextSet = new Set(prev.filter(Boolean));
    if (nextSet.has(id)) nextSet.delete(id);
    else nextSet.add(id);

    const nextObj = sanitizeChatPayload({ ...parsed.value, [key]: Array.from(nextSet) });
    setChatJsonText(prettyJson(nextObj));
  }

  useEffect(() => {
    fetchChatList();
    fetchKbList();
  }, []);

  useEffect(() => {
    if (!chatSelected && chatList.length) loadChatDetail(chatList[0]?.id || '');
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [chatList]);

  async function saveChat() {
    if (!chatSelected?.id) return;
    setChatDetailError('');
    setChatSaveStatus('');
    setChatLocked(null);

    const parsed = parseJson(chatJsonText);
    if (!parsed.ok) {
      setChatDetailError(parsed.error);
      return;
    }

    const name = String(chatNameText || chatSelected.name || '').trim();
    if (!name) {
      setChatDetailError('名称不能为空');
      return;
    }

    const updates = sanitizeChatPayload({ ...parsed.value, name });
    setBusy(true);
    try {
      const updated = await knowledgeApi.updateRagflowChat(chatSelected.id, updates);
      if (!updated || !updated.id) throw new Error('保存成功但未返回最新配置');
      setChatSelected(updated);
      setChatNameText(String(updated?.name || name));
      setChatJsonText(prettyJson(sanitizeChatPayload(updated)));
      setChatSaveStatus('已保存');
      await fetchChatList();
      try {
        const fresh = await knowledgeApi.getRagflowChat(chatSelected.id);
        if (fresh && fresh.id) {
          setChatSelected(fresh);
          setChatNameText(String(fresh?.name || name));
          setChatJsonText(prettyJson(sanitizeChatPayload(fresh)));
        }
      } catch (_) {}
    } catch (e) {
      const msg = String(e?.message || '');
      if (msg.includes('chat_dataset_locked') || msg.includes("doesn't own parsed file")) {
        setChatLocked({ message: msg, desiredPayload: updates });
        setChatDetailError('该对话已关联已解析文档，当前配置不允许直接切换到不包含这些文档的知识库。可复制为新对话后再调整知识库。');
      } else {
        setChatDetailError(msg || '保存失败');
      }
    } finally {
      setBusy(false);
    }
  }

  async function saveChatNameOnly() {
    if (!chatSelected?.id) return;
    const name = String(chatNameText || chatSelected.name || '').trim();
    if (!name) {
      setChatDetailError('名称不能为空');
      return;
    }
    setChatDetailError('');
    setChatSaveStatus('');
    setBusy(true);
    try {
      const updated = await knowledgeApi.updateRagflowChat(chatSelected.id, { name });
      if (!updated || !updated.id) throw new Error('保存成功但未返回最新配置');
      setChatSelected(updated);
      setChatNameText(String(updated?.name || name));
      setChatJsonText(prettyJson(sanitizeChatPayload(updated)));
      setChatSaveStatus('已保存名称');
      setChatLocked(null);
      await fetchChatList();
    } catch (e) {
      setChatDetailError(e?.message || '保存失败');
    } finally {
      setBusy(false);
    }
  }

  async function copyToNewChat() {
    if (!isAdmin || !chatLocked?.desiredPayload) return;
    const baseName = String(chatNameText || chatSelected?.name || '新对话').trim() || '新对话';
    const name = String(baseName) + '_copy';
    setBusy(true);
    try {
      const created = await knowledgeApi.createRagflowChat({ ...chatLocked.desiredPayload, name });
      if (!created || !created.id) throw new Error('新建成功但未返回对话信息');
      setChatLocked(null);
      setChatDetailError('');
      setChatSaveStatus('已复制为新对话');
      await fetchChatList();
      await loadChatDetail(created.id);
    } catch (e) {
      setChatDetailError(e?.message || '复制创建失败');
    } finally {
      setBusy(false);
    }
  }

  async function clearParsedFiles() {
    if (!chatSelected?.id || !isAdmin) return;
    const ok = window.confirm('确认清除该对话的已解析文件绑定？\n\n这将尝试解除 RAGFlow 的 parsed files 归属限制，以便切换知识库。');
    if (!ok) return;

    setChatDetailError('');
    setChatSaveStatus('');
    setChatLocked(null);
    setBusy(true);
    try {
      await knowledgeApi.clearRagflowChatParsedFiles(chatSelected.id);
      await fetchChatList();
      await loadChatDetail(chatSelected.id);
      setChatSaveStatus('已清除解析绑定（如支持）');
    } catch (e) {
      setChatDetailError(e?.message || '清除失败');
    } finally {
      setBusy(false);
    }
  }

  async function deleteChat(chat) {
    if (!chat?.id) return;
    const ok = window.confirm('确认删除对话: ' + (chat.name || chat.id));
    if (!ok) return;
    setBusy(true);
    try {
      await knowledgeApi.deleteRagflowChat(chat.id);
      if (chatSelected?.id === chat.id) setChatSelected(null);
      await fetchChatList();
    } catch (e) {
      setChatError(e?.message || '删除失败');
    } finally {
      setBusy(false);
    }
  }

  function openCreate() {
    setCreateName('');
    const firstId = String(chatList[0]?.id || '');
    setCreateFromId(firstId);
    setCreateJsonText('{}');
    setCreateError('');
    if (firstId) syncCreateJsonFromCopy(firstId);
    setCreateOpen(true);
  }

  async function syncCreateJsonFromCopy(sourceId) {
    if (!sourceId) return;
    setCreateError('');
    try {
      const src = await knowledgeApi.getRagflowChat(sourceId);
      if (!src || !src.id) throw new Error('未获取到源对话配置');
      setCreateJsonText(prettyJson(sanitizeChatPayload(src)));
    } catch (e) {
      setCreateJsonText('{}');
      setCreateError(e?.message || '读取源对话配置失败');
    }
  }

  async function createChat() {
    if (!isAdmin) return;
    setCreateError('');

    const name = String(createName || '').trim();
    if (!name) {
      setCreateError('请输入对话名称');
      return;
    }

    const parsed = parseJson(createJsonText);
    if (!parsed.ok) {
      setCreateError(parsed.error);
      return;
    }

    const payload = sanitizeChatPayload({ ...parsed.value, name });
    setBusy(true);
    try {
      const created = await knowledgeApi.createRagflowChat(payload);
      if (!created || !created.id) throw new Error('新建成功但未返回对话信息');
      setCreateOpen(false);
      await fetchChatList();
      await loadChatDetail(created.id);
    } catch (e) {
      setCreateError(e?.message || '创建失败');
    } finally {
      setBusy(false);
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

  return (
    <div style={shellStyle}>
      <section style={panelStyle}>
        <div style={{ padding: '14px 16px', borderBottom: '1px solid #e5e7eb' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', gap: '10px' }}>
            <div style={{ fontSize: '1rem', fontWeight: 950, color: '#111827' }}>对话</div>
            <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
              <div style={{ fontSize: '0.85rem', color: '#6b7280' }}>{chatLoading ? '加载中...' : String(chatList.length) + ' 个'}</div>
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
              value={chatFilter}
              onChange={(e) => setChatFilter(e.target.value)}
              placeholder="按名称 / ID / 描述筛选"
              style={{ flex: 1, padding: '10px 12px', border: '1px solid #e5e7eb', borderRadius: '10px', outline: 'none' }}
            />
            <button
              onClick={fetchChatList}
              disabled={chatLoading}
              style={{
                padding: '10px 12px',
                borderRadius: '10px',
                border: '1px solid #e5e7eb',
                background: chatLoading ? '#f3f4f6' : '#ffffff',
                cursor: chatLoading ? 'not-allowed' : 'pointer',
                fontWeight: 800,
              }}
            >
              刷新
            </button>
          </div>

          {chatError && <div style={{ marginTop: '10px', color: '#b91c1c', fontSize: '0.9rem' }}>{chatError}</div>}
        </div>

        <div style={{ padding: '12px' }}>
          {filteredChatList.map((c) => {
            const id = String(c?.id || '');
            const name = String(c?.name || '');
            const isSelected = String(chatSelected?.id || '') === id;
            const deleteDisabled = !isAdmin || busy;

            return (
              <div key={id} style={{ position: 'relative', marginBottom: '10px' }}>
                <button
                  onClick={() => loadChatDetail(id)}
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
                      deleteChat({ ...c, id });
                    }}
                    disabled={deleteDisabled}
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
              {chatSaveStatus && <div style={{ color: '#047857', fontWeight: 900 }}>{chatSaveStatus}</div>}
              {isAdmin && (
                <button
                  onClick={saveChat}
                  disabled={!chatSelected?.id || busy || chatDetailLoading}
                  style={{
                    padding: '10px 14px',
                    borderRadius: '12px',
                    border: '1px solid #047857',
                    background: busy ? '#6ee7b7' : '#10b981',
                    color: '#ffffff',
                    cursor: busy ? 'not-allowed' : 'pointer',
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
          {chatDetailError && <div style={{ color: '#b91c1c', marginBottom: '10px' }}>{chatDetailError}</div>}
          {chatLocked && (
            <div style={{ marginBottom: '12px', display: 'flex', gap: '10px', flexWrap: 'wrap', alignItems: 'center' }}>
              <button
                onClick={copyToNewChat}
                disabled={!isAdmin || busy}
                style={{
                  padding: '8px 12px',
                  borderRadius: '10px',
                  border: '1px solid #1d4ed8',
                  background: '#1d4ed8',
                  color: '#ffffff',
                  cursor: !isAdmin || busy ? 'not-allowed' : 'pointer',
                  fontWeight: 950,
                }}
              >
                复制新对话
              </button>
              <button
                onClick={saveChatNameOnly}
                disabled={!isAdmin || busy}
                style={{
                  padding: '8px 12px',
                  borderRadius: '10px',
                  border: '1px solid #e5e7eb',
                  background: '#ffffff',
                  color: '#111827',
                  cursor: !isAdmin || busy ? 'not-allowed' : 'pointer',
                  fontWeight: 950,
                }}
              >
                仅保存名称
              </button>
              <button
                onClick={clearParsedFiles}
                disabled={!isAdmin || busy || !chatSelected?.id}
                style={{
                  padding: '8px 12px',
                  borderRadius: '10px',
                  border: '1px solid #f59e0b',
                  background: '#f59e0b',
                  color: '#111827',
                  cursor: !isAdmin || busy || !chatSelected?.id ? 'not-allowed' : 'pointer',
                  fontWeight: 950,
                }}
              >
                清除解析文件绑定
              </button>
            </div>
          )}

          {!chatSelected?.id ? (
            <div style={{ color: '#6b7280' }}>未加载</div>
          ) : (
            <>
              <div style={{ display: 'grid', gridTemplateColumns: '160px 1fr', gap: '10px', alignItems: 'center' }}>
                <div style={{ fontWeight: 900, color: '#111827' }}>名称</div>
                <input
                  value={chatNameText}
                  onChange={(e) => setChatNameText(e.target.value)}
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

              <div style={{ marginTop: '14px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', gap: '10px' }}>
                  <div style={{ fontWeight: 950, color: '#111827' }}>知识库</div>
                  <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
                    <div style={{ fontSize: '0.85rem', color: '#6b7280' }}>{kbLoading ? '加载中...' : String(kbList.length) + ' 个'}</div>
                    <button
                      onClick={fetchKbList}
                      disabled={kbLoading}
                      style={{
                        padding: '8px 10px',
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
                </div>

                {kbError && <div style={{ marginTop: '8px', color: '#b91c1c' }}>{kbError}</div>}

                <div style={{ marginTop: '10px', border: '1px solid #e5e7eb', borderRadius: '12px', overflow: 'hidden', background: '#ffffff' }}>
                  <div style={{ maxHeight: '220px', overflow: 'auto', padding: '10px', display: 'grid', gap: '8px' }}>
                    {kbList.length === 0 ? (
                      <div style={{ color: '#6b7280' }}>{kbLoading ? '加载中...' : '无知识库'}</div>
                    ) : (
                      kbList.map((kb) => {
                        const id = String(kb?.id || '').trim();
                        const name = String(kb?.name || kb?.title || id || '').trim();
                        const checked = !!id && selectedDatasetIds.includes(id);
                        return (
                          <label
                            key={id || name}
                            style={{
                              display: 'flex',
                              gap: '10px',
                              alignItems: 'flex-start',
                              padding: '10px 12px',
                              border: '1px solid #e5e7eb',
                              borderRadius: '12px',
                              background: checked ? '#eff6ff' : '#ffffff',
                              cursor: isAdmin ? 'pointer' : 'default',
                            }}
                          >
                            <input type="checkbox" checked={checked} disabled={!isAdmin || !id} onChange={() => toggleDatasetSelection(id)} style={{ marginTop: '2px' }} />
                            <div style={{ minWidth: 0 }}>
                              <div style={{ fontWeight: 950, color: '#111827', lineHeight: 1.2 }}>{name}</div>
                              <div style={{ marginTop: '4px', color: '#6b7280', fontSize: '0.82rem' }}>ID: {id || '(unknown)'}</div>
                            </div>
                          </label>
                        );
                      })
                    )}
                  </div>
                </div>

                <div style={{ marginTop: '8px', color: '#6b7280', fontSize: '0.85rem' }}>勾选知识库后，点击右上角保存才会生效。</div>
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
            <div style={{ padding: '14px 16px', borderBottom: '1px solid #e5e7eb', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div style={{ fontWeight: 950, color: '#111827' }}>新建对话</div>
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
                  placeholder="输入新对话名称"
                  style={{ width: '100%', padding: '10px 12px', borderRadius: '10px', border: '1px solid #e5e7eb', outline: 'none' }}
                />
              </div>

              <div style={{ marginTop: '12px', display: 'grid', gridTemplateColumns: '160px 1fr', gap: '10px' }}>
                <div style={{ fontWeight: 900, color: '#111827' }}>复制配置</div>
                <select
                  value={createFromId}
                  onChange={(e) => {
                    const v = e.target.value;
                    setCreateFromId(v);
                    syncCreateJsonFromCopy(v);
                  }}
                  style={{ padding: '10px 12px', borderRadius: '10px', border: '1px solid #e5e7eb' }}
                  disabled={!chatList.length}
                >
                  {chatList.map((c) => (
                    <option key={String(c?.id || '')} value={String(c?.id || '')}>
                      {String(c?.name || c?.id || '')}
                    </option>
                  ))}
                </select>
              </div>
              {!chatList.length && <div style={{ marginTop: '8px', color: '#6b7280' }}>暂无可复制来源对话</div>}

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
                onClick={createChat}
                disabled={!isAdmin || busy}
                style={{
                  padding: '10px 14px',
                  borderRadius: '12px',
                  border: '1px solid #1d4ed8',
                  background: busy ? '#93c5fd' : '#2563eb',
                  color: '#ffffff',
                  cursor: busy ? 'not-allowed' : 'pointer',
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
  );
}
