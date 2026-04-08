import React from 'react';

export default function KnowledgeBasesWorkspacePanel({
  ROOT,
  isMobile,
  canManageDirectory,
  canManageDatasets,
  currentDirId,
  selectedNodeId,
  breadcrumb,
  keyword,
  setKeyword,
  kbError,
  kbSaveStatus,
  filteredRows,
  selectedItem,
  dragDatasetId,
  handleDatasetDragStart,
  handleDatasetDragEnd,
  handleSelectRow,
  handleDoubleClickRow,
  refreshAll,
  handleGoParent,
  createDirectory,
  renameDirectory,
  deleteDirectory,
  openCreateKb,
  showSelectedDatasetDetails,
  kbNameText,
  setKbNameText,
  saveKb,
  kbBusy,
  datasetDirId,
  setDatasetDirId,
  dirOptions,
  handleDeleteSelectedKb,
  canDeleteSelectedKb,
  handleOpenBreadcrumb,
}) {
  return (
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
            {'\u5237\u65b0'}
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
            {'\u8fd4\u56de\u4e0a\u7ea7'}
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
                {'\u65b0\u5efa\u76ee\u5f55'}
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
                {'\u91cd\u547d\u540d\u76ee\u5f55'}
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
                {'\u5220\u9664\u76ee\u5f55'}
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
              {'\u65b0\u5efa\u77e5\u8bc6\u5e93'}
            </button>
          ) : null}
        </div>

        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 10 }}>
          <span style={{ color: '#6b7280', fontSize: 13 }}>{'\u8def\u5f84:'}</span>
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
          placeholder={'\u7b5b\u9009\u5f53\u524d\u76ee\u5f55\u5185\u5bb9'}
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
            {
              '\u652f\u6301\u62d6\u62fd\uff1a\u5c06\u53f3\u4fa7\u201c\u77e5\u8bc6\u5e93\u201d\u884c\u62d6\u5230\u5de6\u4fa7\u4efb\u610f\u76ee\u5f55\uff0c\u53ef\u5feb\u901f\u79fb\u52a8\u6302\u8f7d\u4f4d\u7f6e\u3002'
            }
          </div>
        ) : null}
        {kbError ? <div style={{ color: '#b91c1c', marginTop: 8 }}>{kbError}</div> : null}
        {kbSaveStatus ? <div style={{ color: '#047857', marginTop: 8 }}>{kbSaveStatus}</div> : null}
      </div>

      <div style={{ maxHeight: 420, overflowY: 'auto', overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ background: '#f8fafc', borderBottom: '1px solid #e5e7eb' }}>
              <th style={{ textAlign: 'left', padding: '8px 10px' }}>{'\u540d\u79f0'}</th>
              <th style={{ textAlign: 'left', padding: '8px 10px' }}>{'\u4fee\u6539\u65e5\u671f'}</th>
              <th style={{ textAlign: 'left', padding: '8px 10px' }}>{'\u7c7b\u578b'}</th>
            </tr>
          </thead>
          <tbody>
            {filteredRows.map((row) => {
              const selected = selectedItem?.kind === row.kind && selectedItem?.id === row.id;
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
                    cursor: canManageDirectory && row.kind === 'dataset' ? 'grab' : 'pointer',
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
                  {'\u5f53\u524d\u76ee\u5f55\u4e3a\u7a7a'}
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>

      {showSelectedDatasetDetails ? (
        <div style={{ borderTop: '1px solid #e5e7eb', padding: 12 }}>
          <div style={{ fontWeight: 700, marginBottom: 8 }}>{'\u77e5\u8bc6\u5e93\u5c5e\u6027'}</div>
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: isMobile ? '1fr' : '100px 1fr 130px',
              gap: 8,
              alignItems: 'center',
              marginBottom: 8,
            }}
          >
            <label htmlFor="kbs-name-input">{'\u540d\u79f0'}</label>
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
                {'\u4fdd\u5b58'}
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
            <label htmlFor="kbs-dir-select">{'\u6302\u8f7d\u76ee\u5f55'}</label>
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
                {'\u5220\u9664\u77e5\u8bc6\u5e93'}
              </button>
            ) : null}
          </div>
        </div>
      ) : null}
    </section>
  );
}
