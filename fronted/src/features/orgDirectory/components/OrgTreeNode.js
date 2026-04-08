import React from 'react';

import { chunkItems, formatDateTime, toNodeKey } from '../helpers';
import { treeBranchStyle, treeButtonStyle } from '../pageStyles';

export default function OrgTreeNode({
  node,
  depth,
  expandedKeys,
  onToggleBranch,
  onSelectPerson,
  highlightedNodeKey,
  selectedPersonNodeKey,
  personColumnCount,
  registerNodeRef,
}) {
  const nodeKey = toNodeKey(node);
  const children = Array.isArray(node.children) ? node.children : [];
  const branchChildren = children.filter((item) => item.node_type !== 'person');
  const peopleChildren = children.filter((item) => item.node_type === 'person');
  const sortedPeopleChildren = [...peopleChildren].sort((left, right) => {
    const leftManager = left.is_department_manager ? 1 : 0;
    const rightManager = right.is_department_manager ? 1 : 0;
    if (leftManager !== rightManager) return rightManager - leftManager;
    if ((left.sort_order || 0) !== (right.sort_order || 0)) {
      return (left.sort_order || 0) - (right.sort_order || 0);
    }
    return String(left.name || '').localeCompare(String(right.name || ''), 'zh-CN');
  });
  const peopleRows = chunkItems(sortedPeopleChildren, personColumnCount);
  const hasChildren = children.length > 0;
  const branchExpanded = node.node_type === 'person' ? false : expandedKeys.has(nodeKey);
  const isHighlighted = highlightedNodeKey === nodeKey;
  const isCompany = node.node_type === 'company';
  const isPerson = node.node_type === 'person';
  const badgeLabel = isCompany ? '公司' : '部门';
  const metaText = isPerson
    ? [
        node.employee_user_id ? `员工UserID ${node.employee_user_id}` : null,
        node.employee_no ? `工号 ${node.employee_no}` : null,
        node.email ? node.email : null,
      ]
        .filter(Boolean)
        .join(' / ') || '-'
    : `更新时间 ${formatDateTime(node.updated_at_ms)}`;

  return (
    <div style={{ marginTop: depth === 0 ? 0 : 2 }}>
      <div
        ref={(element) => registerNodeRef(nodeKey, element)}
        data-node-key={nodeKey}
        data-testid={`org-tree-node-${node.node_type}-${node.id}`}
        style={{
          display: 'flex',
          alignItems: 'flex-start',
          gap: 8,
          padding: isCompany ? '5px 8px' : '4px 8px',
          borderRadius: 10,
          backgroundColor: isHighlighted ? '#dbeafe' : isCompany ? '#f8fbff' : '#ffffff',
          border: `1px solid ${isHighlighted ? '#60a5fa' : isCompany ? '#dbeafe' : '#edf2f7'}`,
        }}
      >
        <div style={{ width: 18, marginTop: 1 }}>
          {!isPerson && hasChildren ? (
            <button
              type="button"
              onClick={() => onToggleBranch(nodeKey)}
              aria-label={branchExpanded ? '收起分支' : '展开分支'}
              style={treeButtonStyle}
            >
              {branchExpanded ? '-' : '+'}
            </button>
          ) : (
            <div style={{ width: 18 }} />
          )}
        </div>

        <div style={{ minWidth: 0, flex: 1 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' }}>
            {!isPerson ? (
              <span
                style={{
                  fontSize: '0.68rem',
                  lineHeight: 1.2,
                  padding: '2px 7px',
                  borderRadius: 999,
                  backgroundColor: isCompany ? '#dbeafe' : '#f3f4f6',
                  color: '#1f2937',
                  fontWeight: 700,
                }}
              >
                {badgeLabel}
              </span>
            ) : null}
            <span
              style={{
                fontSize: isCompany ? '0.87rem' : '0.82rem',
                fontWeight: 700,
                color: '#111827',
                wordBreak: 'break-word',
              }}
            >
              {node.name}
            </span>
            {!isCompany && !isPerson ? (
              <span style={{ fontSize: '0.72rem', color: '#64748b' }}>L{node.level_no}</span>
            ) : null}
          </div>

          {node.path_name && node.path_name !== node.name ? (
            <div style={{ marginTop: 3, color: '#6b7280', fontSize: '0.74rem', wordBreak: 'break-word' }}>
              {node.path_name}
            </div>
          ) : null}

          <div style={{ marginTop: 3, color: '#64748b', fontSize: '0.73rem', wordBreak: 'break-word' }}>
            {metaText}
          </div>
        </div>
      </div>

      {!isPerson && branchExpanded ? (
        <div style={treeBranchStyle}>
          {branchChildren.map((child) => (
            <OrgTreeNode
              key={toNodeKey(child)}
              node={child}
              depth={depth + 1}
              expandedKeys={expandedKeys}
              onToggleBranch={onToggleBranch}
              onSelectPerson={onSelectPerson}
              highlightedNodeKey={highlightedNodeKey}
              selectedPersonNodeKey={selectedPersonNodeKey}
              personColumnCount={personColumnCount}
              registerNodeRef={registerNodeRef}
            />
          ))}

          {sortedPeopleChildren.length > 0 ? (
            <div style={{ marginTop: 4, overflowX: 'auto' }}>
              <table
                style={{
                  width: '100%',
                  borderCollapse: 'collapse',
                  tableLayout: 'fixed',
                  backgroundColor: '#ffffff',
                  border: '1px solid #e5e7eb',
                  borderRadius: 10,
                }}
              >
                <tbody>
                  {peopleRows.map((row, rowIndex) => (
                    <tr key={`person-row-${nodeKey}-${rowIndex}`}>
                      {row.map((child, columnIndex) => {
                        const childNodeKey = toNodeKey(child);
                        const isSelectedPerson = selectedPersonNodeKey === childNodeKey;
                        const isHighlightedPerson = highlightedNodeKey === childNodeKey;

                        return (
                          <td
                            key={childNodeKey}
                            style={{
                              width: `${100 / personColumnCount}%`,
                              borderBottom:
                                rowIndex === peopleRows.length - 1 ? 'none' : '1px solid #e5e7eb',
                              borderRight: columnIndex === row.length - 1 ? 'none' : '1px solid #e5e7eb',
                              padding: 0,
                            }}
                          >
                            <button
                              ref={(element) => registerNodeRef(childNodeKey, element)}
                              type="button"
                              data-node-key={childNodeKey}
                              data-testid={`org-tree-node-person-${child.id}`}
                              onClick={() => onSelectPerson(child)}
                              style={{
                                width: '100%',
                                padding: '8px 10px',
                                border: 'none',
                                backgroundColor:
                                  isSelectedPerson || isHighlightedPerson ? '#eff6ff' : '#ffffff',
                                color: child.is_department_manager ? '#15803d' : '#111827',
                                fontSize: '0.8rem',
                                fontWeight: child.is_department_manager ? 700 : 500,
                                textAlign: 'left',
                                cursor: 'pointer',
                                whiteSpace: 'nowrap',
                                overflow: 'hidden',
                                textOverflow: 'ellipsis',
                              }}
                              title={child.name}
                            >
                              {child.name}
                            </button>
                          </td>
                        );
                      })}
                      {Array.from({ length: Math.max(0, personColumnCount - row.length) }).map(
                        (_, fillerIndex) => (
                          <td
                            key={`person-empty-${nodeKey}-${rowIndex}-${fillerIndex}`}
                            style={{
                              width: `${100 / personColumnCount}%`,
                              borderBottom:
                                rowIndex === peopleRows.length - 1 ? 'none' : '1px solid #e5e7eb',
                              borderRight:
                                fillerIndex === personColumnCount - row.length - 1
                                  ? 'none'
                                  : '1px solid #e5e7eb',
                            }}
                          />
                        )
                      )}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
