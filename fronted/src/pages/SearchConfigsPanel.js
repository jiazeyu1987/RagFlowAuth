import React from 'react';

import ConfigDetailPanel from '../features/knowledge/searchConfigs/components/ConfigDetailPanel';
import ConfigListPanel from '../features/knowledge/searchConfigs/components/ConfigListPanel';
import CreateConfigDialog from '../features/knowledge/searchConfigs/components/CreateConfigDialog';
import useSearchConfigsPanelPage from '../features/knowledge/searchConfigs/useSearchConfigsPanelPage';

export function SearchConfigsPanel() {
  const {
    isAdmin,
    isMobile,
    list,
    loading,
    error,
    filter,
    filteredList,
    selected,
    detailLoading,
    detailError,
    nameText,
    jsonText,
    saveStatus,
    busy,
    createOpen,
    createMode,
    createName,
    createFromId,
    createJsonText,
    createError,
    setFilter,
    setNameText,
    setJsonText,
    setCreateName,
    setCreateJsonText,
    fetchList,
    loadDetail,
    save,
    removeItem,
    openCreate,
    closeCreate,
    create,
    resetDetailToSelected,
    handleCreateModeChange,
    handleCreateSourceChange,
  } = useSearchConfigsPanelPage();

  return (
    <div
      data-testid="search-configs-page"
      style={{
        padding: isMobile ? '12px' : '16px',
        display: 'grid',
        gridTemplateColumns: isMobile ? '1fr' : '360px 1fr',
        gap: '14px',
        alignItems: 'start',
      }}
    >
      <ConfigListPanel
        list={list}
        filteredList={filteredList}
        selectedId={selected?.id}
        filter={filter}
        loading={loading}
        error={error}
        busy={busy}
        isAdmin={isAdmin}
        isMobile={isMobile}
        onChangeFilter={setFilter}
        onOpenCreate={openCreate}
        onRefresh={fetchList}
        onSelect={loadDetail}
        onDelete={removeItem}
      />

      <ConfigDetailPanel
        selected={selected}
        detailLoading={detailLoading}
        detailError={detailError}
        nameText={nameText}
        jsonText={jsonText}
        saveStatus={saveStatus}
        busy={busy}
        isAdmin={isAdmin}
        isMobile={isMobile}
        onChangeName={setNameText}
        onChangeJson={setJsonText}
        onReset={resetDetailToSelected}
        onSave={save}
      />

      <CreateConfigDialog
        open={createOpen}
        list={list}
        busy={busy}
        mode={createMode}
        name={createName}
        fromId={createFromId}
        jsonText={createJsonText}
        error={createError}
        isMobile={isMobile}
        onClose={closeCreate}
        onChangeMode={handleCreateModeChange}
        onChangeName={setCreateName}
        onChangeFromId={handleCreateSourceChange}
        onChangeJsonText={setCreateJsonText}
        onCreate={create}
      />
    </div>
  );
}

export default SearchConfigsPanel;
