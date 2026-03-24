import React, { useMemo, useState } from 'react';
import authClient from '../api/authClient';
import { useAuth } from '../hooks/useAuth';

const tabStyle = (active) => ({
  border: '1px solid',
  borderColor: active ? '#2563eb' : '#d1d5db',
  background: active ? '#eff6ff' : '#ffffff',
  color: active ? '#1d4ed8' : '#374151',
  borderRadius: 10,
  padding: '8px 14px',
  cursor: 'pointer',
  fontWeight: 600,
});

const sectionStyle = {
  border: '1px solid #e5e7eb',
  borderRadius: 12,
  background: '#fff',
  padding: 16,
};

const fieldLabelStyle = {
  display: 'block',
  marginBottom: 6,
  fontWeight: 600,
  color: '#111827',
};

const keyStyle = {
  color: '#374151',
  fontWeight: 600,
  minWidth: 96,
  flexShrink: 0,
};

const valueStyle = {
  color: '#111827',
  wordBreak: 'break-word',
};

const mapApiError = (message) => {
  const code = String(message || '').trim();
  if (code === 'model_not_found') return '未找到该型号信息';
  if (code === 'only_xlsx_supported') return '仅支持 .xlsx 文件';
  if (code === 'file_required') return '请先选择导入文件';
  if (code === 'empty_file') return '文件内容为空';
  if (code.startsWith('invalid_xlsx')) return 'Excel 文件无法解析，请确认文件格式';
  return code || '操作失败';
};

