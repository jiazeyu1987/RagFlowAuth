import React, { useCallback, useEffect, useRef, useState } from 'react';
import { ensureTablePreviewStyles } from '../shared/preview/tablePreviewStyles';
import { useEscapeClose } from '../shared/hooks/useEscapeClose';
import documentClient, { DOCUMENT_SOURCE } from '../shared/documents/documentClient';
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
import '../features/chat/chatMedical.css';

const Chat = () => {
  const { canDownload } = useAuth();
  const canDownloadFiles = typeof canDownload === 'function' ? !!canDownload() : false;

  const [inputMessage, setInputMessage] = useState('');
  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewTarget, setPreviewTarget] = useState(null);
  const [citationHover, setCitationHover] = useState(null);

  const messagesEndRef = useRef(null);

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
      console.debug('[对话:引用]', ...args);
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
      debugLogCitations('打开预览', { before_title: source.title, docId: source.docId, dataset: source.dataset });
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
      if (!canDownloadFiles) throw new Error('暂无下载权限');
      await documentClient.downloadToBrowser({
        source: DOCUMENT_SOURCE.RAGFLOW,
        docId: source.docId,
        datasetName: source.dataset,
        filename: source.title,
      });
    },
    [canDownloadFiles]
  );

  const onCitationClick = useCallback((event, { id, chunk }) => {
    const rect = event?.currentTarget?.getBoundingClientRect?.();
    const x = rect ? rect.left + rect.width / 2 : event?.clientX ?? 0;
    const y = rect ? rect.top : event?.clientY ?? 0;
    setCitationHover({
      id,
      chunk: String(chunk || '').trim() || '(未获取到片段内容)',
      x,
      y,
    });
  }, []);

  const onCitationPopupLeave = useCallback(() => {
    setCitationHover(null);
  }, []);

  const handleKeyPress = useCallback(
    (event) => {
      if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        if (selectedChatId && selectedSessionId) {
          sendMessage();
        }
      }
    },
    [selectedChatId, selectedSessionId, sendMessage]
  );

  return (
    <div data-testid="chat-page" className="chat-med-page">
      <ChatSidebar
        loading={loading}
        chats={chats}
        selectedChatId={selectedChatId}
        sessions={sessions}
        selectedSessionId={selectedSessionId}
        onSelectChat={actions.setSelectedChatId}
        onCreateSession={actions.createSession}
        onSelectSession={actions.selectSession}
        onOpenRenameDialog={(session) => actions.setRenameDialog({ show: true, sessionId: session.id, value: session.name || '' })}
        onOpenDeleteDialog={(session) =>
          actions.setDeleteConfirm({
            show: true,
            sessionId: session.id,
            sessionName: session.name || session.id,
          })
        }
      />

      <div data-testid="chat-panel" className="chat-med-card chat-med-panel">
        <div data-testid="chat-header" className="chat-med-header">
          {selectedChatId ? '对话窗口' : '请选择左侧助手开始对话'}
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
          <div data-testid="chat-error" className="chat-med-error">
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
