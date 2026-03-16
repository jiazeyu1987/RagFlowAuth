import React from 'react';

export default function ConfigListPanel({
  panelClassName,
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
    <section className={panelClassName}>
      <div className="admin-med-panel__head">
        <div className="admin-med-head" style={{ alignItems: 'baseline' }}>
          <div style={{ fontWeight: 700, color: '#163f63' }}>检索配置列表</div>
          <div className="admin-med-inline-note">{loading ? '加载中...' : `共 ${list.length} 项`}</div>
        </div>

        <div className="admin-med-actions" style={{ marginTop: 10 }}>
          <input
            value={filter}
            onChange={(event) => onChangeFilter(event.target.value)}
            placeholder="按名称或编号筛选"
            className="medui-input"
            style={{ flex: 1, minWidth: 180 }}
          />
          <button onClick={onRefresh} disabled={loading} className="medui-btn medui-btn--secondary">
            刷新
          </button>
          <button onClick={onOpenCreate} disabled={!isAdmin} className="medui-btn medui-btn--primary">
            新建配置
          </button>
        </div>
      </div>

      <div className="admin-med-panel__body admin-med-list-scroll">
        {error ? <div className="admin-med-danger">{error}</div> : null}

        {filteredList.length === 0 ? (
          <div className="medui-empty" style={{ paddingTop: 16 }}>暂无匹配配置</div>
        ) : (
          filteredList.map((item) => {
            const active = selectedId === item.id;
            return (
              <div key={item.id} className="admin-med-list-item">
                <button type="button" className={`admin-med-list-item__button${active ? ' is-active' : ''}`} onClick={() => onSelect(item.id)}>
                  <div className="admin-med-list-item__title">{item.name || '（未命名）'}</div>
                  <div className="admin-med-list-item__meta">{`编号：${item.id}`}</div>
                </button>

                {isAdmin ? (
                  <button
                    type="button"
                    onClick={(event) => {
                      event.preventDefault();
                      event.stopPropagation();
                      onDelete(item);
                    }}
                    disabled={busy}
                    title="删除"
                    className="medui-btn medui-btn--danger admin-med-list-item__delete"
                  >
                    删除
                  </button>
                ) : null}
              </div>
            );
          })
        )}
      </div>
    </section>
  );
}
