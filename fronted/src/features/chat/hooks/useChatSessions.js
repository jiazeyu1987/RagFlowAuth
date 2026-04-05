import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

import { chatApi } from '../api';

const DEFAULT_SESSION_NAMES = ['\u65b0\u4f1a\u8bdd', '\u65b0\u5bf9\u8bdd', 'new chat'];
const HIDDEN_CHAT_NAMES = new Set(['\u5927\u6a21\u578b', '\u5c0f\u6a21\u578b', '\u95ee\u9898\u6bd4\u5bf9']);

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
  const selectedChatIdRef = useRef(null);
  const fetchSessionsRequestRef = useRef(0);

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
      setError(err?.message || '\u52a0\u8f7d\u804a\u5929\u52a9\u624b\u5931\u8d25');
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchSessions = useCallback(
    async (chatId) => {
      if (!chatId) return;
      const requestedChatId = String(chatId);
      const requestId = fetchSessionsRequestRef.current + 1;
      fetchSessionsRequestRef.current = requestId;
      try {
        const data = await chatApi.listChatSessions(chatId);
        if (fetchSessionsRequestRef.current !== requestId || String(selectedChatIdRef.current || '') !== requestedChatId) {
          return;
        }
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
        if (fetchSessionsRequestRef.current !== requestId || String(selectedChatIdRef.current || '') !== requestedChatId) {
          return;
        }
        setError(err?.message || '\u52a0\u8f7d\u4f1a\u8bdd\u5931\u8d25');
      }
    },
    [restoreSourcesIntoMessages]
  );

  useEffect(() => {
    fetchChats();
  }, [fetchChats]);

  useEffect(() => {
    selectedChatIdRef.current = selectedChatId;
  }, [selectedChatId]);

  useEffect(() => {
    if (selectedChatId) {
      fetchSessions(selectedChatId);
    } else {
      fetchSessionsRequestRef.current += 1;
      setSessions([]);
      setSelectedSessionId(null);
      setMessages([]);
    }
  }, [fetchSessions, selectedChatId]);

  const createSession = useCallback(async () => {
    if (!selectedChatId) return;
    try {
      const sessionName = '\u65b0\u5bf9\u8bdd';
      const session = await chatApi.createChatSession(selectedChatId, sessionName);
      setSessions((prev) => [session, ...prev]);
      setSelectedSessionId(session.id);
      setMessages(restoreSourcesIntoMessages(selectedChatId, session.id, session.messages || []));
    } catch (err) {
      setError(err?.message || '\u65b0\u5efa\u4f1a\u8bdd\u5931\u8d25');
    }
  }, [restoreSourcesIntoMessages, selectedChatId]);

  const selectSession = useCallback(
    (sessionId) => {
      const session = sessions.find((s) => s.id === sessionId);
      if (!session) return;
      setSelectedSessionId(sessionId);
      setMessages(restoreSourcesIntoMessages(selectedChatId, sessionId, session.messages || []));
    },
    [restoreSourcesIntoMessages, selectedChatId, sessions]
  );

  const confirmDeleteSession = useCallback(async () => {
    if (!deleteConfirm.sessionId || !selectedChatId) return;
    try {
      await chatApi.deleteChatSessions(selectedChatId, [deleteConfirm.sessionId]);
      setSessions((prev) => {
        const remaining = prev.filter((s) => s.id !== deleteConfirm.sessionId);
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
      setError(err?.message || '\u5220\u9664\u4f1a\u8bdd\u5931\u8d25');
    }
  }, [deleteConfirm.sessionId, restoreSourcesIntoMessages, selectedChatId, selectedSessionId]);

  const confirmRenameSession = useCallback(async () => {
    if (!renameDialog.sessionId || !selectedChatId) return;
    const newName = String(renameDialog.value || '').trim();
    if (!newName) return;
    try {
      await chatApi.renameChatSession(selectedChatId, renameDialog.sessionId, newName);
      setSessions((prev) => prev.map((s) => (s.id === renameDialog.sessionId ? { ...s, name: newName } : s)));
      setRenameDialog({ show: false, sessionId: null, value: '' });
    } catch (err) {
      setError(err?.message || '\u91cd\u547d\u540d\u5931\u8d25');
    }
  }, [renameDialog.sessionId, renameDialog.value, selectedChatId]);

  const autoRenameSessionByFirstQuestion = useCallback(
    async (question) => {
      if (!selectedChatId || !selectedSessionId) return;
      const target = sessions.find((s) => s.id === selectedSessionId);
      if (!target) return;
      if (!isAutoSessionName(target.name)) return;

      const newName = buildSessionNameFromQuestion(question);
      if (!newName) return;

      try {
        await chatApi.renameChatSession(selectedChatId, selectedSessionId, newName);
        setSessions((prev) => prev.map((s) => (s.id === selectedSessionId ? { ...s, name: newName } : s)));
      } catch {
        // Keep chat flow uninterrupted when rename fails.
      }
    },
    [buildSessionNameFromQuestion, isAutoSessionName, selectedChatId, selectedSessionId, sessions]
  );

  const refreshCurrentSessionMessages = useCallback(async () => {
    if (!selectedChatId || !selectedSessionId) return false;
    try {
      const data = await chatApi.listChatSessions(selectedChatId);
      const list = data.sessions || [];
      setSessions(list);

      const matched = list.find((s) => s.id === selectedSessionId);
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
