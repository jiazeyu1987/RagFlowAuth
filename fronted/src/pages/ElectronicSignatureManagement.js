import React, { useCallback, useEffect, useState } from 'react';
import { electronicSignatureApi } from '../features/electronicSignature/api';

const cardStyle = {
  background: 'white',
  border: '1px solid #e5e7eb',
  borderRadius: '12px',
  padding: '16px',
  marginTop: '16px',
};

const tableStyle = {
  width: '100%',
  borderCollapse: 'collapse',
};

const cellStyle = {
  borderBottom: '1px solid #e5e7eb',
  textAlign: 'left',
  padding: '8px',
  verticalAlign: 'top',
  fontSize: '0.9rem',
};

const inputStyle = {
  padding: '8px 10px',
  borderRadius: '8px',
  border: '1px solid #d1d5db',
  width: '100%',
};

const buttonStyle = {
  border: '1px solid #d1d5db',
  borderRadius: '8px',
  background: 'white',
  color: '#111827',
  cursor: 'pointer',
  padding: '8px 12px',
};

const primaryButtonStyle = {
  ...buttonStyle,
  border: 'none',
  background: '#2563eb',
  color: 'white',
};

const TEXT = {
  title: '\u7535\u5b50\u7b7e\u540d\u7ba1\u7406',
  loading: '\u6b63\u5728\u52a0\u8f7d\u7535\u5b50\u7b7e\u540d\u6570\u636e...',
  loadError: '\u52a0\u8f7d\u7535\u5b50\u7b7e\u540d\u6570\u636e\u5931\u8d25',
  detailError: '\u52a0\u8f7d\u7b7e\u540d\u8be6\u60c5\u5931\u8d25',
  verifyError: '\u9a8c\u7b7e\u5931\u8d25',
  search: '\u67e5\u8be2',
  reset: '\u91cd\u7f6e',
  total: '\u603b\u6570',
  noData: '\u6682\u65e0\u7535\u5b50\u7b7e\u540d\u8bb0\u5f55',
  filters: '\u7b5b\u9009\u6761\u4ef6',
  signatureId: '\u7b7e\u540d ID',
  recordType: '\u8bb0\u5f55\u7c7b\u578b',
  recordId: '\u8bb0\u5f55 ID',
  action: '\u64cd\u4f5c',
  signer: '\u7b7e\u7f72\u4eba',
  status: '\u72b6\u6001',
  signedAt: '\u7b7e\u7f72\u65f6\u95f4',
  meaning: '\u7b7e\u540d\u542b\u4e49',
  reason: '\u7b7e\u7f72\u539f\u56e0',
  verified: '\u9a8c\u7b7e\u7ed3\u679c',
  view: '\u67e5\u770b',
  verify: '\u9a8c\u7b7e',
  detail: '\u7b7e\u540d\u8be6\u60c5',
  recordPayload: '\u8bb0\u5f55\u5feb\u7167',
  recordHash: '\u8bb0\u5f55\u54c8\u5e0c',
  signatureHash: '\u7b7e\u540d\u54c8\u5e0c',
  signTokenId: '\u6311\u6218 ID',
  closeHint: '\u9ed8\u8ba4\u663e\u793a\u6700\u65b0 100 \u6761',
  yes: '\u901a\u8fc7',
  no: '\u672a\u901a\u8fc7',
  notSelected: '\u8bf7\u5148\u9009\u62e9\u4e00\u6761\u7b7e\u540d\u8bb0\u5f55',
};

const formatTime = (ms) => {
  if (!ms) return '-';
  const n = Number(ms);
  if (!Number.isFinite(n) || n <= 0) return '-';
  return new Date(n).toLocaleString();
};

const prettyJson = (value) => {
  try {
    return JSON.stringify(value ?? null, null, 2);
  } catch {
    return String(value ?? '');
  }
};

const INITIAL_FILTERS = {
  record_type: '',
  record_id: '',
  action: '',
  signed_by: '',
  status: '',
};

