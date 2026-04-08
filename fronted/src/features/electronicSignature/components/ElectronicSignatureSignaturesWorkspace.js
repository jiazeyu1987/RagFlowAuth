import React from 'react';

import {
  TEXT,
  buttonStyle,
  cardStyle,
  cellStyle,
  getActionLabel,
  getRecordTypeLabel,
  getSignerFullName,
  getSignerLabel,
  getStatusLabel,
  formatTime,
  tableStyle,
} from '../electronicSignatureManagementView';

export default function ElectronicSignatureSignaturesWorkspace({
  displaySignatures,
  selectedSignatureId,
  handleSelectSignature,
  detailLoading,
  selectedSignature,
  verifyLoading,
  handleVerifySignature,
}) {
  return (
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
  );
}
