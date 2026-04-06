import React from 'react';

import useElectronicSignatureManagementPage from '../features/electronicSignature/useElectronicSignatureManagementPage';

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
  title: '电子签名管理',
  loading: '正在加载电子签名数据...',
  search: '查询',
  reset: '重置',
  total: '总数',
  noData: '暂无电子签名记录',
  filters: '筛选条件',
  signatureId: '签名 ID',
  recordType: '记录类型',
  recordId: '记录 ID',
  action: '操作',
  fullName: '姓名',
  signer: '签署人',
  status: '状态',
  signedAt: '签署时间',
  meaning: '签名含义',
  reason: '签署原因',
  verified: '验签结果',
  view: '查看',
  verify: '验签',
  detail: '签名详情',
  recordHash: '记录哈希',
  signatureHash: '签名哈希',
  signTokenId: '挑战 ID',
  closeHint: '默认显示最新 100 条',
  yes: '通过',
  no: '未通过',
  notSelected: '请先选择一条签名记录',
  authorizationTitle: '签名授权管理',
  authorizationStatus: '授权状态',
  authorizationEnabled: '已授权',
  authorizationDisabled: '未授权',
  authorizationAction: '授权操作',
  enable: '启用',
  disable: '停用',
  signatureTab: '电子签名管理',
  authorizationTab: '签名授权管理',
};

const RECORD_TYPE_LABELS = {
  operation_approval_request: '操作审批',
  knowledge_document_review: '文档审核',
};

const ACTION_LABELS = {
  operation_approval_approve: '审批通过',
  operation_approval_reject: '审批驳回',
  document_approve: '文档批准',
  document_reject: '文档驳回',
};

const STATUS_LABELS = {
  signed: '已签署',
};

const getRecordTypeLabel = (value) =>
  RECORD_TYPE_LABELS[String(value || '')] || String(value || '-');
const getActionLabel = (value) => ACTION_LABELS[String(value || '')] || String(value || '-');
const getStatusLabel = (value) => STATUS_LABELS[String(value || '')] || String(value || '-');
const getSignerFullName = (item) => item?.signed_by_full_name || '-';
const getSignerLabel = (item) => item?.signed_by_username || item?.signed_by || '-';

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

const formatTime = (ms) => {
  if (!ms) return '-';
  const value = Number(ms);
  if (!Number.isFinite(value) || value <= 0) return '-';
  return new Date(value).toLocaleString();
};

const getAuthorizationButtonTestId = (userId) =>
  `electronic-signature-authorization-toggle-${String(userId || '').replace(/[^a-zA-Z0-9_-]/g, '_')}`;

