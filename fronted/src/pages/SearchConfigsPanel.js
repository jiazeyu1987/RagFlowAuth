import React from 'react';
import ConfigDetailPanel from '../features/knowledge/searchConfigs/components/ConfigDetailPanel';
import ConfigListPanel from '../features/knowledge/searchConfigs/components/ConfigListPanel';
import CreateConfigDialog from '../features/knowledge/searchConfigs/components/CreateConfigDialog';
import useSearchConfigsPanel from '../features/knowledge/searchConfigs/useSearchConfigsPanel';

export function SearchConfigsPanel() {
  const {
    isAdmin,
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
    setCreateMode,
    setCreateName,
    setCreateFromId,
    setCreateJsonText,
    fetchList,
    loadDetail,
    save,
    removeItem,
    openCreate,
    closeCreate,
    syncCreateJsonFromCopy,
    create,
    resetDetailToSelected,
  } = useSearchConfigsPanel();

  return (
    <div
      style={{
        padding: '16px',
        display: 'grid',
        gridTemplateColumns: '360px 1fr',
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
        onClose={closeCreate}
        onChangeMode={(mode) => {
          setCreateMode(mode);
          if (mode === 'blank') {
            setCreateFromId('');
            setCreateJsonText('{}');
          }
        }}
        onChangeName={setCreateName}
        onChangeFromId={(id) => {
          setCreateFromId(id);
          syncCreateJsonFromCopy(id);
        }}
        onChangeJsonText={setCreateJsonText}
        onCreate={create}
      />
    </div>
  );
}

export default SearchConfigsPanel;