const ElectronicSignatureManagement = () => {
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [verifyLoading, setVerifyLoading] = useState(false);
  const [error, setError] = useState('');
  const [filters, setFilters] = useState(INITIAL_FILTERS);
  const [signatures, setSignatures] = useState([]);
  const [total, setTotal] = useState(0);
  const [selectedSignatureId, setSelectedSignatureId] = useState('');
  const [selectedSignature, setSelectedSignature] = useState(null);

  const loadSignatures = useCallback(async (nextFilters, currentSelectedSignatureId = '') => {
    setError('');
    setLoading(true);
    try {
      const response = await electronicSignatureApi.listSignatures({ ...nextFilters, limit: 100, offset: 0 });
      const items = response.items || [];
      setSignatures(items);
      setTotal(Number(response.total || 0));
      if (items.length === 0) {
        setSelectedSignatureId('');
        setSelectedSignature(null);
        return;
      }
      const nextId = items.some((item) => item.signature_id === currentSelectedSignatureId)
        ? currentSelectedSignatureId
        : items[0].signature_id;
      setSelectedSignatureId(nextId);
      const detail = await electronicSignatureApi.getSignature(nextId);
      setSelectedSignature(detail);
    } catch (e) {
      setError(e.message || TEXT.loadError);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadSignatures(INITIAL_FILTERS);
  }, [loadSignatures]);

  const handleSearch = async () => {
    await loadSignatures(filters, selectedSignatureId);
  };

  const handleReset = async () => {
    setFilters(INITIAL_FILTERS);
    await loadSignatures(INITIAL_FILTERS);
  };

  const handleSelectSignature = async (signatureId) => {
    setSelectedSignatureId(signatureId);
    setDetailLoading(true);
    setError('');
    try {
      const detail = await electronicSignatureApi.getSignature(signatureId);
      setSelectedSignature(detail);
    } catch (e) {
      setError(e.message || TEXT.detailError);
    } finally {
      setDetailLoading(false);
    }
  };

  const handleVerifySignature = async () => {
    if (!selectedSignatureId) {
      setError(TEXT.notSelected);
      return;
    }
    setVerifyLoading(true);
    setError('');
    try {
      const result = await electronicSignatureApi.verifySignature(selectedSignatureId);
      setSelectedSignature((prev) => (prev ? { ...prev, verified: Boolean(result.verified) } : prev));
    } catch (e) {
      setError(e.message || TEXT.verifyError);
    } finally {
      setVerifyLoading(false);
    }
  };

  if (loading) {
    return <div style={{ padding: '12px' }}>{TEXT.loading}</div>;
  }

  return (
    <div style={{ maxWidth: '1400px' }} data-testid="electronic-signature-management-page">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
        <h2 style={{ margin: 0 }}>{TEXT.title}</h2>
        <div style={{ color: '#6b7280', fontSize: '0.9rem' }}>{TEXT.closeHint}</div>
      </div>

      {error ? (
        <div data-testid="electronic-signature-error" style={{ marginTop: '12px', padding: '10px 12px', background: '#fef2f2', color: '#991b1b', borderRadius: '10px' }}>
          {error}
        </div>
      ) : null}

      <div style={cardStyle}>
        <h3 style={{ marginTop: 0 }}>{TEXT.filters}</h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '12px' }}>
          <label style={{ display: 'grid', gap: '6px' }}>
            <span>{TEXT.recordType}</span>
            <input value={filters.record_type} onChange={(e) => setFilters((prev) => ({ ...prev, record_type: e.target.value }))} style={inputStyle} />
          </label>
          <label style={{ display: 'grid', gap: '6px' }}>
            <span>{TEXT.recordId}</span>
            <input value={filters.record_id} onChange={(e) => setFilters((prev) => ({ ...prev, record_id: e.target.value }))} style={inputStyle} />
          </label>
          <label style={{ display: 'grid', gap: '6px' }}>
            <span>{TEXT.action}</span>
            <input value={filters.action} onChange={(e) => setFilters((prev) => ({ ...prev, action: e.target.value }))} style={inputStyle} />
          </label>
          <label style={{ display: 'grid', gap: '6px' }}>
            <span>{TEXT.signer}</span>
            <input value={filters.signed_by} onChange={(e) => setFilters((prev) => ({ ...prev, signed_by: e.target.value }))} style={inputStyle} />
          </label>
          <label style={{ display: 'grid', gap: '6px' }}>
            <span>{TEXT.status}</span>
            <input value={filters.status} onChange={(e) => setFilters((prev) => ({ ...prev, status: e.target.value }))} style={inputStyle} />
          </label>
        </div>
        <div style={{ display: 'flex', gap: '8px', marginTop: '12px', flexWrap: 'wrap' }}>
          <button type="button" onClick={handleSearch} style={primaryButtonStyle}>{TEXT.search}</button>
          <button type="button" onClick={handleReset} style={buttonStyle}>{TEXT.reset}</button>
          <div style={{ marginLeft: 'auto', color: '#6b7280', alignSelf: 'center' }}>{TEXT.total}: {total}</div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1.4fr) minmax(360px, 1fr)', gap: '16px' }}>
        <div style={cardStyle}>
          <div style={{ overflowX: 'auto' }}>
            <table style={tableStyle}>
              <thead>
                <tr>
                  <th style={cellStyle}>{TEXT.signatureId}</th>
                  <th style={cellStyle}>{TEXT.recordType}</th>
                  <th style={cellStyle}>{TEXT.recordId}</th>
                  <th style={cellStyle}>{TEXT.action}</th>
                  <th style={cellStyle}>{TEXT.signer}</th>
                  <th style={cellStyle}>{TEXT.signedAt}</th>
                  <th style={cellStyle}>{TEXT.status}</th>
                  <th style={cellStyle}>{TEXT.verified}</th>
                  <th style={cellStyle}>{TEXT.view}</th>
                </tr>
              </thead>
              <tbody>
                {signatures.length === 0 ? (
                  <tr>
                    <td style={cellStyle} colSpan={9}>{TEXT.noData}</td>
                  </tr>
                ) : signatures.map((item) => (
                  <tr key={item.signature_id} style={{ background: item.signature_id === selectedSignatureId ? '#eff6ff' : 'transparent' }}>
                    <td style={cellStyle}>{item.signature_id}</td>
                    <td style={cellStyle}>{item.record_type}</td>
                    <td style={cellStyle}>{item.record_id}</td>
                    <td style={cellStyle}>{item.action}</td>
                    <td style={cellStyle}>{item.signed_by_username || item.signed_by}</td>
                    <td style={cellStyle}>{formatTime(item.signed_at_ms)}</td>
                    <td style={cellStyle}>{item.status}</td>
                    <td style={cellStyle}>{item.verified === true ? TEXT.yes : item.verified === false ? TEXT.no : '-'}</td>
                    <td style={cellStyle}>
                      <button type="button" onClick={() => handleSelectSignature(item.signature_id)} style={buttonStyle}>{TEXT.view}</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div style={cardStyle}>
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: '8px', alignItems: 'center', flexWrap: 'wrap' }}>
            <h3 style={{ margin: 0 }}>{TEXT.detail}</h3>
            <button
              type="button"
              onClick={handleVerifySignature}
              disabled={!selectedSignatureId || verifyLoading}
              style={{ ...buttonStyle, cursor: !selectedSignatureId || verifyLoading ? 'not-allowed' : 'pointer' }}
            >
              {verifyLoading ? `${TEXT.verify}...` : TEXT.verify}
            </button>
          </div>

          {detailLoading ? (
            <div style={{ marginTop: '12px', color: '#6b7280' }}>{TEXT.loading}</div>
          ) : selectedSignature ? (
            <div style={{ display: 'grid', gap: '10px', marginTop: '12px' }}>
              <div><strong>{TEXT.signatureId}:</strong> {selectedSignature.signature_id}</div>
              <div><strong>{TEXT.recordType}:</strong> {selectedSignature.record_type}</div>
              <div><strong>{TEXT.recordId}:</strong> {selectedSignature.record_id}</div>
              <div><strong>{TEXT.action}:</strong> {selectedSignature.action}</div>
              <div><strong>{TEXT.signer}:</strong> {selectedSignature.signed_by_username || selectedSignature.signed_by}</div>
              <div><strong>{TEXT.signedAt}:</strong> {formatTime(selectedSignature.signed_at_ms)}</div>
              <div><strong>{TEXT.meaning}:</strong> {selectedSignature.meaning}</div>
              <div><strong>{TEXT.reason}:</strong> {selectedSignature.reason}</div>
              <div><strong>{TEXT.status}:</strong> {selectedSignature.status}</div>
              <div><strong>{TEXT.verified}:</strong> {selectedSignature.verified === true ? TEXT.yes : selectedSignature.verified === false ? TEXT.no : '-'}</div>
              <div><strong>{TEXT.signTokenId}:</strong> {selectedSignature.sign_token_id}</div>
              <div><strong>{TEXT.recordHash}:</strong> <span style={{ wordBreak: 'break-all' }}>{selectedSignature.record_hash}</span></div>
              <div><strong>{TEXT.signatureHash}:</strong> <span style={{ wordBreak: 'break-all' }}>{selectedSignature.signature_hash}</span></div>
              <div>
                <strong>{TEXT.recordPayload}:</strong>
                <pre style={{ marginTop: '8px', padding: '12px', background: '#f9fafb', borderRadius: '8px', overflowX: 'auto', fontSize: '0.85rem' }}>
                  {prettyJson(selectedSignature.record_payload)}
                </pre>
              </div>
            </div>
          ) : (
            <div style={{ marginTop: '12px', color: '#6b7280' }}>{TEXT.notSelected}</div>
          )}
        </div>
      </div>
    </div>
  );
};

export default ElectronicSignatureManagement;
