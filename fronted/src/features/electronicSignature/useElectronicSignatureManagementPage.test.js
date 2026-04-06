import { act, renderHook, waitFor } from '@testing-library/react';

import { electronicSignatureApi } from './api';
import useElectronicSignatureManagementPage from './useElectronicSignatureManagementPage';

jest.mock('./api', () => ({
  electronicSignatureApi: {
    listSignatures: jest.fn(),
    getSignature: jest.fn(),
    verifySignature: jest.fn(),
    listAuthorizations: jest.fn(),
    updateAuthorization: jest.fn(),
  },
}));

const signatureListItem = {
  signature_id: 'sig-1',
  record_type: 'operation_approval_request',
  action: 'operation_approval_approve',
  signed_by_full_name: '张三',
  signed_by_username: 'zhangsan',
  status: 'signed',
  verified: false,
  signed_at_ms: 1710000000000,
};

const signatureDetail = {
  ...signatureListItem,
  meaning: '审批签名',
  reason: '审批通过',
  sign_token_id: 'token-1',
  record_hash: 'record-hash-1',
  signature_hash: 'signature-hash-1',
};

const authorizationItems = [
  {
    user_id: 'user-1',
    username: 'zhangsan',
    full_name: '张三',
    status: 'active',
    electronic_signature_enabled: false,
    last_login_at_ms: 1710000000000,
  },
];

describe('useElectronicSignatureManagementPage', () => {
  beforeEach(() => {
    jest.clearAllMocks();

    electronicSignatureApi.listSignatures.mockResolvedValue({
      items: [signatureListItem],
      total: 1,
    });
    electronicSignatureApi.getSignature.mockResolvedValue(signatureDetail);
    electronicSignatureApi.verifySignature.mockResolvedValue({ verified: true });
    electronicSignatureApi.listAuthorizations.mockResolvedValue({
      items: authorizationItems,
    });
    electronicSignatureApi.updateAuthorization.mockResolvedValue({ ok: true });
  });

  it('loads signatures, selects the first signature, and verifies it', async () => {
    const { result } = renderHook(() => useElectronicSignatureManagementPage());

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.displaySignatures).toHaveLength(1);
    expect(result.current.selectedSignatureId).toBe('sig-1');
    expect(result.current.selectedSignature?.sign_token_id).toBe('token-1');
    expect(result.current.authorizations).toHaveLength(1);

    await act(async () => {
      await result.current.handleVerifySignature();
    });

    expect(electronicSignatureApi.verifySignature).toHaveBeenCalledWith('sig-1');
    expect(result.current.verifyMessage).toBe('验签通过');
    expect(result.current.selectedSignature?.verified).toBe(true);
    expect(result.current.displaySignatures[0]?.verified).toBe(true);
  });

  it('updates authorization and reloads authorization list', async () => {
    const { result } = renderHook(() => useElectronicSignatureManagementPage());

    await waitFor(() => {
      expect(result.current.authorizations).toHaveLength(1);
    });

    await act(async () => {
      await result.current.handleToggleAuthorization('user-1', true);
    });

    expect(electronicSignatureApi.updateAuthorization).toHaveBeenCalledWith('user-1', {
      electronic_signature_enabled: true,
    });
    expect(electronicSignatureApi.listAuthorizations).toHaveBeenCalledTimes(2);
  });
});
