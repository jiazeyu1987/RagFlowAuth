import React from 'react';

const headerButtonStyle = {
  flex: '1 1 120px',
  padding: '10px 12px',
  borderRadius: '10px',
  border: '1px solid #e5e7eb',
  background: '#ffffff',
  color: '#111827',
  cursor: 'pointer',
  fontWeight: 800,
};

const listItemStyle = (active) => ({
  padding: '12px 12px',
  borderRadius: '12px',
  border: `1px solid ${active ? '#2563eb' : '#e5e7eb'}`,
  background: active ? '#eff6ff' : '#ffffff',
  cursor: 'pointer',
  marginBottom: '10px',
  display: 'grid',
  gridTemplateColumns: '1fr 56px',
  gap: '10px',
  alignItems: 'center',
});

export default function ConfigListPanel({
  list,
  filteredList,
  selectedId,
  filter,
  loading,
  error,
  busy,
  isAdmin,
  onChangeFilter,
  onOpenCreate,
  onRefresh,
  onSelect,
  onDelete,
}) {
  return (
    <div
      style={{
        background: '#ffffff',
        border: '1px solid #e5e7eb',
        borderRadius: '12px',
        overflow: 'hidden',
        boxShadow: '0 6px 18px rgba(15, 23, 42, 0.06)',
      }}
    >
      <div style={{ padding: '14px 14px 10px', borderBottom: '1px solid #e5e7eb' }}>
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: '10px',
          }}
        >
          <div style={{ fontWeight: 900, fontSize: '15px', color: '#111827' }}>
            检索配置 <span style={{ color: '#6b7280' }}>({list.length})</span>
          </div>
          <div style={{ display: 'flex', gap: '8px' }}>
            <button onClick={onOpenCreate} disabled={!isAdmin} style={headerButtonStyle}>
              新建
            </button>
            <button onClick={onRefresh} disabled={loading} style={headerButtonStyle}>
              刷新
            </button>
          </div>
        </div>

        <div style={{ marginTop: '12px' }}>
          <input
            value={filter}
            onChange={(event) => onChangeFilter(event.target.value)}
            placeholder="按名称或编号筛选"
            style={{
              width: '100%',
              padding: '10px 12px',
              borderRadius: '12px',
              border: '1px solid #e5e7eb',
              outline: 'none',
              fontWeight: 700,
            }}
          />
        </div>
        {error ? (
          <div style={{ marginTop: '10px', color: '#b91c1c', fontWeight: 800 }}>{error}</div>
        ) : null}
        {loading ? <div style={{ marginTop: '10px', color: '#6b7280' }}>加载中...</div> : null}
      </div>

      <div style={{ padding: '14px', maxHeight: '72vh', overflow: 'auto' }}>
        {filteredList.map((item) => {
          const active = selectedId === item.id;
          return (
            <div key={item.id} style={listItemStyle(active)} onClick={() => onSelect(item.id)}>
              <div style={{ minWidth: 0 }}>
                <div
                  style={{
                    fontWeight: 900,
                    color: '#111827',
                    whiteSpace: 'nowrap',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                  }}
                >
                  {item.name || '（未命名）'}
                </div>
                <div style={{ marginTop: '4px', color: '#6b7280', fontSize: '12px' }}>
                  ID：{item.id}
                </div>
              </div>
              <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
                {isAdmin ? (
                  <button
                    onClick={(event) => {
                      event.preventDefault();
                      event.stopPropagation();
                      onDelete(item);
                    }}
                    disabled={busy}
                    title="删除"
                    style={{
                      width: '44px',
                      height: '36px',
                      borderRadius: '10px',
                      border: '1px solid #fecaca',
                      background: busy ? '#fee2e2' : '#ffffff',
                      color: '#b91c1c',
                      cursor: busy ? 'not-allowed' : 'pointer',
                      fontWeight: 900,
                    }}
                  >
                    删
                  </button>
                ) : null}
              </div>
            </div>
          );
        })}
        {!filteredList.length ? <div style={{ color: '#6b7280' }}>暂无配置</div> : null}
      </div>
    </div>
  );
}
