import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import drugAdminManager from '../features/drugAdmin/DrugAdminManager';

const CARD = {
  background: '#fff',
  border: '1px solid #e5e7eb',
  borderRadius: '14px',
  boxShadow: '0 1px 2px rgba(0,0,0,0.04)',
};

const BUTTON = {
  padding: '8px 12px',
  borderRadius: '10px',
  border: '1px solid #d1d5db',
  background: '#fff',
  color: '#111827',
  cursor: 'pointer',
  fontWeight: 700,
};

const PRIMARY_BUTTON = {
  ...BUTTON,
  border: '1px solid #bfdbfe',
  background: '#eff6ff',
  color: '#1d4ed8',
};

const getRowStatusChip = (row) =>
  row?.ok
    ? { text: '可达', color: '#065f46', bg: '#d1fae5', border: '#a7f3d0' }
    : { text: '失败', color: '#991b1b', bg: '#fee2e2', border: '#fecaca' };

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
    [verifyResult],
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
        setError(e?.message || '加载省份列表失败');
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
    setInfo(`正在检测 ${selectedProvince}...`);
    try {
      const result = await drugAdminManager.resolveProvince(selectedProvince);
      setLastResolve(result);
      if (result?.ok && result?.url) {
        window.open(result.url, '_blank', 'noopener,noreferrer');
        setInfo(`${selectedProvince} 可访问（HTTP ${result?.code || '-'}）`);
      } else {
        setInfo(`${selectedProvince} 当前不可访问`);
      }
    } catch (e) {
      setError(e?.message || '解析请求失败');
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
      setError(e?.message || '批量校验失败');
    } finally {
      setVerifying(false);
    }
  };

  return (
    <div style={{ width: '100%', boxSizing: 'border-box' }} data-testid="drug-admin-page">
      <div style={{ ...CARD, padding: '16px', marginBottom: '14px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: '10px', alignItems: 'center', flexWrap: 'wrap' }}>
          <div style={{ fontSize: '1.1rem', fontWeight: 900, color: '#111827' }}>药监导航</div>
          <button type="button" onClick={() => navigate('/tools')} style={BUTTON}>
            返回工具页
          </button>
        </div>
        <div style={{ marginTop: '8px', color: '#6b7280', fontSize: '0.9rem', lineHeight: 1.6 }}>
          国家及各省药监站点入口。
          {(validatedOn || source) && (
            <div style={{ marginTop: '4px' }}>
              校验日期：{validatedOn || '-'}；来源：{source || '-'}
            </div>
          )}
        </div>
      </div>

      <div style={{ ...CARD, padding: '16px' }}>
        {loading ? (
          <div style={{ color: '#6b7280' }}>加载中...</div>
        ) : (
          <>
            <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap', alignItems: 'center' }}>
              <label htmlFor="drug-admin-province" style={{ color: '#374151', fontWeight: 700 }}>
                省份
              </label>
              <select
                id="drug-admin-province"
                value={selectedProvince}
                onChange={(e) => setSelectedProvince(e.target.value)}
                disabled={actionLoading || verifying}
                style={{
                  minWidth: '280px',
                  padding: '8px 10px',
                  borderRadius: '10px',
                  border: '1px solid #d1d5db',
                  background: '#fff',
                }}
              >
                {provinces.map((item) => (
                  <option key={item.name} value={item.name}>
                    {item.name}
                  </option>
                ))}
              </select>
              <button
                type="button"
                onClick={openSelected}
                disabled={actionLoading || verifying || !selectedProvince}
                style={PRIMARY_BUTTON}
                data-testid="drug-admin-open-selected"
              >
                {actionLoading ? '解析中...' : '打开省份站点'}
              </button>
              <button
                type="button"
                onClick={verifyAll}
                disabled={actionLoading || verifying || !provinces.length}
                style={BUTTON}
                data-testid="drug-admin-verify-all"
              >
                {verifying ? '校验中...' : '全部校验'}
              </button>
            </div>

            {(info || error) && (
              <div style={{ marginTop: '12px' }}>
                {!!info && <div style={{ color: '#065f46', marginBottom: error ? '6px' : 0 }}>{info}</div>}
                {!!error && <div style={{ color: '#991b1b' }}>{error}</div>}
              </div>
            )}

            {lastResolve && !lastResolve.ok && Array.isArray(lastResolve.errors) && lastResolve.errors.length > 0 && (
              <div style={{ marginTop: '12px', background: '#fff7ed', border: '1px solid #fed7aa', borderRadius: '10px', padding: '10px' }}>
                <div style={{ color: '#9a3412', fontWeight: 700, marginBottom: '6px' }}>最近一次解析错误</div>
                <ul style={{ margin: 0, paddingLeft: '18px', color: '#9a3412' }}>
                  {lastResolve.errors.slice(0, 6).map((line, idx) => (
                    <li key={`${idx}-${line}`} style={{ marginBottom: '4px' }}>
                      {line}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {verifyResult && (
              <div style={{ marginTop: '14px' }}>
                <div style={{ marginBottom: '8px', color: '#374151', fontWeight: 700 }}>
                  校验结果：总计 {verifyResult.total || 0}，成功 {verifyResult.success || 0}，失败 {verifyResult.failed || 0}
                </div>
                {!!failedRows.length && (
                  <div style={{ border: '1px solid #e5e7eb', borderRadius: '10px', overflow: 'hidden' }}>
                    <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.92rem' }}>
                      <thead>
                        <tr style={{ background: '#f9fafb' }}>
                          <th style={{ textAlign: 'left', padding: '10px', borderBottom: '1px solid #e5e7eb' }}>省份</th>
                          <th style={{ textAlign: 'left', padding: '10px', borderBottom: '1px solid #e5e7eb' }}>状态</th>
                          <th style={{ textAlign: 'left', padding: '10px', borderBottom: '1px solid #e5e7eb' }}>首个错误</th>
                        </tr>
                      </thead>
                      <tbody>
                        {failedRows.map((row) => {
                          const chip = getRowStatusChip(row);
                          return (
                            <tr key={row.province}>
                              <td style={{ padding: '10px', borderBottom: '1px solid #f3f4f6', color: '#111827' }}>{row.province}</td>
                              <td style={{ padding: '10px', borderBottom: '1px solid #f3f4f6' }}>
                                <span
                                  style={{
                                    padding: '2px 8px',
                                    borderRadius: '999px',
                                    fontWeight: 700,
                                    fontSize: '0.82rem',
                                    color: chip.color,
                                    background: chip.bg,
                                    border: `1px solid ${chip.border}`,
                                  }}
                                >
                                  {chip.text}
                                </span>
                              </td>
                              <td style={{ padding: '10px', borderBottom: '1px solid #f3f4f6', color: '#6b7280' }}>
                                {(row.errors && row.errors[0]) || '-'}
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
