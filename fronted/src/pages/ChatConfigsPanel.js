import React, { useEffect, useMemo, useState } from 'react';
import ChatConfigCreateDialog from '../features/chat/configs/components/ChatConfigCreateDialog';
import ChatConfigDetailPanel from '../features/chat/configs/components/ChatConfigDetailPanel';
import ChatConfigListPanel from '../features/chat/configs/components/ChatConfigListPanel';
import {
  getDatasetIdsKeyForUpdate,
  getSelectedDatasetIdsFromChatJson,
  HIDDEN_CHAT_NAMES,
  parseJson,
  prettyJson,
  sanitizeChatPayload,
} from '../features/chat/configs/chatConfigUtils';
import { chatConfigsApi } from '../features/chat/configs/api';
import { knowledgeApi } from '../features/knowledge/api';
import { useAuth } from '../hooks/useAuth';

const MOBILE_BREAKPOINT = 768;

const panelStyle = {
  background: '#ffffff',
  border: '1px solid #e5e7eb',
  borderRadius: '12px',
  overflow: 'hidden',
  boxShadow: '0 6px 18px rgba(15, 23, 42, 0.06)',
};

export function ChatConfigsPanel() {
  const { user } = useAuth();
  const canManageChats = ['admin', 'sub_admin'].includes(String(user?.role || ''));
  const [isMobile, setIsMobile] = useState(() => {
    if (typeof window === 'undefined') return false;
    return window.innerWidth <= MOBILE_BREAKPOINT;
  });

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
  const [createError, setCreateError] = useState('');

  const [kbList, setKbList] = useState([]);
  const [kbLoading, setKbLoading] = useState(false);
  const [kbError, setKbError] = useState('');

  useEffect(() => {
    if (typeof window === 'undefined') return undefined;
    const handleResize = () => setIsMobile(window.innerWidth <= MOBILE_BREAKPOINT);
    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const filteredChatList = useMemo(() => {
    const keyword = String(chatFilter || '').trim().toLowerCase();
    if (!keyword) return chatList;
    return chatList.filter((chat) => {
      const id = String(chat?.id || '').toLowerCase();
      const name = String(chat?.name || '').toLowerCase();
      const description = String(chat?.description || '').toLowerCase();
      return id.includes(keyword) || name.includes(keyword) || description.includes(keyword);
    });
  }, [chatFilter, chatList]);

  const selectedDatasetIds = useMemo(() => {
    const parsed = parseJson(chatJsonText);
    if (!parsed.ok) return [];
    return getSelectedDatasetIdsFromChatJson(parsed.value);
  }, [chatJsonText]);

  async function fetchChatList() {
    setChatError('');
    setChatLoading(true);
    try {
      const chats = await chatConfigsApi.listChats({ page_size: 1000 });
      const visibleChats = chats.filter((chat) => {
        const rawName = String(chat?.name || '').trim();
        const normalized = rawName.replace(/^\[|\]$/g, '').trim();
        return !HIDDEN_CHAT_NAMES.has(rawName) && !HIDDEN_CHAT_NAMES.has(normalized);
      });
      setChatList(visibleChats);
    } catch (error) {
      setChatList([]);
      setChatError(error?.message || '加载对话列表失败');
    } finally {
      setChatLoading(false);
    }
  }

  async function fetchKbList() {
    setKbError('');
    setKbLoading(true);
    try {
      const datasets = await knowledgeApi.listRagflowDatasets();
      setKbList(datasets);
    } catch (error) {
      setKbList([]);
      setKbError(error?.message || '加载知识库列表失败');
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
      const chat = await chatConfigsApi.getChat(chatId);
      if (!chat || !chat.id) throw new Error('chat_not_found');
      setChatSelected(chat);
      setChatNameText(String(chat?.name || ''));
      setChatJsonText(prettyJson(sanitizeChatPayload(chat)));
    } catch (error) {
      setChatSelected(null);
      setChatDetailError(error?.message || '加载对话详情失败');
    } finally {
      setChatDetailLoading(false);
    }
  }

  function toggleDatasetSelection(datasetId) {
    if (!canManageChats || !datasetId) return;
    setChatDetailError('');
    setChatSaveStatus('');

    const parsed = parseJson(chatJsonText);
    if (!parsed.ok) {
      setChatDetailError(parsed.error);
      return;
    }

    const key = getDatasetIdsKeyForUpdate(parsed.value);
    const prev = Array.isArray(parsed.value?.[key])
      ? parsed.value[key].map((item) => String(item || '').trim())
      : [];
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
    if (!chatSelected && chatList.length) {
      loadChatDetail(chatList[0]?.id || '');
    }
  }, [chatList, chatSelected]);

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
      const updated = await chatConfigsApi.updateChat(chatSelected.id, updates);
      if (!updated || !updated.id) throw new Error('保存成功，但未返回最新配置');

      setChatSelected(updated);
      setChatNameText(String(updated?.name || name));
      setChatJsonText(prettyJson(sanitizeChatPayload(updated)));
      setChatSaveStatus('已保存');
      await fetchChatList();

      try {
        const fresh = await chatConfigsApi.getChat(chatSelected.id);
        if (fresh && fresh.id) {
          setChatSelected(fresh);
          setChatNameText(String(fresh?.name || name));
          setChatJsonText(prettyJson(sanitizeChatPayload(fresh)));
        }
      } catch (_) {}
    } catch (error) {
      const message = String(error?.message || '');
      if (message.includes('chat_dataset_not_ready')) {
        setChatLocked(null);
        setChatDetailError('所选知识库还没有已解析文档，暂时不能绑定到对话。请先上传并完成解析。');
      } else if (message.includes('chat_dataset_locked') || message.includes("doesn't own parsed file")) {
        setChatLocked({ message, desiredPayload: updates });
        setChatDetailError('该对话已关联已解析文档，当前不允许直接切换到不包含这些文档的知识库。可以先复制为新对话，再调整知识库。');
      } else {
        setChatDetailError(message || '保存失败');
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
      const updated = await chatConfigsApi.updateChat(chatSelected.id, { name });
      if (!updated || !updated.id) throw new Error('保存成功，但未返回最新配置');
      setChatSelected(updated);
      setChatNameText(String(updated?.name || name));
      setChatJsonText(prettyJson(sanitizeChatPayload(updated)));
      setChatSaveStatus('已保存名称');
      setChatLocked(null);
      await fetchChatList();
    } catch (error) {
      setChatDetailError(error?.message || '保存失败');
    } finally {
      setBusy(false);
    }
  }

  async function copyToNewChat() {
    if (!canManageChats || !chatLocked?.desiredPayload) return;
    const baseName = String(chatNameText || chatSelected?.name || '新对话').trim() || '新对话';
    const name = `${baseName}_copy`;

    setBusy(true);
    try {
      const created = await chatConfigsApi.createChat({ ...chatLocked.desiredPayload, name });
      if (!created || !created.id) throw new Error('新建成功，但未返回对话信息');
      setChatLocked(null);
      setChatDetailError('');
      setChatSaveStatus('已复制为新对话');
      await fetchChatList();
      await loadChatDetail(created.id);
    } catch (error) {
      setChatDetailError(error?.message || '复制创建失败');
    } finally {
      setBusy(false);
    }
  }

  async function clearParsedFiles() {
    if (!chatSelected?.id || !canManageChats) return;
    const ok = window.confirm('确认清除该对话的已解析文件绑定？\n\n这将尝试解除 RAGFlow parsed files 的归属限制，以便切换知识库。');
    if (!ok) return;

    setChatDetailError('');
    setChatSaveStatus('');
    setChatLocked(null);
    setBusy(true);
    try {
      await chatConfigsApi.clearParsedFiles(chatSelected.id);
      await fetchChatList();
      await loadChatDetail(chatSelected.id);
      setChatSaveStatus('已尝试清除解析绑定');
    } catch (error) {
      setChatDetailError(error?.message || '清除失败');
    } finally {
      setBusy(false);
    }
  }

  async function deleteChat(chat) {
    if (!chat?.id) return;
    const ok = window.confirm(`确认删除对话: ${chat.name || chat.id}`);
    if (!ok) return;

    setBusy(true);
    try {
      await chatConfigsApi.deleteChat(chat.id);
      if (chatSelected?.id === chat.id) setChatSelected(null);
      await fetchChatList();
    } catch (error) {
      setChatError(error?.message || '删除失败');
    } finally {
      setBusy(false);
    }
  }

  function openCreate() {
    setCreateName('');
    setCreateError('');
    setCreateOpen(true);
  }

  async function createChat() {
    if (!canManageChats) return;
    setCreateError('');

    const name = String(createName || '').trim();
    if (!name) {
      setCreateError('请输入对话名称');
      return;
    }

    setBusy(true);
    try {
      const created = await chatConfigsApi.createChat({ name });
      if (!created || !created.id) throw new Error('新建成功，但未返回对话信息');
      setCreateOpen(false);
      await fetchChatList();
      await loadChatDetail(created.id);
    } catch (error) {
      const message = String(error?.message || '');
      if (message.includes('chat_dataset_not_ready')) {
        setCreateError('所选知识库还没有已解析文档，暂时不能绑定到对话。请先上传并完成解析。');
      } else {
        setCreateError(message || '创建失败');
      }
    } finally {
      setBusy(false);
    }
  }

  return (
    <div
      style={{
        padding: isMobile ? '12px' : '16px',
        display: 'grid',
        gridTemplateColumns: isMobile ? '1fr' : '360px 1fr',
        gap: '14px',
        alignItems: 'start',
      }}
      data-testid="chat-configs-page"
    >
      <ChatConfigListPanel
        panelStyle={panelStyle}
        isMobile={isMobile}
        chatLoading={chatLoading}
        chatListLength={chatList.length}
        canManageChats={canManageChats}
        onOpenCreate={openCreate}
        chatFilter={chatFilter}
        onFilterChange={setChatFilter}
        onRefresh={fetchChatList}
        chatError={chatError}
        filteredChatList={filteredChatList}
        selectedChatId={chatSelected?.id}
        onSelectChat={loadChatDetail}
        onDeleteChat={deleteChat}
        busy={busy}
      />

      <ChatConfigDetailPanel
        panelStyle={panelStyle}
        isMobile={isMobile}
        canManageChats={canManageChats}
        chatSaveStatus={chatSaveStatus}
        onSave={saveChat}
        saveDisabled={!chatSelected?.id || busy || chatDetailLoading}
        chatDetailError={chatDetailError}
        chatLocked={chatLocked}
        onCopyToNewChat={copyToNewChat}
        onSaveNameOnly={saveChatNameOnly}
        onClearParsedFiles={clearParsedFiles}
        busy={busy}
        hasChatSelected={Boolean(chatSelected?.id)}
        chatNameText={chatNameText}
        onChatNameChange={setChatNameText}
        kbLoading={kbLoading}
        kbList={kbList}
        kbError={kbError}
        onRefreshKb={fetchKbList}
        selectedDatasetIds={selectedDatasetIds}
        onToggleDatasetSelection={toggleDatasetSelection}
      />

      <ChatConfigCreateDialog
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        isMobile={isMobile}
        createName={createName}
        onCreateNameChange={setCreateName}
        createError={createError}
        onCreate={createChat}
        isAdmin={canManageChats}
        busy={busy}
      />
    </div>
  );
}

export default ChatConfigsPanel;