const ElectronicSignatureManagement = () => {
  const {
    activeTab,
    loading,
    detailLoading,
    verifyLoading,
    error,
    verifyMessage,
    filters,
    displaySignatures,
    total,
    selectedSignatureId,
    selectedSignature,
    authorizationLoading,
    authorizations,
    setActiveTab,
    setFilterValue,
    handleSearch,
    handleReset,
    handleSelectSignature,
    handleVerifySignature,
    handleToggleAuthorization,
  } = useElectronicSignatureManagementPage();

  if (loading) {
    return <div style={{ padding: '12px' }}>{TEXT.loading}</div>;
  }

  return (
    <div style={{ maxWidth: '1400px' }} data-testid="electronic-signature-management-page">
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          gap: '12px',
          flexWrap: 'wrap',
        }}
      >
        <h2 style={{ margin: 0 }}>{TEXT.title}</h2>
        <div style={{ color: '#6b7280', fontSize: '0.9rem' }}>{TEXT.closeHint}</div>
      </div>

      {error ? (
        <div
          data-testid="electronic-signature-error"
          style={{
            marginTop: '12px',
            padding: '10px 12px',
            background: '#fef2f2',
            color: '#991b1b',
            borderRadius: '10px',
          }}
        >
          {error}
        </div>
      ) : null}

      {verifyMessage ? (
        <div
          data-testid="electronic-signature-verify-message"
          style={{
            marginTop: '12px',
            padding: '10px 12px',
            background: '#ecfdf5',
            color: '#166534',
            borderRadius: '10px',
          }}
        >
          {verifyMessage}
        </div>
      ) : null}

      <div style={{ display: 'flex', gap: '8px', marginTop: '16px', flexWrap: 'wrap' }}>
        <button
          type="button"
          data-testid="electronic-signature-tab-signatures"
          onClick={() => setActiveTab('signatures')}
          style={
            activeTab === 'signatures'
              ? { ...primaryButtonStyle, padding: '10px 16px' }
              : tabButtonStyle
          }
        >
          {TEXT.signatureTab}
        </button>
        <button
          type="button"
          data-testid="electronic-signature-tab-authorizations"
          onClick={() => setActiveTab('authorizations')}
          style={
            activeTab === 'authorizations'
              ? { ...primaryButtonStyle, padding: '10px 16px' }
              : tabButtonStyle
          }
        >
          {TEXT.authorizationTab}
        </button>
      </div>

      {activeTab === 'signatures' ? (
        <>
          <div style={cardStyle}>
            <h3 style={{ marginTop: 0 }}>{TEXT.filters}</h3>
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
                gap: '12px',
              }}
            >
              <label style={{ display: 'grid', gap: '6px' }}>
                <span>{TEXT.recordType}</span>
                <select
                  value={filters.record_type}
                  onChange={(event) => setFilterValue('record_type', event.target.value)}
                  style={inputStyle}
                >
                  {RECORD_TYPE_OPTIONS.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </label>
              <label style={{ display: 'grid', gap: '6px' }}>
                <span>{TEXT.action}</span>
                <select
                  value={filters.action}
                  onChange={(event) => setFilterValue('action', event.target.value)}
                  style={inputStyle}
                >
                  {ACTION_OPTIONS.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </label>
              <label style={{ display: 'grid', gap: '6px' }}>
                <span>{TEXT.signer}</span>
                <input
                  value={filters.signed_by}
                  onChange={(event) => setFilterValue('signed_by', event.target.value)}
                  style={inputStyle}
                />
              </label>
              <label style={{ display: 'grid', gap: '6px' }}>
                <span>{`${TEXT.signedAt}起`}</span>
                <input
                  type="datetime-local"
                  value={filters.signed_at_from}
                  onChange={(event) => setFilterValue('signed_at_from', event.target.value)}
                  style={inputStyle}
                />
              </label>
              <label style={{ display: 'grid', gap: '6px' }}>
                <span>{`${TEXT.signedAt}止`}</span>
                <input
                  type="datetime-local"
                  value={filters.signed_at_to}
                  onChange={(event) => setFilterValue('signed_at_to', event.target.value)}
                  style={inputStyle}
                />
              </label>
            </div>
            <div style={{ display: 'flex', gap: '8px', marginTop: '12px', flexWrap: 'wrap' }}>
              <button
                type="button"
                data-testid="electronic-signature-search"
                onClick={handleSearch}
                style={primaryButtonStyle}
              >
                {TEXT.search}
              </button>
              <button
                type="button"
                data-testid="electronic-signature-reset"
                onClick={handleReset}
                style={buttonStyle}
              >
                {TEXT.reset}
              </button>
              <div style={{ marginLeft: 'auto', color: '#6b7280', alignSelf: 'center' }}>
                {TEXT.total}: {total}
              </div>
            </div>
          </div>

          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'minmax(0, 1.4fr) minmax(360px, 1fr)',
              gap: '16px',
            }}
          >
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
                        <td style={cellStyle} colSpan={8}>
                          {TEXT.noData}
                        </td>
                      </tr>
                    ) : (
                      displaySignatures.map((item) => (
                        <tr
                          key={item.signature_id}
                          style={{
                            background:
                              item.signature_id === selectedSignatureId ? '#eff6ff' : 'transparent',
                          }}
                        >
                          <td style={cellStyle}>{getRecordTypeLabel(item.record_type)}</td>
                          <td style={cellStyle}>{getActionLabel(item.action)}</td>
                          <td style={cellStyle}>{getSignerFullName(item)}</td>
                          <td style={cellStyle}>{getSignerLabel(item)}</td>
                          <td style={cellStyle}>{formatTime(item.signed_at_ms)}</td>
                          <td style={cellStyle}>{getStatusLabel(item.status)}</td>
                          <td style={cellStyle}>
                            {item.verified === true ? TEXT.yes : item.verified === false ? TEXT.no : '-'}
                          </td>
                          <td style={cellStyle}>
                            <button
                              type="button"
                              data-testid={`electronic-signature-view-${item.signature_id}`}
                              onClick={() => handleSelectSignature(item.signature_id)}
                              style={buttonStyle}
                            >
                              {TEXT.view}
                            </button>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>

            <div style={cardStyle}>
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  gap: '8px',
                  alignItems: 'center',
                  flexWrap: 'wrap',
                }}
              >
                <h3 style={{ margin: 0 }}>{TEXT.detail}</h3>
                <button
                  type="button"
                  data-testid="electronic-signature-verify"
                  onClick={handleVerifySignature}
                  disabled={!selectedSignatureId || verifyLoading}
                  style={{
                    ...buttonStyle,
                    cursor:
                      !selectedSignatureId || verifyLoading ? 'not-allowed' : 'pointer',
                  }}
                >
                  {verifyLoading ? `${TEXT.verify}...` : TEXT.verify}
                </button>
              </div>

              {detailLoading ? (
                <div style={{ marginTop: '12px', color: '#6b7280' }}>{TEXT.loading}</div>
              ) : selectedSignature ? (
                <div style={{ display: 'grid', gap: '10px', marginTop: '12px' }}>
                  <div>
                    <strong>{TEXT.recordType}:</strong> {getRecordTypeLabel(selectedSignature.record_type)}
                  </div>
                  <div>
                    <strong>{TEXT.action}:</strong> {getActionLabel(selectedSignature.action)}
                  </div>
                  <div>
                    <strong>{TEXT.signer}:</strong> {getSignerLabel(selectedSignature)}
                  </div>
                  <div>
                    <strong>{TEXT.signedAt}:</strong> {formatTime(selectedSignature.signed_at_ms)}
                  </div>
                  <div>
                    <strong>{TEXT.meaning}:</strong> {selectedSignature.meaning}
                  </div>
                  <div>
                    <strong>{TEXT.reason}:</strong> {selectedSignature.reason}
                  </div>
                  <div>
                    <strong>{TEXT.status}:</strong> {getStatusLabel(selectedSignature.status)}
                  </div>
                  <div>
                    <strong>{TEXT.verified}:</strong>{' '}
                    {selectedSignature.verified === true
                      ? TEXT.yes
                      : selectedSignature.verified === false
                        ? TEXT.no
                        : '-'}
                  </div>
                  <div>
                    <strong>{TEXT.signTokenId}:</strong> {selectedSignature.sign_token_id}
                  </div>
                  <div>
                    <strong>{TEXT.recordHash}:</strong>{' '}
                    <span style={{ wordBreak: 'break-all' }}>{selectedSignature.record_hash}</span>
                  </div>
                  <div>
                    <strong>{TEXT.signatureHash}:</strong>{' '}
                    <span style={{ wordBreak: 'break-all' }}>{selectedSignature.signature_hash}</span>
                  </div>
                </div>
              ) : (
                <div style={{ marginTop: '12px', color: '#6b7280' }}>{TEXT.notSelected}</div>
              )}
            </div>
          </div>
        </>
      ) : (
        <div style={cardStyle}>
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              gap: '12px',
              flexWrap: 'wrap',
            }}
          >
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
                    <td style={cellStyle} colSpan={5}>
                      {TEXT.loading}
                    </td>
                  </tr>
                ) : authorizations.length === 0 ? (
                  <tr>
                    <td style={cellStyle} colSpan={5}>
                      {TEXT.noData}
                    </td>
                  </tr>
                ) : (
                  authorizations.map((item) => (
                    <tr key={item.user_id}>
                      <td style={cellStyle}>
                        <div>{item.full_name || item.username}</div>
                      </td>
                      <td style={cellStyle}>{item.status || '-'}</td>
                      <td style={cellStyle}>
                        {item.electronic_signature_enabled
                          ? TEXT.authorizationEnabled
                          : TEXT.authorizationDisabled}
                      </td>
                      <td style={cellStyle}>{formatTime(item.last_login_at_ms)}</td>
                      <td style={cellStyle}>
                        <button
                          type="button"
                          data-testid={getAuthorizationButtonTestId(item.user_id)}
                          onClick={() =>
                            handleToggleAuthorization(
                              item.user_id,
                              !item.electronic_signature_enabled
                            )
                          }
                          style={
                            item.electronic_signature_enabled
                              ? buttonStyle
                              : primaryButtonStyle
                          }
                        >
                          {item.electronic_signature_enabled ? TEXT.disable : TEXT.enable}
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};

export default ElectronicSignatureManagement;
