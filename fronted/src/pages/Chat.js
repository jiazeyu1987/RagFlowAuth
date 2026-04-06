import React from 'react';

import ChatComposer from '../features/chat/components/ChatComposer';
import ChatMessages from '../features/chat/components/ChatMessages';
import ChatSidebar from '../features/chat/components/ChatSidebar';
import CitationTooltip from '../features/chat/components/dialogs/CitationTooltip';
import DeleteSessionDialog from '../features/chat/components/dialogs/DeleteSessionDialog';
import RenameSessionDialog from '../features/chat/components/dialogs/RenameSessionDialog';
import useChatPage from '../features/chat/useChatPage';
import {
  extractCitationIds,
  normalizeSource,
  rewriteCitationLinks,
} from '../features/chat/utils/citationStore';
import { parseThinkSegments } from '../features/chat/utils/thinkParser';
import { documentsApi } from '../features/documents/api';
import { DocumentPreviewModal } from '../shared/documents/preview/DocumentPreviewModal';

const Chat = () => {
  const {
    canDownloadFiles,
    inputMessage,
    previewOpen,
    previewTarget,
    citationHover,
    isMobile,
    messagesEndRef,
    chats,
    selectedChatId,
    sessions,
    selectedSessionId,
    messages,
    loading,
    error,
    deleteConfirm,
    renameDialog,
    setInputMessage,
    setSelectedChatId,
    createSession,
    selectSession,
    setError,
    confirmDeleteSession,
    closeDeleteConfirm,
    confirmRenameSession,
    closeRenameDialog,
    closePreview,
    sendMessage,
    openSourcePreview,
    downloadSource,
    onCitationClick,
    onCitationPopupLeave,
    handleComposerKeyPress,
    openRenameDialog,
    openDeleteDialog,
    setRenameDialogValue,
  } = useChatPage();

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
        onSelectChat={setSelectedChatId}
        onCreateSession={createSession}
        onSelectSession={selectSession}
        onOpenRenameDialog={openRenameDialog}
        onOpenDeleteDialog={openDeleteDialog}
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
          onCreateSession={createSession}
          parseThinkSegments={parseThinkSegments}
          rewriteCitationLinks={rewriteCitationLinks}
          extractCitationIds={extractCitationIds}
          normalizeSource={normalizeSource}
          onCitationClick={onCitationClick}
          openSourcePreview={openSourcePreview}
          downloadSource={downloadSource}
          canDownloadFiles={canDownloadFiles}
          setError={setError}
        />

        {error ? (
          <div
            data-testid="chat-error"
            style={{ padding: '10px 16px', backgroundColor: '#fee2e2', color: '#991b1b' }}
          >
            {error}
          </div>
        ) : null}

        <ChatComposer
          selectedChatId={selectedChatId}
          selectedSessionId={selectedSessionId}
          inputMessage={inputMessage}
          setInputMessage={setInputMessage}
          onKeyPress={handleComposerKeyPress}
          onCreateSession={createSession}
          onSendMessage={sendMessage}
        />
      </div>

      <CitationTooltip citationHover={citationHover} onMouseLeave={onCitationPopupLeave} />

      <DeleteSessionDialog
        open={deleteConfirm.show}
        sessionName={deleteConfirm.sessionName}
        onCancel={closeDeleteConfirm}
        onConfirm={confirmDeleteSession}
      />

      <RenameSessionDialog
        open={renameDialog.show}
        value={renameDialog.value}
        onChangeValue={setRenameDialogValue}
        onCancel={closeRenameDialog}
        onConfirm={confirmRenameSession}
      />

      <DocumentPreviewModal
        open={previewOpen}
        target={previewTarget}
        onClose={closePreview}
        canDownloadFiles={canDownloadFiles}
        documentApi={documentsApi}
      />
    </div>
  );
};

export default Chat;
