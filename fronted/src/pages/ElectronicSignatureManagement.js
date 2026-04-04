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

const tabButtonStyle = {
  ...buttonStyle,
  padding: '10px 16px',
};

const TEXT = {
  title: '\u7535\u5b50\u7b7e\u540d\u7ba1\u7406',
  loading: '\u6b63\u5728\u52a0\u8f7d\u7535\u5b50\u7b7e\u540d\u6570\u636e...',
  loadError: '\u52a0\u8f7d\u7535\u5b50\u7b7e\u540d\u6570\u636e\u5931\u8d25',
  detailError: '\u52a0\u8f7d\u7b7e\u540d\u8be6\u60c5\u5931\u8d25',
  verifyError: '\u9a8c\u7b7e\u5931\u8d25',
  verifySuccess: '\u9a8c\u7b7e\u5b8c\u6210',
  search: '\u67e5\u8be2',
  reset: '\u91cd\u7f6e',
  total: '\u603b\u6570',
  noData: '\u6682\u65e0\u7535\u5b50\u7b7e\u540d\u8bb0\u5f55',
  filters: '\u7b5b\u9009\u6761\u4ef6',
  signatureId: '\u7b7e\u540d ID',
  recordType: '\u8bb0\u5f55\u7c7b\u578b',
  recordId: '\u8bb0\u5f55 ID',
  action: '\u64cd\u4f5c',
  fullName: '\u59d3\u540d',
  signer: '\u7b7e\u7f72\u4eba',
  status: '\u72b6\u6001',
  signedAt: '\u7b7e\u7f72\u65f6\u95f4',
  meaning: '\u7b7e\u540d\u542b\u4e49',
  reason: '\u7b7e\u7f72\u539f\u56e0',
  verified: '\u9a8c\u7b7e\u7ed3\u679c',
  view: '\u67e5\u770b',
  verify: '\u9a8c\u7b7e',
  detail: '\u7b7e\u540d\u8be6\u60c5',
  recordHash: '\u8bb0\u5f55\u54c8\u5e0c',
  signatureHash: '\u7b7e\u540d\u54c8\u5e0c',
  signTokenId: '\u6311\u6218 ID',
  closeHint: '\u9ed8\u8ba4\u663e\u793a\u6700\u65b0 100 \u6761',
  yes: '\u901a\u8fc7',
  no: '\u672a\u901a\u8fc7',
  verifyPassed: '\u9a8c\u7b7e\u901a\u8fc7',
  verifyFailed: '\u9a8c\u7b7e\u672a\u901a\u8fc7',
  notSelected: '\u8bf7\u5148\u9009\u62e9\u4e00\u6761\u7b7e\u540d\u8bb0\u5f55',
  authorizationTitle: '\u7b7e\u540d\u6388\u6743\u7ba1\u7406',
  authorizationStatus: '\u6388\u6743\u72b6\u6001',
  authorizationEnabled: '\u5df2\u6388\u6743',
  authorizationDisabled: '\u672a\u6388\u6743',
  authorizationAction: '\u6388\u6743\u64cd\u4f5c',
  authorizationUpdateError: '\u66f4\u65b0\u7b7e\u540d\u6388\u6743\u5931\u8d25',
  authorizationLoadError: '\u52a0\u8f7d\u7b7e\u540d\u6388\u6743\u5931\u8d25',
  enable: '\u542f\u7528',
  disable: '\u505c\u7528',
  signatureTab: '\u7535\u5b50\u7b7e\u540d\u7ba1\u7406',
  authorizationTab: '\u7b7e\u540d\u6388\u6743\u7ba1\u7406',
};

const formatTime = (ms) => {
  if (!ms) return '-';
  const n = Number(ms);
  if (!Number.isFinite(n) || n <= 0) return '-';
  return new Date(n).toLocaleString();
};

const RECORD_TYPE_LABELS = {
  operation_approval_request: '\u64cd\u4f5c\u5ba1\u6279',
  knowledge_document_review: '\u6587\u6863\u5ba1\u6838',
};

const ACTION_LABELS = {
  operation_approval_approve: '\u5ba1\u6279\u901a\u8fc7',
  operation_approval_reject: '\u5ba1\u6279\u9a73\u56de',
  document_approve: '\u6587\u6863\u6279\u51c6',
  document_reject: '\u6587\u6863\u9a73\u56de',
};

