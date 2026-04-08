import React from 'react';

import { primaryButtonStyle, tabButtonStyle, TEXT } from '../electronicSignatureManagementView';

export default function ElectronicSignatureHeader({
  activeTab,
  setActiveTab,
  error,
  verifyMessage,
}) {
  return (
    <>
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
    </>
  );
}
