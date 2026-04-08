import React from 'react';

import DirectoryTreeView from './DirectoryTreeView';

export default function KnowledgeBasesTreePanel({
  isMobile,
  treeError,
  indexes,
  currentDirId,
  selectedNodeId,
  expanded,
  handleToggleExpanded,
  handleTreeNodeOpen,
  canManageDirectory,
  dropTargetNodeId,
  handleTreeDragOver,
  handleTreeDrop,
  handleTreeDragLeave,
}) {
  return (
    <section style={{ border: '1px solid #e5e7eb', borderRadius: 12, background: '#fff' }}>
      <div
        style={{
          padding: '10px 12px',
          borderBottom: '1px solid #e5e7eb',
          fontWeight: 800,
        }}
      >
        {'\u76ee\u5f55\u6811'}
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
  );
}