const STATUS_LABELS = {
  signed: '\u5df2\u7b7e\u7f72',
};

const getRecordTypeLabel = (value) => RECORD_TYPE_LABELS[String(value || '')] || String(value || '-');
const getActionLabel = (value) => ACTION_LABELS[String(value || '')] || String(value || '-');
const getStatusLabel = (value) => STATUS_LABELS[String(value || '')] || String(value || '-');
const getSignerFullName = (item) => item?.signed_by_full_name || '-';
const getSignerLabel = (item) =>
  item?.signed_by_username || item?.signed_by || '-';

const RECORD_TYPE_OPTIONS = [
  { value: '', label: '全部' },
  { value: 'operation_approval_request', label: getRecordTypeLabel('operation_approval_request') },
  { value: 'knowledge_document_review', label: getRecordTypeLabel('knowledge_document_review') },
];

const ACTION_OPTIONS = [
  { value: '', label: '全部' },
  { value: 'operation_approval_approve', label: getActionLabel('operation_approval_approve') },
  { value: 'operation_approval_reject', label: getActionLabel('operation_approval_reject') },
  { value: 'document_approve', label: getActionLabel('document_approve') },
  { value: 'document_reject', label: getActionLabel('document_reject') },
];

const toTimestampMs = (value, endOfMinute = false) => {
  const text = String(value || '').trim();
  if (!text) return undefined;
  const normalized = endOfMinute ? `${text}:59` : `${text}:00`;
  const timestamp = new Date(normalized).getTime();
  return Number.isFinite(timestamp) ? timestamp : undefined;
};

const INITIAL_FILTERS = {
  record_type: '',
  action: '',
  signed_by: '',
  signed_at_from: '',
  signed_at_to: '',
};

