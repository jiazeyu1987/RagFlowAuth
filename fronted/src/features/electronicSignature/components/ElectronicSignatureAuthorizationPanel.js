import React from 'react';

import {
  TEXT,
  buttonStyle,
  cardStyle,
  cellStyle,
  formatTime,
  getAuthorizationButtonTestId,
  primaryButtonStyle,
  tableStyle,
} from '../electronicSignatureManagementView';

export default function ElectronicSignatureAuthorizationPanel({
  authorizationLoading,
  authorizations,
  handleToggleAuthorization,
}) {
  return (
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
  );
}
