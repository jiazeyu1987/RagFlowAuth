import React from 'react';

import { toNodeKey } from '../helpers';
import { panelStyle } from '../pageStyles';
import OrgTreeNode from './OrgTreeNode';

export default function OrgTreePanel({
  isMobile,
  tree,
  isMissingPersonNodes,
  expandedKeys,
  handleToggleBranch,
  handleSelectPerson,
  highlightedNodeKey,
  selectedPersonNodeKey,
  personColumnCount,
  registerNodeRef,
}) {
  return (
    <div style={{ ...panelStyle, padding: isMobile ? 14 : 18, minWidth: 0 }}>
      {isMissingPersonNodes ? (
        <div
          data-testid="org-tree-empty-people-hint"
          style={{
            marginBottom: 12,
            padding: '10px 12px',
            borderRadius: 10,
            backgroundColor: '#fff7ed',
            border: '1px solid #fdba74',
            color: '#9a3412',
            fontSize: '0.82rem',
            lineHeight: 1.6,
          }}
        >
          当前组织库缺少人员叶子节点，树暂时只能展示到部门。请先在右侧选择组织架构 Excel 文件，再执行重建后展开到个人。
        </div>
      ) : null}

      <div data-testid="org-tree" style={{ display: 'grid', gap: 3 }}>
        {tree.map((companyNode) => (
          <OrgTreeNode
            key={toNodeKey(companyNode)}
            node={companyNode}
            depth={0}
            expandedKeys={expandedKeys}
            onToggleBranch={handleToggleBranch}
            onSelectPerson={handleSelectPerson}
            highlightedNodeKey={highlightedNodeKey}
            selectedPersonNodeKey={selectedPersonNodeKey}
            personColumnCount={personColumnCount}
            registerNodeRef={registerNodeRef}
          />
        ))}
        {tree.length === 0 ? <div style={{ color: '#6b7280' }}>暂无组织数据</div> : null}
      </div>
    </div>
  );
}
