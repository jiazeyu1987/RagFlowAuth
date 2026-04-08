import React from 'react';
import { Link } from 'react-router-dom';
import { buttonStyle, cardStyle, primaryButtonStyle } from '../pageStyles';

export default function ApprovalCenterAlert({
  error,
  showTrainingHelp,
  currentUserLabel,
  userRole,
  trainingRecordPath,
  trainingCertificationPath,
}) {
  if (!error) {
    return null;
  }

  return (
    <div
      data-testid="approval-center-error"
      style={{ ...cardStyle, borderColor: '#fecaca', background: '#fef2f2', color: '#991b1b' }}
    >
      <div>{error}</div>
      {showTrainingHelp ? (
        <div style={{ marginTop: '10px', display: 'grid', gap: '10px' }}>
          <div data-testid="approval-center-training-help">
            当前审批账号：{currentUserLabel}。审批培训门禁已生效，需要先补录培训记录，再授予上岗认证。
          </div>
          {String(userRole || '') === 'admin' ? (
            <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
              <Link
                data-testid="approval-center-training-record-link"
                to={trainingRecordPath}
                style={{
                  ...primaryButtonStyle,
                  textDecoration: 'none',
                  display: 'inline-flex',
                  alignItems: 'center',
                }}
              >
                去补录培训记录
              </Link>
              <Link
                data-testid="approval-center-training-certification-link"
                to={trainingCertificationPath}
                style={{
                  ...buttonStyle,
                  textDecoration: 'none',
                  display: 'inline-flex',
                  alignItems: 'center',
                }}
              >
                去补录上岗认证
              </Link>
            </div>
          ) : (
            <div>
              请联系管理员在“培训合规管理”中为当前账号补录培训记录并授予上岗认证。
            </div>
          )}
        </div>
      ) : null}
    </div>
  );
}
