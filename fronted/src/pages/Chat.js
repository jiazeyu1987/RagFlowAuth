import React, { useCallback, useEffect, useRef, useState } from 'react';
import { ensureTablePreviewStyles } from '../shared/preview/tablePreviewStyles';
import { useEscapeClose } from '../shared/hooks/useEscapeClose';
import { DOCUMENT_SOURCE, documentsApi } from '../features/documents/api';
import { useAuth } from '../hooks/useAuth';
import { DocumentPreviewModal } from '../shared/documents/preview/DocumentPreviewModal';
import ChatSidebar from '../features/chat/components/ChatSidebar';
import ChatMessages from '../features/chat/components/ChatMessages';
import ChatComposer from '../features/chat/components/ChatComposer';
import DeleteSessionDialog from '../features/chat/components/dialogs/DeleteSessionDialog';
import RenameSessionDialog from '../features/chat/components/dialogs/RenameSessionDialog';
import CitationTooltip from '../features/chat/components/dialogs/CitationTooltip';
import {
  normalizeForCompare,
  containsReasoningMarkers,
  stripThinkTags,
  parseThinkSegments,
} from '../features/chat/utils/thinkParser';
import {
  extractCitationIds,
  normalizeSource,
  rewriteCitationLinks,
  saveSourcesForAssistantMessage,
  restoreSourcesIntoMessages,
} from '../features/chat/utils/citationStore';
import { useChatSessions } from '../features/chat/hooks/useChatSessions';
import { useChatStream } from '../features/chat/hooks/useChatStream';

const MOBILE_BREAKPOINT = 768;

