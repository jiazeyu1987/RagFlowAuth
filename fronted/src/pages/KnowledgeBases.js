import React from 'react';

import CreateKnowledgeBaseDialog from '../features/knowledge/knowledgeBases/components/CreateKnowledgeBaseDialog';
import DirectoryTreeView from '../features/knowledge/knowledgeBases/components/DirectoryTreeView';
import useKnowledgeBasesPage from '../features/knowledge/knowledgeBases/useKnowledgeBasesPage';
import { ChatConfigsPanel } from './ChatConfigsPanel';

const getSubtabButtonStyle = (active) => ({
  border: `1px solid ${active ? '#1d4ed8' : '#e5e7eb'}`,
  borderRadius: 10,
  background: active ? '#1d4ed8' : '#fff',
  color: active ? '#fff' : '#111827',
  cursor: 'pointer',
  padding: '9px 12px',
  fontWeight: 700,
});

export default function KnowledgeBases() {
  const {
    ROOT,
    subtab,
    isMobile,
    kbList,
    kbError,
    treeError,
    kbBusy,
    kbSaveStatus,
    currentDirId,
    selectedNodeId,
    expanded,
    keyword,
    selectedItem,
    dragDatasetId,
    dropTargetNodeId,
    kbNameText,
    datasetDirId,
    createOpen,
    createName,
    createFromId,
    createDirId,
    createError,
    canManageDirectory,
    canManageDatasets,
    indexes,
    breadcrumb,
    dirOptions,
    filteredRows,
    canDeleteSelectedKb,
    showSelectedDatasetDetails,
    setSubtab,
    setKeyword,
    setKbNameText,
    setDatasetDirId,
    setCreateName,
    setCreateDirId,
    refreshAll,
    saveKb,
    createDirectory,
    renameDirectory,
    deleteDirectory,
    openCreateKb,
    closeCreateKb,
    createKb,
    handleCreateFromIdChange,
    handleToggleExpanded,
    handleTreeNodeOpen,
    handleOpenBreadcrumb,
    handleGoParent,
    handleSelectRow,
    handleDoubleClickRow,
    handleDatasetDragStart,
    handleDatasetDragEnd,
    handleDeleteSelectedKb,
    handleTreeDragOver,
    handleTreeDrop,
    handleTreeDragLeave,
  } = useKnowledgeBasesPage();

  return (
    <div style={{ padding: isMobile ? 10 : 14 }}>
      <div style={{ marginBottom: 10, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
        <button
          data-testid="kbs-subtab-kbs"
          onClick={() => setSubtab('kbs')}
          style={getSubtabButtonStyle(subtab === 'kbs')}
        >
          知识配置
        </button>
        <button
          data-testid="kbs-subtab-chats"
          onClick={() => setSubtab('chats')}
          style={getSubtabButtonStyle(subtab === 'chats')}
        >
          对话配置
        </button>
      </div>

      {subtab === 'kbs' ? (
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: isMobile ? '1fr' : '320px 1fr',
            gap: 14,
          }}
        >
          <section style={{ border: '1px solid #e5e7eb', borderRadius: 12, background: '#fff' }}>
            <div
              style={{
                padding: '10px 12px',
                borderBottom: '1px solid #e5e7eb',
                fontWeight: 800,
              }}
            >
              目录树
            </div>
            <div style={{ padding: 12, maxHeight: isMobile ? 280 : 720, overflowY: 'auto' }}>
              {treeError ? <div style={{ color: '#b91c1c', marginBottom: 8 }}>{treeError}</div> : null}
              <DirectoryTreeView
                indexes={indexes}
                currentDirId={currentDirId}
                selectedNodeId={selectedNodeId}
                expanded={expanded}
                onToggle={handleToggleExpanded}
                onOpen={handleTreeNodeOpen}
                dropTargetNodeId={canManageDirectory ? dropTargetNodeId : null}
                onDragOverNode={handleTreeDragOver}
                onDropNode={handleTreeDrop}
                onDragLeaveNode={handleTreeDragLeave}
                allowDatasetDrop={canManageDirectory}
              />
            </div>
          </section>

          <section style={{ border: '1px solid #e5e7eb', borderRadius: 12, background: '#fff' }}>
            <div style={{ padding: '10px 12px', borderBottom: '1px solid #e5e7eb' }}>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 10 }}>
                <button
                  data-testid="kbs-refresh-all"
                  onClick={refreshAll}
                  style={{
                    border: '1px solid #d1d5db',
                    borderRadius: 8,
                    background: '#fff',
                    cursor: 'pointer',
                    padding: '6px 9px',
                  }}
                >
                  刷新
                </button>
                <button
                  data-testid="kbs-go-parent"
                  onClick={handleGoParent}
                  disabled={currentDirId === ROOT}
                  style={{
                    border: '1px solid #d1d5db',
                    borderRadius: 8,
                    background: currentDirId === ROOT ? '#f3f4f6' : '#fff',
                    cursor: currentDirId === ROOT ? 'not-allowed' : 'pointer',
                    padding: '6px 9px',
                  }}
                >
                  返回上级
                </button>
                {canManageDirectory ? (
                  <>
                    <button
                      data-testid="kbs-create-dir"
                      onClick={createDirectory}
                      style={{
                        border: '1px solid #2563eb',
                        borderRadius: 8,
                        background: '#2563eb',
                        color: '#fff',
                        cursor: 'pointer',
                        padding: '6px 9px',
                      }}
                    >
                      新建目录
                    </button>
                    <button
                      data-testid="kbs-rename-dir"
                      onClick={renameDirectory}
                      disabled={!selectedNodeId || selectedNodeId === ROOT}
                      style={{
                        border: '1px solid #f59e0b',
                        borderRadius: 8,
                        background:
                          !selectedNodeId || selectedNodeId === ROOT ? '#fde68a' : '#f59e0b',
                        color: '#fff',
                        cursor:
                          !selectedNodeId || selectedNodeId === ROOT ? 'not-allowed' : 'pointer',
                        padding: '6px 9px',
                      }}
                    >
                      重命名目录
                    </button>
                    <button
                      data-testid="kbs-delete-dir"
                      onClick={deleteDirectory}
                      disabled={!selectedNodeId || selectedNodeId === ROOT}
                      style={{
                        border: '1px solid #ef4444',
                        borderRadius: 8,
                        background:
                          !selectedNodeId || selectedNodeId === ROOT ? '#fecaca' : '#ef4444',
                        color: '#fff',
                        cursor:
                          !selectedNodeId || selectedNodeId === ROOT ? 'not-allowed' : 'pointer',
                        padding: '6px 9px',
                      }}
                    >
                      删除目录
                    </button>
                  </>
                ) : null}
                {canManageDatasets ? (
                  <button
                    data-testid="kbs-create-kb"
                    onClick={openCreateKb}
                    style={{
                      border: '1px solid #059669',
                      borderRadius: 8,
                      background: '#10b981',
                      color: '#fff',
                      cursor: 'pointer',
                      padding: '6px 9px',
                    }}
                  >
                    新建知识库
                  </button>
                ) : null}
              </div>

              <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 10 }}>
                <span style={{ color: '#6b7280', fontSize: 13 }}>路径:</span>
                {breadcrumb.map((item, index) => (
                  <React.Fragment key={item.id || '__root__'}>
                    <button
                      type="button"
                      onClick={() => handleOpenBreadcrumb(item.id)}
                      style={{
                        border: 'none',
                        background: 'transparent',
                        cursor: 'pointer',
                        color: currentDirId === item.id ? '#1d4ed8' : '#374151',
                        fontWeight: currentDirId === item.id ? 700 : 500,
                        padding: 0,
                      }}
                    >
                      {item.name}
                    </button>
                    {index < breadcrumb.length - 1 ? (
                      <span style={{ color: '#9ca3af' }}>&gt;</span>
                    ) : null}
                  </React.Fragment>
                ))}
              </div>

              <input
                value={keyword}
                onChange={(event) => setKeyword(event.target.value)}
                placeholder="筛选当前目录内容"
                style={{
                  width: isMobile ? '100%' : 320,
                  maxWidth: '100%',
                  border: '1px solid #d1d5db',
                  borderRadius: 8,
                  padding: '8px 10px',
                  boxSizing: 'border-box',
                }}
              />
              {canManageDirectory ? (
                <div data-testid="kbs-drag-tip" style={{ marginTop: 6, color: '#6b7280', fontSize: 12 }}>
                  支持拖拽：将右侧“知识库”行拖到左侧任意目录，可快速移动挂载位置。
                </div>
              ) : null}
              {kbError ? <div style={{ color: '#b91c1c', marginTop: 8 }}>{kbError}</div> : null}
              {kbSaveStatus ? (
                <div style={{ color: '#047857', marginTop: 8 }}>{kbSaveStatus}</div>
              ) : null}
            </div>

            <div style={{ maxHeight: 420, overflowY: 'auto', overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr style={{ background: '#f8fafc', borderBottom: '1px solid #e5e7eb' }}>
                    <th style={{ textAlign: 'left', padding: '8px 10px' }}>名称</th>
                    <th style={{ textAlign: 'left', padding: '8px 10px' }}>修改日期</th>
                    <th style={{ textAlign: 'left', padding: '8px 10px' }}>类型</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredRows.map((row) => {
                    const selected =
                      selectedItem?.kind === row.kind && selectedItem?.id === row.id;
                    const safeRowId = String(row.id || '').replace(/[^a-zA-Z0-9_-]/g, '_');

                    return (
                      <tr
                        key={`${row.kind}_${row.id}`}
                        data-testid={`kbs-row-${row.kind}-${safeRowId}`}
                        draggable={canManageDirectory && row.kind === 'dataset'}
                        onDragStart={(event) => handleDatasetDragStart(event, row)}
                        onDragEnd={handleDatasetDragEnd}
                        onClick={() => handleSelectRow(row)}
                        onDoubleClick={() => handleDoubleClickRow(row)}
                        style={{
                          borderBottom: '1px solid #f1f5f9',
                          background: selected ? '#eff6ff' : '#fff',
                          cursor:
                            canManageDirectory && row.kind === 'dataset' ? 'grab' : 'pointer',
                          opacity:
                            dragDatasetId && row.kind === 'dataset' && dragDatasetId === row.id
                              ? 0.5
                              : 1,
                        }}
                      >
                        <td style={{ padding: '8px 10px' }}>{row.name}</td>
                        <td style={{ padding: '8px 10px', color: '#4b5563' }}>{row.modified}</td>
                        <td style={{ padding: '8px 10px', color: '#4b5563' }}>{row.type}</td>
                      </tr>
                    );
                  })}
                  {!filteredRows.length ? (
                    <tr>
                      <td colSpan={3} style={{ padding: 18, color: '#6b7280', textAlign: 'center' }}>
                        当前目录为空
                      </td>
                    </tr>
                  ) : null}
                </tbody>
              </table>
            </div>

            {showSelectedDatasetDetails ? (
              <div style={{ borderTop: '1px solid #e5e7eb', padding: 12 }}>
                <div style={{ fontWeight: 700, marginBottom: 8 }}>知识库属性</div>
                <div
                  style={{
                    display: 'grid',
                    gridTemplateColumns: isMobile ? '1fr' : '100px 1fr 130px',
                    gap: 8,
                    alignItems: 'center',
                    marginBottom: 8,
                  }}
                >
                  <label htmlFor="kbs-name-input">名称</label>
                  <input
                    id="kbs-name-input"
                    data-testid="kbs-name-input"
                    value={kbNameText}
                    onChange={(event) => setKbNameText(event.target.value)}
                    disabled={!canManageDatasets}
                    style={{
                      border: '1px solid #d1d5db',
                      borderRadius: 8,
                      padding: '8px 10px',
                      background: canManageDatasets ? '#fff' : '#f9fafb',
                    }}
                  />
                  {canManageDatasets ? (
                    <button
                      data-testid="kbs-save-kb"
                      onClick={saveKb}
                      disabled={kbBusy}
                      style={{
                        border: '1px solid #059669',
                        borderRadius: 8,
                        background: kbBusy ? '#6ee7b7' : '#10b981',
                        color: '#fff',
                        cursor: kbBusy ? 'not-allowed' : 'pointer',
                        padding: '8px 10px',
                        width: isMobile ? '100%' : 'auto',
                      }}
                    >
                      保存
                    </button>
                  ) : null}
                </div>
                <div
                  style={{
                    display: 'grid',
                    gridTemplateColumns: isMobile ? '1fr' : '100px 1fr 130px',
                    gap: 8,
                    alignItems: 'center',
                  }}
                >
                  <label htmlFor="kbs-dir-select">挂载目录</label>
                  <select
                    id="kbs-dir-select"
                    data-testid="kbs-dir-select"
                    value={datasetDirId}
                    onChange={(event) => setDatasetDirId(event.target.value)}
                    disabled={!canManageDatasets}
                    style={{
                      border: '1px solid #d1d5db',
                      borderRadius: 8,
                      padding: '8px 10px',
                      background: canManageDatasets ? '#fff' : '#f9fafb',
                    }}
                  >
                    {dirOptions.map((option) => (
                      <option key={option.id || '__root__'} value={option.id}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                  {canManageDatasets ? (
                    <button
                      data-testid="kbs-delete-kb"
                      onClick={handleDeleteSelectedKb}
                      disabled={kbBusy || !canDeleteSelectedKb}
                      style={{
                        border: '1px solid #ef4444',
                        borderRadius: 8,
                        background: kbBusy || !canDeleteSelectedKb ? '#fecaca' : '#ef4444',
                        color: '#fff',
                        cursor: kbBusy || !canDeleteSelectedKb ? 'not-allowed' : 'pointer',
                        padding: '8px 10px',
                        width: isMobile ? '100%' : 'auto',
                      }}
                    >
                      删除知识库
                    </button>
                  ) : null}
                </div>
              </div>
            ) : null}
          </section>
        </div>
      ) : (
        <ChatConfigsPanel />
      )}

      <CreateKnowledgeBaseDialog
        open={createOpen}
        onClose={closeCreateKb}
        createName={createName}
        onCreateNameChange={setCreateName}
        createFromId={createFromId}
        onCreateFromIdChange={handleCreateFromIdChange}
        kbList={kbList}
        createDirId={createDirId}
        onCreateDirIdChange={setCreateDirId}
        dirOptions={dirOptions}
        createError={createError}
        onCreate={createKb}
        isAdmin={canManageDatasets}
        kbBusy={kbBusy}
      />
    </div>
  );
}