const ElectronicSignatureManagement = () => {
  const [activeTab, setActiveTab] = useState('signatures');
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [verifyLoading, setVerifyLoading] = useState(false);
  const [error, setError] = useState('');
  const [verifyMessage, setVerifyMessage] = useState('');
  const [filters, setFilters] = useState(INITIAL_FILTERS);
  const [displaySignatures, setDisplaySignatures] = useState([]);
  const [total, setTotal] = useState(0);
  const [selectedSignatureId, setSelectedSignatureId] = useState('');
  const [selectedSignature, setSelectedSignature] = useState(null);
  const [authorizationLoading, setAuthorizationLoading] = useState(true);
  const [authorizations, setAuthorizations] = useState([]);

  const loadSignatures = useCallback(async (nextFilters, currentSelectedSignatureId = '') => {
    setError('');
    setVerifyMessage('');
    setLoading(true);
    try {
      const response = await electronicSignatureApi.listSignatures({
        record_type: nextFilters?.record_type,
        action: nextFilters?.action,
        signed_by: nextFilters?.signed_by,
        signed_at_from_ms: toTimestampMs(nextFilters?.signed_at_from, false),
        signed_at_to_ms: toTimestampMs(nextFilters?.signed_at_to, true),
        limit: 100,
        offset: 0,
      });
      const items = response.items || [];
      setDisplaySignatures(items);
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

  const loadAuthorizations = useCallback(async () => {
    setAuthorizationLoading(true);
    try {
      const response = await electronicSignatureApi.listAuthorizations({ limit: 200 });
      setAuthorizations(response.items || []);
    } catch (e) {
      setError(e.message || TEXT.authorizationLoadError);
    } finally {
      setAuthorizationLoading(false);
    }
  }, []);

  useEffect(() => {
    loadAuthorizations();
  }, [loadAuthorizations]);

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
    setVerifyMessage('');
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
    setVerifyMessage('');
    try {
      const result = await electronicSignatureApi.verifySignature(selectedSignatureId);
      const verified = Boolean(result.verified);
      setSelectedSignature((prev) => (prev ? { ...prev, verified } : prev));
      setDisplaySignatures((prev) => prev.map((item) => (
        item.signature_id === selectedSignatureId ? { ...item, verified } : item
      )));
      setVerifyMessage(verified ? TEXT.verifyPassed : TEXT.verifyFailed);
    } catch (e) {
      setError(e.message || TEXT.verifyError);
    } finally {
      setVerifyLoading(false);
    }
  };

  const handleToggleAuthorization = async (userId, nextEnabled) => {
    setError('');
    try {
      await electronicSignatureApi.updateAuthorization(userId, {
        electronic_signature_enabled: nextEnabled,
      });
      await loadAuthorizations();
    } catch (e) {
      setError(e.message || TEXT.authorizationUpdateError);
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

      {verifyMessage ? (
        <div style={{ marginTop: '12px', padding: '10px 12px', background: '#ecfdf5', color: '#166534', borderRadius: '10px' }}>
          {verifyMessage}
        </div>
      ) : null}

      <div style={{ display: 'flex', gap: '8px', marginTop: '16px', flexWrap: 'wrap' }}>
        <button
          type="button"
          onClick={() => setActiveTab('signatures')}
          style={activeTab === 'signatures' ? { ...primaryButtonStyle, padding: '10px 16px' } : tabButtonStyle}
        >
          {TEXT.signatureTab}
        </button>
        <button
          type="button"
          onClick={() => setActiveTab('authorizations')}
          style={activeTab === 'authorizations' ? { ...primaryButtonStyle, padding: '10px 16px' } : tabButtonStyle}
        >
          {TEXT.authorizationTab}
        </button>
      </div>

      {activeTab === 'signatures' ? (
        <>
          <div style={cardStyle}>
            <h3 style={{ marginTop: 0 }}>{TEXT.filters}</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '12px' }}>
              <label style={{ display: 'grid', gap: '6px' }}>
                <span>{TEXT.recordType}</span>
                <select
                  value={filters.record_type}
                  onChange={(e) => setFilters((prev) => ({ ...prev, record_type: e.target.value }))}
                  style={inputStyle}
                >
                  {RECORD_TYPE_OPTIONS.map((option) => (
                    <option key={option.value} value={option.value}>{option.label}</option>
                  ))}
                </select>
              </label>
              <label style={{ display: 'grid', gap: '6px' }}>
                <span>{TEXT.action}</span>
                <select
                  value={filters.action}
                  onChange={(e) => setFilters((prev) => ({ ...prev, action: e.target.value }))}
                  style={inputStyle}
                >
                  {ACTION_OPTIONS.map((option) => (
                    <option key={option.value} value={option.value}>{option.label}</option>
                  ))}
                </select>
              </label>
              <label style={{ display: 'grid', gap: '6px' }}>
                <span>{TEXT.signer}</span>
                <input value={filters.signed_by} onChange={(e) => setFilters((prev) => ({ ...prev, signed_by: e.target.value }))} style={inputStyle} />
              </label>
              <label style={{ display: 'grid', gap: '6px' }}>
                <span>{`${TEXT.signedAt}起`}</span>
                <input
                  type="datetime-local"
                  value={filters.signed_at_from}
                  onChange={(e) => setFilters((prev) => ({ ...prev, signed_at_from: e.target.value }))}
                  style={inputStyle}
                />
              </label>
              <label style={{ display: 'grid', gap: '6px' }}>
                <span>{`${TEXT.signedAt}止`}</span>
                <input
                  type="datetime-local"
                  value={filters.signed_at_to}
                  onChange={(e) => setFilters((prev) => ({ ...prev, signed_at_to: e.target.value }))}
                  style={inputStyle}
                />
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
                      <th style={cellStyle}>{TEXT.recordType}</th>
                      <th style={cellStyle}>{TEXT.action}</th>
                      <th style={cellStyle}>{TEXT.fullName}</th>
                      <th style={cellStyle}>{TEXT.signer}</th>
                      <th style={cellStyle}>{TEXT.signedAt}</th>
                      <th style={cellStyle}>{TEXT.status}</th>
                      <th style={cellStyle}>{TEXT.verified}</th>
                      <th style={cellStyle}>{TEXT.view}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {displaySignatures.length === 0 ? (
                      <tr>
                        <td style={cellStyle} colSpan={8}>{TEXT.noData}</td>
                      </tr>
                    ) : displaySignatures.map((item) => (
                      <tr key={item.signature_id} style={{ background: item.signature_id === selectedSignatureId ? '#eff6ff' : 'transparent' }}>
                        <td style={cellStyle}>{getRecordTypeLabel(item.record_type)}</td>
                        <td style={cellStyle}>{getActionLabel(item.action)}</td>
                        <td style={cellStyle}>{getSignerFullName(item)}</td>
                        <td style={cellStyle}>{getSignerLabel(item)}</td>
                        <td style={cellStyle}>{formatTime(item.signed_at_ms)}</td>
                        <td style={cellStyle}>{getStatusLabel(item.status)}</td>
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
                  <div><strong>{TEXT.recordType}:</strong> {getRecordTypeLabel(selectedSignature.record_type)}</div>
                  <div><strong>{TEXT.action}:</strong> {getActionLabel(selectedSignature.action)}</div>
                  <div><strong>{TEXT.signer}:</strong> {getSignerLabel(selectedSignature)}</div>
                  <div><strong>{TEXT.signedAt}:</strong> {formatTime(selectedSignature.signed_at_ms)}</div>
                  <div><strong>{TEXT.meaning}:</strong> {selectedSignature.meaning}</div>
                  <div><strong>{TEXT.reason}:</strong> {selectedSignature.reason}</div>
                  <div><strong>{TEXT.status}:</strong> {getStatusLabel(selectedSignature.status)}</div>
                  <div><strong>{TEXT.verified}:</strong> {selectedSignature.verified === true ? TEXT.yes : selectedSignature.verified === false ? TEXT.no : '-'}</div>
                  <div><strong>{TEXT.signTokenId}:</strong> {selectedSignature.sign_token_id}</div>
                  <div><strong>{TEXT.recordHash}:</strong> <span style={{ wordBreak: 'break-all' }}>{selectedSignature.record_hash}</span></div>
                  <div><strong>{TEXT.signatureHash}:</strong> <span style={{ wordBreak: 'break-all' }}>{selectedSignature.signature_hash}</span></div>
                </div>
              ) : (
                <div style={{ marginTop: '12px', color: '#6b7280' }}>{TEXT.notSelected}</div>
              )}
            </div>
          </div>
        </>
      ) : (
        <div style={cardStyle}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
            <h3 style={{ margin: 0 }}>{TEXT.authorizationTitle}</h3>
            <div style={{ color: '#6b7280', fontSize: '0.9rem' }}>{TEXT.authorizationAction}</div>
          </div>

          <div style={{ overflowX: 'auto', marginTop: '12px' }}>
            <table style={tableStyle}>
              <thead>
                <tr>
                  <th style={cellStyle}>{TEXT.signer}</th>
                  <th style={cellStyle}>{TEXT.status}</th>
                  <th style={cellStyle}>{TEXT.authorizationStatus}</th>
                  <th style={cellStyle}>{TEXT.signedAt}</th>
                  <th style={cellStyle}>{TEXT.authorizationAction}</th>
                </tr>
              </thead>
              <tbody>
                {authorizationLoading ? (
                  <tr>
                    <td style={cellStyle} colSpan={5}>{TEXT.loading}</td>
                  </tr>
                ) : authorizations.length === 0 ? (
                  <tr>
                    <td style={cellStyle} colSpan={5}>{TEXT.noData}</td>
                  </tr>
                ) : authorizations.map((item) => (
                  <tr key={item.user_id}>
                    <td style={cellStyle}>
                      <div>{item.full_name || item.username}</div>
                      <div style={{ color: '#6b7280', fontSize: '0.8rem' }}>{item.username}</div>
                    </td>
                    <td style={cellStyle}>{item.status || '-'}</td>
                    <td style={cellStyle}>
                      {item.electronic_signature_enabled ? TEXT.authorizationEnabled : TEXT.authorizationDisabled}
                    </td>
                    <td style={cellStyle}>{formatTime(item.last_login_at_ms)}</td>
                    <td style={cellStyle}>
                      <button
                        type="button"
                        onClick={() => handleToggleAuthorization(item.user_id, !item.electronic_signature_enabled)}
                        style={item.electronic_signature_enabled ? buttonStyle : primaryButtonStyle}
                      >
                        {item.electronic_signature_enabled ? TEXT.disable : TEXT.enable}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};

export default ElectronicSignatureManagement;
