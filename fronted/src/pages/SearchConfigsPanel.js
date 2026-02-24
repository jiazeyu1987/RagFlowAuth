import React, { useEffect, useMemo, useState } from 'react';
import { useAuth } from '../hooks/useAuth';
import { knowledgeApi } from '../features/knowledge/api';

function prettyJson(obj) {
  return JSON.stringify(obj ?? {}, null, 2);
}

function parseJson(text) {
  try {
    const val = JSON.parse(text || '{}');
    if (!val || typeof val !== 'object' || Array.isArray(val)) return { ok: false, error: 'JSON 必须是对象' };
    return { ok: true, value: val };
  } catch (e) {
    return { ok: false, error: `JSON 解析失败: ${e?.message || String(e)}` };
  }
}

function normalizeListResponse(res) {
  if (!res) return [];
  if (Array.isArray(res.configs)) return res.configs;
  if (res.data && Array.isArray(res.data.configs)) return res.data.configs;
  if (Array.isArray(res.data)) return res.data;
  return [];
}

export function SearchConfigsPanel() {
  const { user } = useAuth();
  const isAdmin = (user?.role || '') === 'admin';

  const [list, setList] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [filter, setFilter] = useState('');

  const [selected, setSelected] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState('');
  const [nameText, setNameText] = useState('');
  const [jsonText, setJsonText] = useState('{}');
  const [saveStatus, setSaveStatus] = useState('');
  const [busy, setBusy] = useState(false);

  const [createOpen, setCreateOpen] = useState(false);
  const [createMode, setCreateMode] = useState('blank'); // blank | copy
  const [createName, setCreateName] = useState('');
  const [createFromId, setCreateFromId] = useState('');
  const [createJsonText, setCreateJsonText] = useState('{}');
  const [createError, setCreateError] = useState('');

  const filteredList = useMemo(() => {
    const kw = String(filter || '').trim().toLowerCase();
    if (!kw) return list;
    return list.filter((x) => {
      const id = String(x?.id || '').toLowerCase();
      const name = String(x?.name || '').toLowerCase();
      return id.includes(kw) || name.includes(kw);
    });
  }, [filter, list]);

  async function fetchList() {
    setError('');
    setLoading(true);
    try {
      const res = await knowledgeApi.listSearchConfigs();
      setList(normalizeListResponse(res));
    } catch (e) {
      setList([]);
      setError(e?.message || '加载失败');
    } finally {
      setLoading(false);
    }
  }

  async function loadDetail(configId) {
    if (!configId) return;
    setDetailError('');
    setSaveStatus('');
    setDetailLoading(true);
    try {
      const cfg = await knowledgeApi.getSearchConfig(configId);
      if (!cfg || !cfg.id) throw new Error('config_not_found');
      setSelected(cfg);
      setNameText(String(cfg?.name || ''));
      setJsonText(prettyJson(cfg?.config || {}));
    } catch (e) {
      setSelected(null);
      setDetailError(e?.message || '加载失败');
    } finally {
      setDetailLoading(false);
    }
  }

  useEffect(() => {
    fetchList();
  }, []);

  useEffect(() => {
    if (!selected && list.length) loadDetail(list[0]?.id || '');
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [list]);

  async function save() {
    if (!selected?.id) return;
    setDetailError('');
    setSaveStatus('');

    const parsed = parseJson(jsonText);
    if (!parsed.ok) {
      setDetailError(parsed.error);
      return;
    }

    const name = String(nameText || selected.name || '').trim();
    if (!name) {
      setDetailError('名称不能为空');
      return;
    }

    setBusy(true);
    try {
      const updated = await knowledgeApi.updateSearchConfig(selected.id, { name, config: parsed.value });
      if (!updated || !updated.id) throw new Error('保存成功但未返回最新配置');
      setSelected(updated);
      setNameText(String(updated?.name || name));
      setJsonText(prettyJson(updated?.config || parsed.value));
      setSaveStatus('已保存');
      await fetchList();
    } catch (e) {
      setDetailError(e?.message || '保存失败');
    } finally {
      setBusy(false);
    }
  }

  async function removeItem(item) {
    if (!item?.id) return;
    const ok = window.confirm(`确认删除搜索配置: ${item.name || item.id}`);
    if (!ok) return;
    setBusy(true);
    try {
      await knowledgeApi.deleteSearchConfig(item.id);
      if (selected?.id === item.id) setSelected(null);
      await fetchList();
    } catch (e) {
      setError(e?.message || '删除失败');
    } finally {
      setBusy(false);
    }
  }

  function openCreate() {
    setCreateMode('blank');
    setCreateName('');
    setCreateFromId('');
    setCreateJsonText('{}');
    setCreateError('');
    setCreateOpen(true);
  }

  async function syncCreateJsonFromCopy(sourceId) {
    if (!sourceId) return;
    setCreateError('');
    try {
      const src = await knowledgeApi.getSearchConfig(sourceId);
      if (!src || !src.id) throw new Error('未获取到源配置');
      setCreateJsonText(prettyJson(src?.config || {}));
    } catch (e) {
      setCreateJsonText('{}');
      setCreateError(e?.message || '读取源配置失败');
    }
  }

  async function create() {
    if (!isAdmin) return;
    setCreateError('');

    const name = String(createName || '').trim();
    if (!name) {
      setCreateError('请输入名称');
      return;
    }
    const parsed = parseJson(createJsonText);
    if (!parsed.ok) {
      setCreateError(parsed.error);
      return;
    }

    setBusy(true);
    try {
      const created = await knowledgeApi.createSearchConfig({ name, config: parsed.value });
      if (!created || !created.id) throw new Error('创建成功但未返回配置');
      setCreateOpen(false);
      await fetchList();
      await loadDetail(created.id);
    } catch (e) {
      setCreateError(e?.message || '创建失败');
    } finally {
      setBusy(false);
    }
  }

  const shellStyle = {
    padding: '16px',
    display: 'grid',
    gridTemplateColumns: '360px 1fr',
    gap: '14px',
    alignItems: 'start',
  };

  const panelStyle = {
    background: '#ffffff',
    border: '1px solid #e5e7eb',
    borderRadius: '12px',
    overflow: 'hidden',
    boxShadow: '0 6px 18px rgba(15, 23, 42, 0.06)',
  };

  const headerBtn = (active) => ({
    flex: '1 1 140px',
    padding: '10px 12px',
    borderRadius: '10px',
    border: `1px solid ${active ? '#1d4ed8' : '#e5e7eb'}`,
    background: active ? '#1d4ed8' : '#ffffff',
    color: active ? '#ffffff' : '#111827',
    cursor: 'pointer',
    fontWeight: 900,
  });

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

  return (
    <div style={shellStyle}>
      <div style={panelStyle}>
        <div style={{ padding: '14px 14px 10px', borderBottom: '1px solid #e5e7eb' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '10px' }}>
            <div style={{ fontWeight: 950, fontSize: '15px', color: '#111827' }}>
              搜索配置 <span style={{ color: '#6b7280', fontWeight: 800 }}>({list.length} 个)</span>
            </div>
            <div style={{ display: 'flex', gap: '8px' }}>
              <button onClick={openCreate} disabled={!isAdmin} style={headerBtn(false)}>
                新建
              </button>
              <button onClick={fetchList} disabled={loading} style={headerBtn(false)}>
                刷新
              </button>
            </div>
          </div>

          <div style={{ display: 'flex', gap: '10px', marginTop: '12px' }}>
            <input
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              placeholder="按名称/ID 筛选"
              style={{
                flex: 1,
                padding: '10px 12px',
                borderRadius: '12px',
                border: '1px solid #e5e7eb',
                outline: 'none',
                fontWeight: 800,
              }}
            />
          </div>
          {error ? <div style={{ marginTop: '10px', color: '#b91c1c', fontWeight: 900 }}>{error}</div> : null}
          {loading ? <div style={{ marginTop: '10px', color: '#6b7280' }}>加载中...</div> : null}
        </div>

        <div style={{ padding: '14px', maxHeight: '72vh', overflow: 'auto' }}>
          {filteredList.map((x) => {
            const active = selected?.id === x.id;
            return (
              <div key={x.id} style={listItemStyle(active)} onClick={() => loadDetail(x.id)}>
                <div style={{ minWidth: 0 }}>
                  <div style={{ fontWeight: 950, color: '#111827', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                    {x.name || '(未命名)'}
                  </div>
                  <div style={{ marginTop: '4px', color: '#6b7280', fontSize: '12px', fontWeight: 800 }}>
                    ID: {x.id}
                  </div>
                </div>
                <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
                  {isAdmin ? (
                    <button
                      onClick={(e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        removeItem(x);
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
                        fontWeight: 950,
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

      <div style={panelStyle}>
        <div style={{ padding: '14px', borderBottom: '1px solid #e5e7eb', display: 'flex', justifyContent: 'space-between', gap: '10px' }}>
          <div style={{ fontWeight: 950, color: '#111827' }}>配置</div>
          <div style={{ color: '#6b7280', fontWeight: 800 }}>{selected?.name || ''}</div>
        </div>

        <div style={{ padding: '14px' }}>
          {detailLoading ? <div style={{ color: '#6b7280' }}>加载中...</div> : null}
          {detailError ? <div style={{ color: '#b91c1c', fontWeight: 900 }}>{detailError}</div> : null}
          {!selected && !detailLoading ? <div style={{ color: '#6b7280' }}>未选择</div> : null}

          {selected ? (
            <div>
              <div style={{ fontWeight: 950, color: '#111827', marginTop: '8px' }}>名称</div>
              <input
                value={nameText}
                disabled={!isAdmin}
                onChange={(e) => setNameText(e.target.value)}
                placeholder="搜索配置名称"
                style={{
                  width: '100%',
                  padding: '10px 12px',
                  borderRadius: '12px',
                  border: '1px solid #e5e7eb',
                  outline: 'none',
                  fontWeight: 800,
                  marginTop: '8px',
                  background: !isAdmin ? '#f9fafb' : '#ffffff',
                }}
              />

              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: '14px' }}>
                <div style={{ fontWeight: 950, color: '#111827' }}>原始 JSON</div>
                <div style={{ display: 'flex', gap: '10px' }}>
                  <button
                    onClick={() => {
                      setNameText(String(selected?.name || ''));
                      setJsonText(prettyJson(selected?.config || {}));
                      setSaveStatus('');
                      setDetailError('');
                    }}
                    disabled={busy}
                    style={{
                      padding: '10px 14px',
                      borderRadius: '12px',
                      border: '1px solid #e5e7eb',
                      background: '#ffffff',
                      cursor: busy ? 'not-allowed' : 'pointer',
                      fontWeight: 950,
                    }}
                  >
                    重置
                  </button>
                  {isAdmin ? (
                    <button
                      onClick={save}
                      disabled={busy}
                      style={{
                        padding: '10px 14px',
                        borderRadius: '12px',
                        border: '1px solid #1d4ed8',
                        background: busy ? '#93c5fd' : '#2563eb',
                        color: '#ffffff',
                        cursor: busy ? 'not-allowed' : 'pointer',
                        fontWeight: 950,
                      }}
                    >
                      保存
                    </button>
                  ) : null}
                </div>
              </div>

              <textarea
                value={jsonText}
                disabled={!isAdmin}
                onChange={(e) => setJsonText(e.target.value)}
                spellCheck={false}
                style={{
                  width: '100%',
                  minHeight: '360px',
                  marginTop: '10px',
                  borderRadius: '12px',
                  border: '1px solid #e5e7eb',
                  padding: '12px',
                  fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace',
                  fontSize: '12px',
                  outline: 'none',
                  background: !isAdmin ? '#f9fafb' : '#ffffff',
                }}
              />

              {saveStatus ? <div style={{ marginTop: '10px', color: '#065f46', fontWeight: 950 }}>{saveStatus}</div> : null}
            </div>
          ) : null}
        </div>
      </div>

      {createOpen ? (
        <div
          onClick={() => setCreateOpen(false)}
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(15, 23, 42, 0.45)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '18px',
            zIndex: 9999,
          }}
        >
          <div
            onClick={(e) => e.stopPropagation()}
            style={{
              width: 'min(900px, 96vw)',
              background: '#ffffff',
              borderRadius: '16px',
              border: '1px solid #e5e7eb',
              overflow: 'hidden',
              boxShadow: '0 24px 80px rgba(0, 0, 0, 0.25)',
            }}
          >
            <div style={{ padding: '14px 16px', borderBottom: '1px solid #e5e7eb', display: 'flex', justifyContent: 'space-between' }}>
              <div style={{ fontWeight: 950 }}>新建搜索配置</div>
              <button
                onClick={() => setCreateOpen(false)}
                style={{ border: 'none', background: 'transparent', cursor: 'pointer', fontSize: '18px', fontWeight: 900 }}
              >
                ×
              </button>
            </div>

            <div style={{ padding: '14px 16px', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
              <div>
                <div style={{ fontWeight: 950, color: '#111827' }}>创建方式</div>
                <div style={{ display: 'flex', gap: '10px', marginTop: '8px' }}>
                  <button
                    onClick={() => {
                      setCreateMode('blank');
                      setCreateFromId('');
                      setCreateJsonText('{}');
                      setCreateError('');
                    }}
                    style={headerBtn(createMode === 'blank')}
                  >
                    空白
                  </button>
                  <button
                    onClick={() => {
                      setCreateMode('copy');
                      setCreateError('');
                    }}
                    style={headerBtn(createMode === 'copy')}
                  >
                    复制
                  </button>
                </div>
              </div>
              <div>
                <div style={{ fontWeight: 950, color: '#111827' }}>名称</div>
                <input
                  value={createName}
                  onChange={(e) => setCreateName(e.target.value)}
                  placeholder="输入名称"
                  style={{
                    width: '100%',
                    marginTop: '8px',
                    padding: '10px 12px',
                    borderRadius: '12px',
                    border: '1px solid #e5e7eb',
                    outline: 'none',
                    fontWeight: 800,
                  }}
                />
              </div>
            </div>

            {createMode === 'copy' ? (
              <div style={{ padding: '0 16px 14px' }}>
                <div style={{ fontWeight: 950, color: '#111827' }}>从已有配置复制</div>
                <select
                  value={createFromId}
                  onChange={(e) => {
                    const v = e.target.value;
                    setCreateFromId(v);
                    syncCreateJsonFromCopy(v);
                  }}
                  style={{
                    width: '100%',
                    marginTop: '8px',
                    padding: '10px 12px',
                    borderRadius: '12px',
                    border: '1px solid #e5e7eb',
                    outline: 'none',
                    fontWeight: 800,
                    background: '#ffffff',
                  }}
                >
                  <option value="">请选择...</option>
                  {list.map((x) => (
                    <option key={x.id} value={x.id}>
                      {x.name || x.id}
                    </option>
                  ))}
                </select>
              </div>
            ) : null}

            <div style={{ padding: '0 16px 16px' }}>
              <div style={{ fontWeight: 950, color: '#111827' }}>配置 JSON</div>
              <textarea
                value={createJsonText}
                onChange={(e) => setCreateJsonText(e.target.value)}
                spellCheck={false}
                style={{
                  width: '100%',
                  minHeight: '240px',
                  marginTop: '8px',
                  borderRadius: '12px',
                  border: '1px solid #e5e7eb',
                  padding: '12px',
                  fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace',
                  fontSize: '12px',
                  outline: 'none',
                }}
              />
              {createError ? <div style={{ marginTop: '10px', color: '#b91c1c', fontWeight: 900 }}>{createError}</div> : null}
            </div>

            <div style={{ padding: '14px 16px', borderTop: '1px solid #e5e7eb', display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
              <button
                onClick={() => setCreateOpen(false)}
                style={{
                  padding: '10px 14px',
                  borderRadius: '12px',
                  border: '1px solid #e5e7eb',
                  background: '#ffffff',
                  cursor: 'pointer',
                  fontWeight: 900,
                }}
              >
                取消
              </button>
              <button
                onClick={create}
                disabled={!isAdmin || busy}
                style={{
                  padding: '10px 14px',
                  borderRadius: '12px',
                  border: '1px solid #1d4ed8',
                  background: busy ? '#93c5fd' : '#2563eb',
                  color: '#ffffff',
                  cursor: busy ? 'not-allowed' : 'pointer',
                  fontWeight: 950,
                }}
              >
                创建
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
