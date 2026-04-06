import { useCallback, useEffect, useMemo, useState } from 'react';
import { chatConfigsApi } from './api';
import { knowledgeApi } from '../../knowledge/api';
import { useAuth } from '../../../hooks/useAuth';
import {
  getDatasetIdsKeyForUpdate,
  getSelectedDatasetIdsFromChatJson,
  HIDDEN_CHAT_NAMES,
  parseJson,
  prettyJson,
  sanitizeChatPayload,
} from './chatConfigUtils';

const MOBILE_BREAKPOINT = 768;

const DATASET_NOT_READY_ERROR =
  '所选知识库还没有已解析文档，暂时不能绑定到对话。请先上传并完成解析。';

const DATASET_LOCKED_ERROR =
  '该对话已关联已解析文档，当前不允许直接切换到不包含这些文档的知识库。可以先复制为新对话，再调整知识库。';

const getInitialIsMobile = () => {
  if (typeof window === 'undefined') return false;
  return window.innerWidth <= MOBILE_BREAKPOINT;
};

const getVisibleChats = (chats) =>
  (Array.isArray(chats) ? chats : []).filter((chat) => {
    const rawName = String(chat?.name || '').trim();
    const normalized = rawName.replace(/^\[|\]$/g, '').trim();
    return !HIDDEN_CHAT_NAMES.has(rawName) && !HIDDEN_CHAT_NAMES.has(normalized);
  });

export default function useChatConfigsPanelPage() {
  const { user } = useAuth();
  const canManageChats = ['admin', 'sub_admin'].includes(String(user?.role || ''));
  const [isMobile, setIsMobile] = useState(getInitialIsMobile);
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

  const fetchChatList = useCallback(async () => {
    setChatError('');
    setChatLoading(true);
    try {
      const chats = await chatConfigsApi.listChats({ page_size: 1000 });
      setChatList(getVisibleChats(chats));
    } catch (error) {
      setChatList([]);
      setChatError(error?.message || '加载对话列表失败');
    } finally {
      setChatLoading(false);
    }
  }, []);

  const fetchKbList = useCallback(async () => {
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
  }, []);

  const loadChatDetail = useCallback(async (chatId) => {
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
  }, []);

  const toggleDatasetSelection = useCallback(
    (datasetId) => {
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

      const nextObject = sanitizeChatPayload({
        ...parsed.value,
        [key]: Array.from(nextSet),
      });
      setChatJsonText(prettyJson(nextObject));
    },
    [canManageChats, chatJsonText]
  );

  useEffect(() => {
    fetchChatList();
    fetchKbList();
  }, [fetchChatList, fetchKbList]);

  useEffect(() => {
    if (!chatSelected && chatList.length) {
      loadChatDetail(chatList[0]?.id || '');
    }
  }, [chatList, chatSelected, loadChatDetail]);

  const saveChat = useCallback(async () => {
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
      if (!updated || !updated.id) {
        throw new Error('保存成功，但未返回最新配置');
      }

      setChatSelected(updated);
      setChatNameText(String(updated?.name || name));
      setChatJsonText(prettyJson(sanitizeChatPayload(updated)));
      setChatSaveStatus('已保存');
      await fetchChatList();

    } catch (error) {
      const message = String(error?.message || '');
      if (message.includes('chat_dataset_not_ready')) {
        setChatLocked(null);
        setChatDetailError(DATASET_NOT_READY_ERROR);
      } else if (
        message.includes('chat_dataset_locked') ||
        message.includes("doesn't own parsed file")
      ) {
        setChatLocked({ message, desiredPayload: updates });
        setChatDetailError(DATASET_LOCKED_ERROR);
      } else {
        setChatDetailError(message || '保存失败');
      }
    } finally {
      setBusy(false);
    }
  }, [chatJsonText, chatNameText, chatSelected, fetchChatList]);

  const saveChatNameOnly = useCallback(async () => {
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
      if (!updated || !updated.id) {
        throw new Error('保存成功，但未返回最新配置');
      }
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
  }, [chatNameText, chatSelected, fetchChatList]);

  const copyToNewChat = useCallback(async () => {
    if (!canManageChats || !chatLocked?.desiredPayload) return;
    const baseName =
      String(chatNameText || chatSelected?.name || '新对话').trim() || '新对话';
    const name = `${baseName}_copy`;

    setBusy(true);
    try {
      const created = await chatConfigsApi.createChat({
        ...chatLocked.desiredPayload,
        name,
      });
      if (!created || !created.id) {
        throw new Error('新建成功，但未返回对话信息');
      }
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
  }, [canManageChats, chatLocked, chatNameText, chatSelected?.name, fetchChatList, loadChatDetail]);

  const clearParsedFiles = useCallback(async () => {
    if (!chatSelected?.id || !canManageChats) return;
    const confirmed = window.confirm(
      '确认清除该对话的已解析文件绑定？\n\n这将尝试解除 RAGFlow parsed files 的归属限制，以便切换知识库。'
    );
    if (!confirmed) return;

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
  }, [canManageChats, chatSelected?.id, fetchChatList, loadChatDetail]);

  const deleteChat = useCallback(
    async (chat) => {
      if (!chat?.id) return;
      const confirmed = window.confirm(`确认删除对话: ${chat.name || chat.id}`);
      if (!confirmed) return;

      setBusy(true);
      try {
        await chatConfigsApi.deleteChat(chat.id);
        if (chatSelected?.id === chat.id) {
          setChatSelected(null);
        }
        await fetchChatList();
      } catch (error) {
        setChatError(error?.message || '删除失败');
      } finally {
        setBusy(false);
      }
    },
    [chatSelected?.id, fetchChatList]
  );

  const openCreate = useCallback(() => {
    setCreateName('');
    setCreateError('');
    setCreateOpen(true);
  }, []);

  const createChat = useCallback(async () => {
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
      if (!created || !created.id) {
        throw new Error('新建成功，但未返回对话信息');
      }
      setCreateOpen(false);
      await fetchChatList();
      await loadChatDetail(created.id);
    } catch (error) {
      const message = String(error?.message || '');
      if (message.includes('chat_dataset_not_ready')) {
        setCreateError(DATASET_NOT_READY_ERROR);
      } else {
        setCreateError(message || '创建失败');
      }
    } finally {
      setBusy(false);
    }
  }, [canManageChats, createName, fetchChatList, loadChatDetail]);

  return {
    canManageChats,
    isMobile,
    chatList,
    chatLoading,
    chatError,
    chatFilter,
    chatSelected,
    chatDetailLoading,
    chatDetailError,
    chatNameText,
    chatSaveStatus,
    chatLocked,
    busy,
    createOpen,
    createName,
    createError,
    kbList,
    kbLoading,
    kbError,
    filteredChatList,
    selectedDatasetIds,
    setChatFilter,
    setChatNameText,
    setCreateName,
    setCreateOpen,
    fetchChatList,
    fetchKbList,
    loadChatDetail,
    saveChat,
    saveChatNameOnly,
    copyToNewChat,
    clearParsedFiles,
    deleteChat,
    openCreate,
    createChat,
    toggleDatasetSelection,
  };
}