const PackageDrawingTool = () => {
  const { isAdmin } = useAuth();
  const admin = isAdmin();

  const [activeTab, setActiveTab] = useState('query');
  const [model, setModel] = useState('');
  const [querying, setQuerying] = useState(false);
  const [queryResult, setQueryResult] = useState(null);
  const [queryError, setQueryError] = useState('');
  const [notFound, setNotFound] = useState(false);

  const [importFile, setImportFile] = useState(null);
  const [importing, setImporting] = useState(false);
  const [importResult, setImportResult] = useState(null);
  const [importError, setImportError] = useState('');

  const resultParameters = useMemo(() => {
    const source = queryResult?.parameters;
    if (!source || typeof source !== 'object') return [];
    return Object.entries(source);
  }, [queryResult]);

  const resultImages = useMemo(() => {
    const source = queryResult?.images;
    if (!Array.isArray(source)) return [];
    return source;
  }, [queryResult]);

  const onQuerySubmit = async (event) => {
    event.preventDefault();
    const clean = String(model || '').trim();
    if (!clean) {
      setQueryError('请输入型号');
      setNotFound(false);
      setQueryResult(null);
      return;
    }

    setQuerying(true);
    setQueryError('');
    setNotFound(false);
    setQueryResult(null);
    try {
      const data = await authClient.queryPackageDrawingByModel(clean);
      setQueryResult(data);
    } catch (error) {
      const message = String(error?.message || '');
      if (message === 'model_not_found') {
        setNotFound(true);
      } else {
        setQueryError(mapApiError(message));
      }
    } finally {
      setQuerying(false);
    }
  };

  const onImportSubmit = async (event) => {
    event.preventDefault();
    if (!importFile) {
      setImportError('请先选择 .xlsx 文件');
      setImportResult(null);
      return;
    }
    setImporting(true);
    setImportError('');
    setImportResult(null);
    try {
      const result = await authClient.importPackageDrawingExcel(importFile);
      setImportResult(result);
    } catch (error) {
      setImportError(mapApiError(error?.message));
    } finally {
      setImporting(false);
    }
  };

  return (
    <div data-testid="package-drawing-page" style={{ display: 'grid', gap: 14 }}>
      <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
        <button
          type="button"
          data-testid="package-drawing-tab-query"
          style={tabStyle(activeTab === 'query')}
          onClick={() => setActiveTab('query')}
        >
          查询信息
        </button>
        {admin ? (
          <button
            type="button"
            data-testid="package-drawing-tab-import"
            style={tabStyle(activeTab === 'import')}
            onClick={() => setActiveTab('import')}
          >
            录入信息
          </button>
        ) : null}
      </div>

      {activeTab === 'query' ? (
        <section style={sectionStyle}>
          <form onSubmit={onQuerySubmit} style={{ display: 'grid', gap: 10 }}>
            <div>
              <label htmlFor="package-drawing-model" style={fieldLabelStyle}>型号</label>
              <input
                id="package-drawing-model"
                data-testid="package-drawing-query-model"
                value={model}
                onChange={(event) => setModel(event.target.value)}
                placeholder="请输入型号（精确匹配）"
                style={{
                  width: '100%',
                  maxWidth: 520,
                  border: '1px solid #d1d5db',
                  borderRadius: 10,
                  padding: '10px 12px',
                }}
              />
            </div>
            <div>
              <button
                type="submit"
                data-testid="package-drawing-query-submit"
                disabled={querying}
                style={{
                  border: '1px solid #2563eb',
                  background: querying ? '#93c5fd' : '#2563eb',
                  color: '#fff',
                  borderRadius: 10,
                  padding: '8px 16px',
                  cursor: querying ? 'not-allowed' : 'pointer',
                }}
              >
                {querying ? '查询中...' : '查询'}
              </button>
            </div>
          </form>

          {queryError ? (
            <div data-testid="package-drawing-query-error" style={{ marginTop: 12, color: '#b91c1c' }}>
              {queryError}
            </div>
          ) : null}
          {notFound ? (
            <div data-testid="package-drawing-query-not-found" style={{ marginTop: 12, color: '#6b7280' }}>
              未找到该型号信息
            </div>
          ) : null}

          {queryResult ? (
            <div data-testid="package-drawing-query-result" style={{ marginTop: 14, display: 'grid', gap: 12 }}>
              <div style={{ display: 'flex', gap: 8 }}>
                <span style={keyStyle}>型号</span>
                <span style={valueStyle}>{queryResult.model || '-'}</span>
              </div>
              <div style={{ display: 'flex', gap: 8 }}>
                <span style={keyStyle}>条形码</span>
                <span style={valueStyle}>{queryResult.barcode || '-'}</span>
              </div>

              <div>
                <div style={{ ...keyStyle, marginBottom: 6 }}>产品参数</div>
                {!resultParameters.length ? (
                  <div style={{ color: '#6b7280' }}>暂无参数</div>
                ) : (
                  <div style={{ display: 'grid', gap: 6 }}>
                    {resultParameters.map(([k, v]) => (
                      <div key={k} style={{ display: 'flex', gap: 8 }}>
                        <span style={keyStyle}>{k}</span>
                        <span style={valueStyle}>{String(v || '')}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              <div>
                <div style={{ ...keyStyle, marginBottom: 8 }}>示意图</div>
                {!resultImages.length ? (
                  <div style={{ color: '#6b7280' }}>暂无示意图</div>
                ) : (
                  <div
                    data-testid="package-drawing-image-list"
                    style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 10 }}
                  >
                    {resultImages.map((img, idx) => {
                      const src = String(img?.data_url || img?.url || '').trim();
                      if (!src) return null;
                      return (
                        <div key={`${src}-${idx}`} style={{ border: '1px solid #e5e7eb', borderRadius: 8, padding: 8 }}>
                          <img
                            alt={`示意图-${idx + 1}`}
                            src={src}
                            style={{ width: '100%', height: 160, objectFit: 'contain', background: '#f8fafc' }}
                          />
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </div>
          ) : null}
        </section>
      ) : null}

      {activeTab === 'import' ? (
        <section style={sectionStyle}>
          {admin ? (
            <form onSubmit={onImportSubmit} style={{ display: 'grid', gap: 10 }}>
              <div>
                <label htmlFor="package-drawing-import-file" style={fieldLabelStyle}>导入文件（仅支持 .xlsx）</label>
                <input
                  id="package-drawing-import-file"
                  type="file"
                  accept=".xlsx"
                  data-testid="package-drawing-import-file"
                  onChange={(event) => setImportFile(event.target.files?.[0] || null)}
                />
              </div>
              <div>
                <button
                  type="submit"
                  data-testid="package-drawing-import-submit"
                  disabled={importing}
                  style={{
                    border: '1px solid #059669',
                    background: importing ? '#6ee7b7' : '#059669',
                    color: '#fff',
                    borderRadius: 10,
                    padding: '8px 16px',
                    cursor: importing ? 'not-allowed' : 'pointer',
                  }}
                >
                  {importing ? '导入中...' : '开始导入'}
                </button>
              </div>
            </form>
          ) : (
            <div style={{ color: '#6b7280' }}>仅管理员可录入</div>
          )}

          {importError ? (
            <div data-testid="package-drawing-import-error" style={{ marginTop: 12, color: '#b91c1c' }}>
              {importError}
            </div>
          ) : null}

          {importResult ? (
            <div data-testid="package-drawing-import-summary" style={{ marginTop: 12, display: 'grid', gap: 6 }}>
              <div>扫描行数：{importResult.rows_scanned || 0}</div>
              <div>导入模型数：{importResult.total || 0}</div>
              <div>成功：{importResult.success || 0}</div>
              <div>失败：{importResult.failed || 0}</div>
              {Array.isArray(importResult.errors) && importResult.errors.length ? (
                <div data-testid="package-drawing-import-errors" style={{ marginTop: 6 }}>
                  {importResult.errors.map((item, index) => (
                    <div key={`${item.sheet || 'sheet'}-${item.row || 0}-${index}`} style={{ color: '#92400e' }}>
                      [{item.sheet || '-'}:{item.row || '-'}] {item.model || '-'} {item.reason || 'error'}
                    </div>
                  ))}
                </div>
              ) : null}
            </div>
          ) : null}
        </section>
      ) : null}
    </div>
  );
};

export default PackageDrawingTool;
