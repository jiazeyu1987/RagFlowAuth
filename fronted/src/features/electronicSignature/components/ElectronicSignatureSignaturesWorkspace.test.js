import { render, screen } from '@testing-library/react';

import ElectronicSignatureSignaturesWorkspace from './ElectronicSignatureSignaturesWorkspace';

describe('ElectronicSignatureSignaturesWorkspace', () => {
  it('shows full name in signature detail', () => {
    render(
      <ElectronicSignatureSignaturesWorkspace
        displaySignatures={[
          {
            signature_id: 'sig-1',
            record_type: 'operation_approval_request',
            action: 'operation_approval_approve',
            signed_by_full_name: '汤斌',
            signed_by_username: 'tangbin',
            signed_at_ms: 1712714740000,
            status: 'signed',
            verified: true,
          },
        ]}
        selectedSignatureId="sig-1"
        handleSelectSignature={() => {}}
        detailLoading={false}
        selectedSignature={{
          signature_id: 'sig-1',
          record_type: 'operation_approval_request',
          action: 'operation_approval_approve',
          signed_by_full_name: '汤斌',
          signed_by_username: 'tangbin',
          signed_at_ms: 1712714740000,
          meaning: '操作审批通过',
          reason: '审批后同意执行该操作',
          status: 'signed',
          verified: true,
          sign_token_id: 'token-1',
          record_hash: 'record-hash-1',
          signature_hash: 'signature-hash-1',
        }}
        verifyLoading={false}
        handleVerifySignature={() => {}}
      />
    );

    expect(screen.getByText('姓名:')).toBeInTheDocument();
    expect(screen.getAllByText('汤斌')).toHaveLength(2);
    expect(screen.getByText('签署人:')).toBeInTheDocument();
    expect(screen.getAllByText('tangbin')).toHaveLength(2);
  });
});
