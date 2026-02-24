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

  // Identity is controlled by path params for update, and by backend for create.
  delete body.id;
  delete body.chat_id;

  // Common read-only / computed fields observed in RAGFlow payloads.
  for (const k of [
    'tenant_id',
    'create_time',
    'update_time',
    'status',
    'token_num',
    'document_count',
    'chunk_count',
  ]) {
    delete body[k];
  }

  // Task metadata fields.
  for (const k of Object.keys(body)) {
    if (k.endsWith('_task_id') || k.endsWith('_task_finish_at') || k.endsWith('_task_start_at')) {
      delete body[k];
    }
  }

  // Normalize dataset linkage for create/update:
  // - The UI may have `datasets` (objects) from list responses
  // - Create/update endpoints typically expect `dataset_ids` (string[])
  // Keep existing explicit ids if provided; otherwise derive from `datasets`.
  const derivedIds = getSelectedDatasetIdsFromChatJson(body);
  const hasExplicitIds = Array.isArray(body.dataset_ids) || Array.isArray(body.kb_ids);
  if (!hasExplicitIds && derivedIds.length) {
    body.dataset_ids = derivedIds;
  }
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
  const a = obj.dataset_ids;
  const b = obj.kb_ids;
  const a2 = obj.datasetIds;
  const b2 = obj.kbIds;
  const a1 = obj.dataset_id ?? obj.datasetId;
  const b1 = obj.kb_id ?? obj.kbId;
  // RAGFlow responses differ by version:
  // - Some use `dataset_ids` (string[])
  // - Some use `kb_ids` (string[])
  // - Some use `datasetIds` / `kbIds` (string[])
  // - Some use `dataset_id` / `kb_id` (string)
  // - Some return `datasets` as a list of dataset objects or ids
  const aIds = Array.isArray(a) ? a.map((x) => String(x || '').trim()).filter(Boolean) : [];
  if (aIds.length) return aIds;
  const bIds = Array.isArray(b) ? b.map((x) => String(x || '').trim()).filter(Boolean) : [];
  if (bIds.length) return bIds;
  const a2Ids = Array.isArray(a2) ? a2.map((x) => String(x || '').trim()).filter(Boolean) : [];
  if (a2Ids.length) return a2Ids;
  const b2Ids = Array.isArray(b2) ? b2.map((x) => String(x || '').trim()).filter(Boolean) : [];
  if (b2Ids.length) return b2Ids;

  const one = [a1, b1].map((x) => String(x || '').trim()).filter(Boolean);
  if (one.length) return one;

  const ds = obj.datasets;
  if (Array.isArray(ds)) {
    const ids = [];
    for (const item of ds) {
      if (!item) continue;
      if (typeof item === 'string' || typeof item === 'number') {
        const s = String(item).trim();
        if (s) ids.push(s);
        continue;
      }
      if (typeof item === 'object') {
        const raw =
          item.id ??
          item.dataset_id ??
          item.kb_id ??
          item.datasetId ??
          item.kbId ??
          '';
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
  const [chatLocked, setChatLocked] = useState(null); // { message: string, desiredPayload: object }

  const [busy, setBusy] = useState(false);

  const [createOpen, setCreateOpen] = useState(false);
  const [createMode, setCreateMode] = useState('blank'); // blank | copy
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
      setChatError(e?.message || '鍔犺浇瀵硅瘽澶辫触');
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
      setChatDetailError(e?.message || '鍔犺浇澶辫触');
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
    if (!isAdmin) return;
    if (!datasetId) return;
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
      setChatDetailError('鍚嶇О涓嶈兘涓虹┖');
      return;
    }

    const updates = sanitizeChatPayload({ ...parsed.value, name });
    setBusy(true);
    try {
      const updated = await knowledgeApi.updateRagflowChat(chatSelected.id, updates);
      if (!updated || !updated.id) throw new Error('Save succeeded but no latest config returned');
      setChatSelected(updated);
      setChatNameText(String(updated?.name || name));
      setChatJsonText(prettyJson(sanitizeChatPayload(updated)));
      setChatSaveStatus('已保存');
      await fetchChatList();
      // Refresh this chat detail from server, so the panel always reflects the
      // canonical config after save (different RAGFlow versions vary fields).
      try {
        const fresh = await knowledgeApi.getRagflowChat(chatSelected.id);
        if (fresh && fresh.id) {
          setChatSelected(fresh);
          setChatNameText(String(fresh?.name || name));
          setChatJsonText(prettyJson(sanitizeChatPayload(fresh)));
        }
      } catch (e) {
        // Keep UI state from update response if refresh fails.
      }
    } catch (e) {
      const msg = String(e?.message || '');
      if (msg.includes('chat_dataset_locked') || msg.includes("doesn't own parsed file")) {
        setChatLocked({ message: msg, desiredPayload: updates });
        setChatDetailError(
          '该对话已关联已解析文档，当前配置不允许直接切换到不包含这些文档的知识库。可复制为新对话后再调整知识库。'
        );
      } else {
        setChatDetailError(msg || '淇濆瓨澶辫触');
      }
    } finally {
      setBusy(false);
    }
  }

  async function saveChatNameOnly() {
    if (!chatSelected?.id) return;
    const name = String(chatNameText || chatSelected.name || '').trim();
    if (!name) {
      setChatDetailError('鍚嶇О涓嶈兘涓虹┖');
      return;
    }
    setChatDetailError('');
    setChatSaveStatus('');
    setBusy(true);
    try {
      const updated = await knowledgeApi.updateRagflowChat(chatSelected.id, { name });
      if (!updated || !updated.id) throw new Error('Save succeeded but no latest config returned');
      setChatSelected(updated);
      setChatNameText(String(updated?.name || name));
      setChatJsonText(prettyJson(sanitizeChatPayload(updated)));
      setChatSaveStatus('已保存名称');
      setChatLocked(null);
      await fetchChatList();
    } catch (e) {
      setChatDetailError(e?.message || '淇濆瓨澶辫触');
    } finally {
      setBusy(false);
    }
  }

  async function copyToNewChat() {
    if (!isAdmin) return;
    if (!chatLocked?.desiredPayload) return;
    const baseName = String(chatNameText || chatSelected?.name || '新对话').trim() || '新对话';
    const name = String(baseName) + '_copy';
    setBusy(true);
    try {
      const created = await knowledgeApi.createRagflowChat({ ...chatLocked.desiredPayload, name });
      if (!created || !created.id) throw new Error('鏂板缓鎴愬姛浣嗘湭杩斿洖瀵硅瘽淇℃伅');
      setChatLocked(null);
      setChatDetailError('');
      setChatSaveStatus('已复制为新对话');
      await fetchChatList();
      await loadChatDetail(created.id);
    } catch (e) {
      setChatDetailError(e?.message || '澶嶅埗鍒涘缓澶辫触');
    } finally {
      setBusy(false);
    }
  }

  async function clearParsedFiles() {
    if (!chatSelected?.id) return;
    if (!isAdmin) return;
    const ok = window.confirm(
      '确认清除该对话的已解析文件绑定？\n\n这将尝试解除 RAGFlow 的 parsed files 归属限制，以便你切换知识库。\n如果 RAGFlow 不支持清除，该操作可能无效果。',
    );
    if (!ok) return;
    setChatDetailError('');
    setChatSaveStatus('');
    setChatLocked(null);
    setBusy(true);
    try {
      await knowledgeApi.clearRagflowChatParsedFiles(chatSelected.id);
      await fetchChatList();
      await loadChatDetail(chatSelected.id);
      setChatSaveStatus('宸叉竻闄よВ鏋愮粦瀹氾紙濡傛敮鎸侊級');
    } catch (e) {
      setChatDetailError(e?.message || '娓呴櫎澶辫触');
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
      setChatError(e?.message || '鍒犻櫎澶辫触');
    } finally {
      setBusy(false);
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
      if (!created || !created.id) throw new Error('鏂板缓鎴愬姛浣嗘湭杩斿洖瀵硅瘽淇℃伅');
      setCreateOpen(false);
      await fetchChatList();
      await loadChatDetail(created.id);
    } catch (e) {
      setCreateError(e?.message || '鍒涘缓澶辫触');
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
    <div style={shellStyle}>
      <section style={panelStyle}>
        <div style={{ padding: '14px 16px', borderBottom: '1px solid #e5e7eb' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', gap: '10px' }}>
            <div style={{ fontSize: '1rem', fontWeight: 950, color: '#111827' }}>瀵硅瘽</div>
            <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
              <div style={{ fontSize: '0.85rem', color: '#6b7280' }}>
                {chatLoading ? '加载中...' : String(chatList.length) + ' 个'}
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
              value={chatFilter}
              onChange={(e) => setChatFilter(e.target.value)}
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
              鍒锋柊
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
                  <div style={{ fontWeight: 950, color: '#111827', fontSize: '0.95rem', lineHeight: 1.2 }}>
                    {name || '(鏈懡鍚?'}
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
                  淇濆瓨
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
                title="Clear parsed-file bindings so you can change dataset selection"
              >
                清除解析文件绑定
              </button>
              <div style={{ color: '#6b7280', fontSize: '0.8rem' }}>{String(chatLocked.message || '').slice(0, 180)}</div>
            </div>
          )}
          {!chatSelected?.id ? (
            <div style={{ color: '#6b7280' }}>未加载</div>
          ) : (
            <>
              <div style={{ display: 'grid', gridTemplateColumns: '160px 1fr', gap: '10px', alignItems: 'center' }}>
                <div style={{ fontWeight: 900, color: '#111827' }}>鍚嶇О</div>
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
                    <div style={{ fontSize: '0.85rem', color: '#6b7280' }}>
                      {kbLoading ? '加载中...' : String(kbList.length) + ' 个'}
                    </div>
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
                      鍒锋柊
                    </button>
                  </div>
                </div>

                {kbError && <div style={{ marginTop: '8px', color: '#b91c1c' }}>{kbError}</div>}

                <div
                  style={{
                    marginTop: '10px',
                    border: '1px solid #e5e7eb',
                    borderRadius: '12px',
                    overflow: 'hidden',
                    background: '#ffffff',
                  }}
                >
                  <div
                    style={{
                      maxHeight: '220px',
                      overflow: 'auto',
                      padding: '10px',
                      display: 'grid',
                      gap: '8px',
                    }}
                  >
                    {kbList.length === 0 ? (
                      <div style={{ color: '#6b7280' }}>{kbLoading ? '鍔犺浇涓?.' : '鏃犵煡璇嗗簱'}</div>
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
                            <input
                              type="checkbox"
                              checked={checked}
                              disabled={!isAdmin || !id}
                              onChange={() => toggleDatasetSelection(id)}
                              style={{ marginTop: '2px' }}
                            />
                            <div style={{ minWidth: 0 }}>
                              <div style={{ fontWeight: 950, color: '#111827', lineHeight: 1.2 }}>{name}</div>
                              <div style={{ marginTop: '4px', color: '#6b7280', fontSize: '0.82rem' }}>
                                ID: {id || '(unknown)'}
                              </div>
                            </div>
                          </label>
                        );
                      })
                    )}
                  </div>
                </div>

                <div style={{ marginTop: '8px', color: '#6b7280', fontSize: '0.85rem' }}>
                  勾选知识库后，点击右上角保存才会生效。
                </div>
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
              <div style={{ fontWeight: 950, color: '#111827' }}>鏂板缓瀵硅瘽</div>
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
                  placeholder="输入新对话名称"
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
                    if (!createFromId && chatList.length) {
                      const firstId = String(chatList[0]?.id || '');
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
                  <div style={{ fontWeight: 900, color: '#111827' }}>鏉ユ簮瀵硅瘽</div>
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
                    {chatList.map((c) => (
                      <option key={String(c?.id || '')} value={String(c?.id || '')}>
                        {String(c?.name || c?.id || '')}
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
                鍒涘缓
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
