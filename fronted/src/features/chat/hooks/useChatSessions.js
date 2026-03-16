import { useCallback, useEffect, useMemo, useState } from 'react';
import { chatApi } from '../api';
import { normalizeDisplayError } from '../../../shared/utils/displayError';

const DEFAULT_SESSION_NAMES = ['新会话', '新对话'];
const HIDDEN_CHAT_NAMES = new Set(['大模型', '小模型', '问题比对']);

export const useChatSessions = ({ restoreSourcesIntoMessages }) => {
  const [chats, setChats] = useState([]);
  const [selectedChatId, setSelectedChatId] = useState(null);
  const [sessions, setSessions] = useState([]);
  const [selectedSessionId, setSelectedSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [deleteConfirm, setDeleteConfirm] = useState({ show: false, sessionId: null, sessionName: '' });
  const [renameDialog, setRenameDialog] = useState({ show: false, sessionId: null, value: '' });

  const closeDeleteConfirm = useCallback(() => {
    setDeleteConfirm({ show: false, sessionId: null, sessionName: '' });
  }, []);

  const closeRenameDialog = useCallback(() => {
    setRenameDialog({ show: false, sessionId: null, value: '' });
  }, []);

  const normalizeSessionName = useCallback((value) => String(value || '').trim().toLowerCase(), []);

  const isAutoSessionName = useCallback(
    (sessionName) => {
      const normalized = normalizeSessionName(sessionName);
      if (!normalized) return true;
      return DEFAULT_SESSION_NAMES.includes(normalized);
    },
    [normalizeSessionName]
  );

  const buildSessionNameFromQuestion = useCallback((question) => {
    const oneLine = String(question || '').replace(/\s+/g, ' ').trim();
    if (!oneLine) return '';
    return oneLine.slice(0, 40);
  }, []);

  const fetchChats = useCallback(async () => {
    try {
      setLoading(true);
      const data = await chatApi.listMyChats();
      const list = (data.chats || []).filter((chat) => {
        const rawName = String(chat?.name || '').trim();
        const normalized = rawName.replace(/^\[|\]$/g, '').trim();
        return !HIDDEN_CHAT_NAMES.has(rawName) && !HIDDEN_CHAT_NAMES.has(normalized);
      });
      setChats(list);
      if (list.length > 0) {
        setSelectedChatId(list[0].id);
      } else {
        setSelectedChatId(null);
      }
    } catch (err) {
      setError(normalizeDisplayError(err?.message ?? err, '加载聊天助手失败'));
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchSessions = useCallback(async (chatId) => {
    if (!chatId) return;
    try {
      const data = await chatApi.listChatSessions(chatId);
      const list = data.sessions || [];
      setSessions(list);
      if (list.length > 0) {
        setSelectedSessionId(list[0].id);
        setMessages(restoreSourcesIntoMessages(chatId, list[0].id, list[0].messages || []));
      } else {
        setSelectedSessionId(null);
        setMessages([]);
      }
    } catch (err) {
      setError(normalizeDisplayError(err?.message ?? err, '加载会话失败'));
    }
  }, [restoreSourcesIntoMessages]);

  useEffect(() => {
    fetchChats();
  }, [fetchChats]);

  useEffect(() => {
    if (selectedChatId) {
      fetchSessions(selectedChatId);
    } else {
      setSessions([]);
      setSelectedSessionId(null);
      setMessages([]);
    }
  }, [fetchSessions, selectedChatId]);

  const createSession = useCallback(async () => {
    if (!selectedChatId) return;
    try {
      const sessionName = '新对话';
      const session = await chatApi.createChatSession(selectedChatId, sessionName);
      setSessions((prev) => [session, ...prev]);
      setSelectedSessionId(session.id);
      setMessages(restoreSourcesIntoMessages(selectedChatId, session.id, session.messages || []));
    } catch (err) {
      setError(normalizeDisplayError(err?.message ?? err, '新建会话失败'));
    }
  }, [restoreSourcesIntoMessages, selectedChatId]);

  const selectSession = useCallback((sessionId) => {
    const session = sessions.find((item) => item.id === sessionId);
    if (!session) return;
    setSelectedSessionId(sessionId);
    setMessages(restoreSourcesIntoMessages(selectedChatId, sessionId, session.messages || []));
  }, [restoreSourcesIntoMessages, selectedChatId, sessions]);

  const confirmDeleteSession = useCallback(async () => {
    if (!deleteConfirm.sessionId || !selectedChatId) return;
    try {
      await chatApi.deleteChatSessions(selectedChatId, [deleteConfirm.sessionId]);
      setSessions((prev) => {
        const remaining = prev.filter((item) => item.id !== deleteConfirm.sessionId);
        if (selectedSessionId === deleteConfirm.sessionId) {
          if (remaining.length > 0) {
            setSelectedSessionId(remaining[0].id);
            setMessages(restoreSourcesIntoMessages(selectedChatId, remaining[0].id, remaining[0].messages || []));
          } else {
            setSelectedSessionId(null);
            setMessages([]);
          }
        }
        return remaining;
      });
      setDeleteConfirm({ show: false, sessionId: null, sessionName: '' });
    } catch (err) {
      setError(normalizeDisplayError(err?.message ?? err, '删除会话失败'));
    }
  }, [deleteConfirm.sessionId, restoreSourcesIntoMessages, selectedChatId, selectedSessionId]);

  const confirmRenameSession = useCallback(async () => {
    if (!renameDialog.sessionId || !selectedChatId) return;
    const newName = String(renameDialog.value || '').trim();
    if (!newName) return;
    try {
      await chatApi.renameChatSession(selectedChatId, renameDialog.sessionId, newName);
      setSessions((prev) => prev.map((item) => (item.id === renameDialog.sessionId ? { ...item, name: newName } : item)));
      setRenameDialog({ show: false, sessionId: null, value: '' });
    } catch (err) {
      setError(normalizeDisplayError(err?.message ?? err, '重命名失败'));
    }
  }, [renameDialog.sessionId, renameDialog.value, selectedChatId]);

  const autoRenameSessionByFirstQuestion = useCallback(async (question) => {
    if (!selectedChatId || !selectedSessionId) return;
    const target = sessions.find((item) => item.id === selectedSessionId);
    if (!target) return;
    if (!isAutoSessionName(target.name)) return;

    const newName = buildSessionNameFromQuestion(question);
    if (!newName) return;

    try {
      await chatApi.renameChatSession(selectedChatId, selectedSessionId, newName);
      setSessions((prev) => prev.map((item) => (item.id === selectedSessionId ? { ...item, name: newName } : item)));
    } catch {
      // Rename failures should not interrupt normal chat flow.
    }
  }, [buildSessionNameFromQuestion, isAutoSessionName, selectedChatId, selectedSessionId, sessions]);

  const refreshCurrentSessionMessages = useCallback(async () => {
    if (!selectedChatId || !selectedSessionId) return false;
    try {
      const data = await chatApi.listChatSessions(selectedChatId);
      const list = data.sessions || [];
      setSessions(list);

      const matched = list.find((item) => item.id === selectedSessionId);
      const target = matched || list[0];
      if (!target) return false;

      setSelectedSessionId(target.id);
      setMessages(restoreSourcesIntoMessages(selectedChatId, target.id, target.messages || []));
      return true;
    } catch {
      return false;
    }
  }, [restoreSourcesIntoMessages, selectedChatId, selectedSessionId]);

  const actions = useMemo(
    () => ({
      fetchChats,
      fetchSessions,
      createSession,
      selectSession,
      confirmDeleteSession,
      confirmRenameSession,
      closeDeleteConfirm,
      closeRenameDialog,
      autoRenameSessionByFirstQuestion,
      refreshCurrentSessionMessages,
      setDeleteConfirm,
      setRenameDialog,
      setSelectedChatId,
      setMessages,
      setError,
    }),
    [
      autoRenameSessionByFirstQuestion,
      closeDeleteConfirm,
      closeRenameDialog,
      confirmDeleteSession,
      confirmRenameSession,
      createSession,
      fetchChats,
      fetchSessions,
      refreshCurrentSessionMessages,
      selectSession,
    ]
  );

  return {
    chats,
    selectedChatId,
    sessions,
    selectedSessionId,
    messages,
    loading,
    error,
    deleteConfirm,
    renameDialog,
    actions,
  };
};
