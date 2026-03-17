import React from 'react';

export default function GroupContentTable({
  rows,
  groups,
  selectedItem,
  dragGroupId,
  onSelectItem,
  onSelectFolder,
  onOpenFolder,
  onStartEditGroup,
  onRemoveGroup,
  onStartGroupDrag,
  onEndGroupDrag,
}) {
  return (
    <div style={{ width: '100%', overflowX: 'auto' }}>
      <table style={{ width: '100%', minWidth: 520, borderCollapse: 'collapse' }}>
        <thead>
          <tr style={{ background: '#f8fafc', borderBottom: '1px solid #e5e7eb' }}>
            <th style={{ textAlign: 'left', padding: '8px 10px' }}>名称</th>
            <th style={{ textAlign: 'left', padding: '8px 10px', width: 90 }}>类型</th>
            <th style={{ textAlign: 'left', padding: '8px 10px', width: 120 }}>操作</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => {
            const selected =
              selectedItem?.kind === row.kind && selectedItem?.id === row.id;
            return (
              <tr
                key={`${row.kind}_${row.id}`}
                draggable={row.kind === 'group'}
                onDragStart={(event) => {
                  if (row.kind !== 'group') return;
                  onStartGroupDrag(event, row.id);
                }}
                onDragEnd={onEndGroupDrag}
                onClick={() => {
                  onSelectItem({ kind: row.kind, id: row.id });
                  if (row.kind === 'folder') onSelectFolder(row.id);
                }}
                onDoubleClick={() => {
                  if (row.kind === 'folder') onOpenFolder(row.id);
                  if (row.kind === 'group') {
                    const group = groups.find((item) => item.group_id === row.id);
                    if (group) onStartEditGroup(group);
                  }
                }}
                style={{
                  borderBottom: '1px solid #f1f5f9',
                  background: selected ? '#eff6ff' : '#fff',
                  cursor: row.kind === 'group' ? 'grab' : 'pointer',
                  opacity:
                    dragGroupId && row.kind === 'group' && dragGroupId === row.id
                      ? 0.5
                      : 1,
                }}
              >
                <td style={{ padding: '8px 10px' }}>
                  {row.kind === 'folder' ? '[文件夹] ' : '[分组] '}
                  {row.name}
                </td>
                <td style={{ padding: '8px 10px', color: '#4b5563' }}>{row.type}</td>
                <td style={{ padding: '8px 10px' }}>
                  {row.kind === 'group' && (
                    <>
                      <button
                        type="button"
                        onClick={(event) => {
                          event.stopPropagation();
                          const group = groups.find((item) => item.group_id === row.id);
                          if (group) onStartEditGroup(group);
                        }}
                        style={{
                          border: '1px solid #3b82f6',
                          borderRadius: 8,
                          background: '#3b82f6',
                          color: '#fff',
                          cursor: 'pointer',
                          padding: '4px 8px',
                          marginRight: 6,
                          fontSize: 12,
                        }}
                      >
                        编辑
                      </button>
                      <button
                        type="button"
                        onClick={(event) => {
                          event.stopPropagation();
                          const group = groups.find((item) => item.group_id === row.id);
                          if (group) onRemoveGroup(group);
                        }}
                        style={{
                          border: '1px solid #ef4444',
                          borderRadius: 8,
                          background: '#ef4444',
                          color: '#fff',
                          cursor: 'pointer',
                          padding: '4px 8px',
                          fontSize: 12,
                        }}
                      >
                        删除
                      </button>
                    </>
                  )}
                </td>
              </tr>
            );
          })}
          {!rows.length && (
            <tr>
              <td colSpan={3} style={{ padding: 18, color: '#6b7280', textAlign: 'center' }}>
                当前文件夹为空
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
