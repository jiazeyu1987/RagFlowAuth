import React from 'react';
import ChatConfigCreateDialog from '../features/chat/configs/components/ChatConfigCreateDialog';
import ChatConfigDetailPanel from '../features/chat/configs/components/ChatConfigDetailPanel';
import ChatConfigListPanel from '../features/chat/configs/components/ChatConfigListPanel';
import useChatConfigsPanelPage from '../features/chat/configs/useChatConfigsPanelPage';

const panelStyle = {
  background: '#ffffff',
  border: '1px solid #e5e7eb',
  borderRadius: '12px',
  overflow: 'hidden',
  boxShadow: '0 6px 18px rgba(15, 23, 42, 0.06)',
};

export function ChatConfigsPanel() {
  const {
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
  } = useChatConfigsPanelPage();

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
