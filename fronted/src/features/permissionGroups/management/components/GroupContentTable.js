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
    <table className="medui-table" style={{ minWidth: '100%' }}>
      <thead>
        <tr>
          <th style={{ padding: '8px 10px' }}>名称</th>
          <th style={{ padding: '8px 10px', width: 90 }}>类型</th>
          <th style={{ padding: '8px 10px', width: 150 }}>操作</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((row) => {
          const selected = selectedItem?.kind === row.kind && selectedItem?.id === row.id;
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
              className={selected ? 'admin-med-table-row-selected' : ''}
              style={{
                cursor: row.kind === 'group' ? 'grab' : 'pointer',
                opacity: dragGroupId && row.kind === 'group' && dragGroupId === row.id ? 0.5 : 1,
              }}
            >
              <td style={{ padding: '8px 10px' }}>
                {row.kind === 'folder' ? '[目录] ' : '[权限组] '}
                {row.name}
              </td>
              <td style={{ padding: '8px 10px', color: '#4b5563' }}>{row.type}</td>
              <td style={{ padding: '8px 10px' }}>
                {row.kind === 'group' ? (
                  <>
                    <button
                      type="button"
                      data-testid={`pg-edit-${String(row.id)}`}
                      onClick={(event) => {
                        event.stopPropagation();
                        const group = groups.find((item) => item.group_id === row.id);
                        if (group) onStartEditGroup(group);
                      }}
                      className="medui-btn medui-btn--secondary"
                      style={{ height: 30, padding: '0 10px', marginRight: 6 }}
                    >
                      编辑
                    </button>
                    <button
                      type="button"
                      data-testid={`pg-delete-${String(row.id)}`}
                      onClick={(event) => {
                        event.stopPropagation();
                        const group = groups.find((item) => item.group_id === row.id);
                        if (group) onRemoveGroup(group);
                      }}
                      className="medui-btn medui-btn--danger"
                      style={{ height: 30, padding: '0 10px' }}
                    >
                      删除
                    </button>
                  </>
                ) : null}
              </td>
            </tr>
          );
        })}
        {!rows.length ? (
          <tr>
            <td colSpan={3} style={{ padding: 18, color: '#6b7280', textAlign: 'center' }}>当前目录为空</td>
          </tr>
        ) : null}
      </tbody>
    </table>
  );
}
