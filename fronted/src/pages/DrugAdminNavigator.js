import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import drugAdminManager from '../features/drugAdmin/DrugAdminManager';
import { normalizeDisplayError } from '../shared/utils/displayError';

const getRowStatusChip = (row) =>
  row?.ok
    ? { text: '可达', className: 'medui-badge medui-badge--success' }
    : { text: '失败', className: 'medui-badge medui-badge--danger' };

export default function DrugAdminNavigator() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [verifying, setVerifying] = useState(false);
  const [error, setError] = useState('');
  const [info, setInfo] = useState('');
  const [validatedOn, setValidatedOn] = useState('');
  const [source, setSource] = useState('');
  const [provinces, setProvinces] = useState([]);
  const [selectedProvince, setSelectedProvince] = useState('');
  const [lastResolve, setLastResolve] = useState(null);
  const [verifyResult, setVerifyResult] = useState(null);

  const failedRows = useMemo(
    () => (Array.isArray(verifyResult?.rows) ? verifyResult.rows.filter((row) => !row?.ok) : []),
    [verifyResult]
  );

  useEffect(() => {
    let alive = true;

    const run = async () => {
      setLoading(true);
      setError('');
      try {
        const data = await drugAdminManager.listProvinces();
        if (!alive) return;
        const list = Array.isArray(data?.provinces) ? data.provinces : [];
        setValidatedOn(String(data?.validated_on || ''));
        setSource(String(data?.source || ''));
        setProvinces(list);
        setSelectedProvince((prev) => (prev ? prev : String(list[0]?.name || '')));
      } catch (e) {
        if (!alive) return;
        setError(normalizeDisplayError(e?.message ?? e, '加载省份列表失败'));
      } finally {
        if (alive) setLoading(false);
      }
    };

    run();
    return () => {
      alive = false;
    };
  }, []);

  const openSelected = async () => {
    if (!selectedProvince) return;
    setActionLoading(true);
    setError('');
    setInfo(`正在检测 ${selectedProvince} ...`);
    try {
      const result = await drugAdminManager.resolveProvince(selectedProvince);
      setLastResolve(result);
      if (result?.ok && result?.url) {
        window.open(result.url, '_blank', 'noopener,noreferrer');
        setInfo(`${selectedProvince} 可访问（状态码 ${result?.code || '-'}）`);
      } else {
        setInfo(`${selectedProvince} 当前不可访问`);
      }
    } catch (e) {
      setError(normalizeDisplayError(e?.message ?? e, '解析请求失败'));
    } finally {
      setActionLoading(false);
    }
  };

  const verifyAll = async () => {
    setVerifying(true);
    setError('');
    setInfo('正在校验全部省份站点...');
    try {
      const result = await drugAdminManager.verifyAll();
      setVerifyResult(result);
      setInfo(`校验完成：总计 ${result?.total || 0}，成功 ${result?.success || 0}，失败 ${result?.failed || 0}`);
    } catch (e) {
      setError(normalizeDisplayError(e?.message ?? e, '批量校验失败'));
    } finally {
      setVerifying(false);
    }
  };

  return (
    <div className="admin-med-page" data-testid="drug-admin-page">
      <section className="medui-surface medui-card-pad">
        <div className="admin-med-head">
          <div>
            <h2 className="admin-med-title" style={{ margin: 0 }}>药监导航</h2>
            <div className="admin-med-inline-note" style={{ marginTop: 6 }}>
              国家及各省药监站点入口。{validatedOn || source ? `校验日期：${validatedOn || '-'}；来源：${source || '-'}` : ''}
            </div>
          </div>
          <button type="button" onClick={() => navigate('/tools')} className="medui-btn medui-btn--secondary">
            返回工具页
          </button>
        </div>
      </section>

      <section className="medui-surface medui-card-pad">
        {loading ? (
          <div className="medui-empty">加载中...</div>
        ) : (
          <>
            <div className="admin-med-actions">
              <label style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                省份
                <select
                  value={selectedProvince}
                  onChange={(e) => setSelectedProvince(e.target.value)}
                  disabled={actionLoading || verifying}
                  className="medui-select"
                  style={{ minWidth: 280 }}
                  id="drug-admin-province"
                >
                  {provinces.map((item) => (
                    <option key={item.name} value={item.name}>
                      {item.name}
                    </option>
                  ))}
                </select>
              </label>

              <button
                type="button"
                onClick={openSelected}
                disabled={actionLoading || verifying || !selectedProvince}
                className="medui-btn medui-btn--primary"
                data-testid="drug-admin-open-selected"
              >
                {actionLoading ? '处理中...' : '打开省份站点'}
              </button>
              <button
                type="button"
                onClick={verifyAll}
                disabled={actionLoading || verifying || !provinces.length}
                className="medui-btn medui-btn--secondary"
                data-testid="drug-admin-verify-all"
              >
                {verifying ? '校验中...' : '全部校验'}
              </button>
            </div>

            {info ? <div className="admin-med-success" style={{ marginTop: 12 }}>{info}</div> : null}
            {error ? <div className="admin-med-danger" style={{ marginTop: 12 }}>{error}</div> : null}

            {lastResolve && !lastResolve.ok && Array.isArray(lastResolve.errors) && lastResolve.errors.length > 0 ? (
              <div className="medui-surface medui-card-pad" style={{ marginTop: 12, borderColor: '#f4d8ac', background: '#fff9ef' }}>
                <div style={{ color: '#9a5b11', fontWeight: 700, marginBottom: 6 }}>最近一次解析错误</div>
                <ul style={{ margin: 0, paddingLeft: 18, color: '#9a5b11' }}>
                  {lastResolve.errors.slice(0, 6).map((line, idx) => (
                    <li key={`${idx}-${line}`} style={{ marginBottom: 4 }}>
                      {line}
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}

            {verifyResult ? (
              <div style={{ marginTop: 14 }}>
                <div className="admin-med-inline-note" style={{ marginBottom: 8 }}>
                  校验结果：总计 {verifyResult.total || 0}，成功 {verifyResult.success || 0}，失败 {verifyResult.failed || 0}
                </div>

                {failedRows.length > 0 ? (
                  <div className="medui-table-wrap">
                    <table className="medui-table">
                      <thead>
                        <tr>
                          <th>省份</th>
                          <th>状态</th>
                          <th>首个错误</th>
                        </tr>
                      </thead>
                      <tbody>
                        {failedRows.map((row) => {
                          const chip = getRowStatusChip(row);
                          return (
                            <tr key={row.province}>
                              <td>{row.province}</td>
                              <td>
                                <span className={chip.className}>{chip.text}</span>
                              </td>
                              <td>{(row.errors && row.errors[0]) || '-'}</td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <div className="medui-empty">当前无失败站点</div>
                )}
              </div>
            ) : null}
          </>
        )}
      </section>
    </div>
  );
}
