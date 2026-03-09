import React from 'react';

const tabStyle = (active) => ({
  padding: '7px 12px',
  borderRadius: '999px',
  border: active ? '1px solid #2563eb' : '1px solid #e5e7eb',
  background: active ? '#dbeafe' : '#fff',
  color: active ? '#1e40af' : '#374151',
  cursor: 'pointer',
  fontWeight: 700,
});

const actionButtonStyle = (kind, disabled) => {
  if (kind === 'stop') {
    return {
      padding: '9px 12px',
      borderRadius: '10px',
      border: '1px solid #f59e0b',
      background: disabled ? '#fde68a' : '#f59e0b',
      color: '#fff',
      cursor: disabled ? 'not-allowed' : 'pointer',
      fontWeight: 800,
    };
  }
  if (kind === 'add') {
    return {
      padding: '9px 12px',
      borderRadius: '10px',
      border: '1px solid #059669',
      background: disabled ? '#6ee7b7' : '#10b981',
      color: '#fff',
      cursor: disabled ? 'not-allowed' : 'pointer',
      fontWeight: 800,
    };
  }
  return {
    padding: '9px 12px',
    borderRadius: '10px',
    border: '1px solid #ef4444',
    background: disabled ? '#fecaca' : '#ef4444',
    color: '#fff',
    cursor: disabled ? 'not-allowed' : 'pointer',
    fontWeight: 800,
  };
};

export default function DownloadResultToolbar({
  resultTab,
  onChangeTab,
  showActions = true,
  onStop,
  onAddAll,
  onRemoveAll,
  stopDisabled = false,
  addAllDisabled = false,
  removeAllDisabled = false,
  stopBusy = false,
  addAllBusy = false,
  currentTabText = 'Current',
  historyTabText = 'History',
  stopText = 'Stop',
  stopBusyText = 'Stopping...',
  addAllText = 'Add All',
  addAllBusyText = 'Adding...',
  removeAllText = 'Delete All',
}) {
  return (
    <>
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
        <button
          type="button"
          onClick={() => onChangeTab && onChangeTab('current')}
          style={tabStyle(resultTab === 'current')}
          data-testid="download-tab-current"
        >
          {currentTabText}
        </button>
        <button
          type="button"
          onClick={() => onChangeTab && onChangeTab('history')}
          style={tabStyle(resultTab === 'history')}
          data-testid="download-tab-history"
        >
          {historyTabText}
        </button>
      </div>

      {showActions ? (
        <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', marginBottom: '8px' }}>
          <button
            type="button"
            onClick={onStop}
            disabled={stopDisabled}
            style={actionButtonStyle('stop', stopDisabled)}
            data-testid="download-stop"
          >
            {stopBusy ? stopBusyText : stopText}
          </button>
          <button
            type="button"
            onClick={onAddAll}
            disabled={addAllDisabled}
            style={actionButtonStyle('add', addAllDisabled)}
            data-testid="download-add-all"
          >
            {addAllBusy ? addAllBusyText : addAllText}
          </button>
          <button
            type="button"
            onClick={onRemoveAll}
            disabled={removeAllDisabled}
            style={actionButtonStyle('delete', removeAllDisabled)}
            data-testid="download-delete-all"
          >
            {removeAllText}
          </button>
        </div>
      ) : null}
    </>
  );
}
