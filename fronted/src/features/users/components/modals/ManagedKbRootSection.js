import React from 'react';
import KnowledgeRootNodeSelector from '../KnowledgeRootNodeSelector';

export default function ManagedKbRootSection({
  label,
  hint,
  nodes,
  disabledNodeIds = [],
  selectedNodeId,
  onSelect,
  loading,
  error,
  companyId,
  createRootError,
  creatingRoot,
  onCreateRootDirectory,
  invalidText = '',
  invalidTestId = '',
  showInvalidWarning = false,
  marginBottom = 16,
}) {
  return (
    <div style={{ marginBottom }}>
      <label style={{ display: 'block', marginBottom: '8px', fontWeight: '500' }}>{label}</label>
      {hint ? <div style={{ marginBottom: '8px', color: '#6b7280', fontSize: '0.85rem' }}>{hint}</div> : null}
      {showInvalidWarning ? (
        <div
          style={{
            marginBottom: 10,
            padding: '10px 12px',
            borderRadius: 8,
            backgroundColor: '#fff7ed',
            color: '#c2410c',
            fontSize: '0.85rem',
            border: '1px solid #fdba74',
          }}
          data-testid={invalidTestId || undefined}
        >
          {invalidText}
        </div>
      ) : null}
      <KnowledgeRootNodeSelector
        nodes={nodes}
        disabledNodeIds={disabledNodeIds}
        selectedNodeId={selectedNodeId}
        onSelect={onSelect}
        disabled={false}
        loading={loading}
        error={error}
        canCreateRoot={Boolean(companyId && onCreateRootDirectory)}
        creatingRoot={creatingRoot}
        createRootError={createRootError}
        onCreateRoot={onCreateRootDirectory}
      />
    </div>
  );
}