const Chat = () => {
  const { canDownload } = useAuth();
  const canDownloadFiles = typeof canDownload === 'function' ? !!canDownload() : false;

  const [inputMessage, setInputMessage] = useState('');
  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewTarget, setPreviewTarget] = useState(null);
  const [citationHover, setCitationHover] = useState(null);
  const [isMobile, setIsMobile] = useState(() => {
    if (typeof window === 'undefined') return false;
    return window.innerWidth <= MOBILE_BREAKPOINT;
  });

  const messagesEndRef = useRef(null);

  useEffect(() => {
    if (typeof window === 'undefined') return undefined;

    const handleResize = () => {
      setIsMobile(window.innerWidth <= MOBILE_BREAKPOINT);
    };

    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const closePreview = useCallback(() => {
    setPreviewOpen(false);
    setPreviewTarget(null);
  }, []);

  const debugChatCitations = useCallback(() => {
    try {
      return String(window?.localStorage?.getItem('RAGFLOWAUTH_DEBUG_CHAT_CITATIONS') || '') === '1';
    } catch {
      return false;
    }
  }, []);

  const debugLogCitations = useCallback(
    (...args) => {
      if (!debugChatCitations()) return;
      console.debug('[Chat:Citations]', ...args);
    },
    [debugChatCitations]
  );

  const restoreSourcesForSession = useCallback(
    (chatId, sessionId, messageList) => restoreSourcesIntoMessages(chatId, sessionId, messageList, stripThinkTags),
    []
  );

  const {
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
  } = useChatSessions({
    restoreSourcesIntoMessages: restoreSourcesForSession,
  });

  const { sendMessage } = useChatStream({
    selectedChatId,
    selectedSessionId,
    inputMessage,
    setInputMessage,
    messages,
    setMessages: actions.setMessages,
    setError: actions.setError,
    autoRenameSessionByFirstQuestion: actions.autoRenameSessionByFirstQuestion,
    normalizeForCompare,
    containsReasoningMarkers,
    stripThinkTags,
    saveSourcesForAssistantMessage: (chatId, sessionId, content, sources) =>
      saveSourcesForAssistantMessage(chatId, sessionId, content, sources, debugLogCitations),
    debugLogCitations,
    normalizeSource,
    refreshSessionMessages: actions.refreshCurrentSessionMessages,
  });

  useEscapeClose(deleteConfirm.show, actions.closeDeleteConfirm);
  useEscapeClose(renameDialog.show, actions.closeRenameDialog);
  useEscapeClose(previewOpen, closePreview);

  useEffect(() => {
    ensureTablePreviewStyles();
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const openSourcePreview = useCallback(
    async (rawSource) => {
      const source = normalizeSource(rawSource);
      if (!source.docId || !source.dataset) return;
      debugLogCitations('preview open', { before_title: source.title, docId: source.docId, dataset: source.dataset });
      setPreviewTarget({
        source: DOCUMENT_SOURCE.RAGFLOW,
        docId: source.docId,
        datasetName: source.dataset,
        filename: source.title,
      });
      setPreviewOpen(true);
    },
    [debugLogCitations]
  );

  const downloadSource = useCallback(
    async (rawSource) => {
      const source = normalizeSource(rawSource);
      if (!source.docId || !source.dataset) return;
      if (!canDownloadFiles) throw new Error('no_download_permission');
      await documentsApi.downloadToBrowser({
        source: DOCUMENT_SOURCE.RAGFLOW,
        docId: source.docId,
        datasetName: source.dataset,
        filename: source.title,
      });
    },
    [canDownloadFiles]
  );

  const onCitationClick = useCallback((e, { id, chunk }) => {
    const rect = e?.currentTarget?.getBoundingClientRect?.();
    const x = rect ? rect.left + rect.width / 2 : e?.clientX ?? 0;
    const y = rect ? rect.top : e?.clientY ?? 0;
    console.debug('[Chat:CitationPopup] open', { id, chunkLen: String(chunk || '').length, x, y });
    setCitationHover({
      id,
      chunk: String(chunk || '').trim() || '(未获取到chunk内容)',
      x,
      y,
    });
  }, []);

  const onCitationPopupLeave = useCallback(() => {
    console.debug('[Chat:CitationPopup] close');
    setCitationHover(null);
  }, []);

  const handleKeyPress = useCallback(
    (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        if (selectedChatId && selectedSessionId) {
          sendMessage();
        }
      }
    },
    [selectedChatId, selectedSessionId, sendMessage]
  );

  return (
    <div
      data-testid="chat-page"
      style={{
        height: isMobile ? 'auto' : 'calc(100vh - 120px)',
        minHeight: isMobile ? 'calc(100vh - 160px)' : undefined,
        display: 'flex',
        flexDirection: isMobile ? 'column' : 'row',
        gap: isMobile ? '12px' : '16px',
      }}
    >
      <ChatSidebar
        loading={loading}
        chats={chats}
        selectedChatId={selectedChatId}
        sessions={sessions}
        selectedSessionId={selectedSessionId}
        onSelectChat={actions.setSelectedChatId}
        onCreateSession={actions.createSession}
        onSelectSession={actions.selectSession}
        onOpenRenameDialog={(s) => actions.setRenameDialog({ show: true, sessionId: s.id, value: s.name || '' })}
        onOpenDeleteDialog={(s) =>
          actions.setDeleteConfirm({
            show: true,
            sessionId: s.id,
            sessionName: s.name || s.id,
          })
        }
      />

      <div
        data-testid="chat-panel"
        style={{
          backgroundColor: 'white',
          borderRadius: isMobile ? '12px' : '8px',
          boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
          flex: 1,
          minWidth: 0,
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
          minHeight: isMobile ? '58vh' : 0,
        }}
      >
        <div
          data-testid="chat-header"
          style={{
            padding: isMobile ? '12px 14px' : '14px 16px',
            borderBottom: '1px solid #e5e7eb',
            fontWeight: 600,
            fontSize: isMobile ? '0.95rem' : '1rem',
          }}
        >
          {selectedChatId ? '对话' : '请选择聊天助手开始对话'}
        </div>

        <ChatMessages
          messagesEndRef={messagesEndRef}
          selectedChatId={selectedChatId}
          selectedSessionId={selectedSessionId}
          messages={messages}
          onCreateSession={actions.createSession}
          parseThinkSegments={parseThinkSegments}
          rewriteCitationLinks={rewriteCitationLinks}
          extractCitationIds={extractCitationIds}
          normalizeSource={normalizeSource}
          onCitationClick={onCitationClick}
          openSourcePreview={openSourcePreview}
          downloadSource={downloadSource}
          canDownloadFiles={canDownloadFiles}
          setError={actions.setError}
        />

        {error && (
          <div data-testid="chat-error" style={{ padding: '10px 16px', backgroundColor: '#fee2e2', color: '#991b1b' }}>
            {error}
          </div>
        )}

        <ChatComposer
          selectedChatId={selectedChatId}
          selectedSessionId={selectedSessionId}
          inputMessage={inputMessage}
          setInputMessage={setInputMessage}
          onKeyPress={handleKeyPress}
          onCreateSession={actions.createSession}
          onSendMessage={sendMessage}
        />
      </div>

      <CitationTooltip citationHover={citationHover} onMouseLeave={onCitationPopupLeave} />

      <DeleteSessionDialog
        open={deleteConfirm.show}
        sessionName={deleteConfirm.sessionName}
        onCancel={actions.closeDeleteConfirm}
        onConfirm={actions.confirmDeleteSession}
      />

      <RenameSessionDialog
        open={renameDialog.show}
        value={renameDialog.value}
        onChangeValue={(value) => actions.setRenameDialog((prev) => ({ ...prev, value }))}
        onCancel={actions.closeRenameDialog}
        onConfirm={actions.confirmRenameSession}
      />

      <DocumentPreviewModal open={previewOpen} target={previewTarget} onClose={closePreview} canDownloadFiles={canDownloadFiles} />
    </div>
  );
};

export default Chat;
