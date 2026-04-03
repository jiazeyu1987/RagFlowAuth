import React from 'react';
import { act, renderHook, waitFor } from '@testing-library/react';
import { AuthProvider, useAuth } from './useAuth';
import authClient from '../api/authClient';

jest.mock('../api/authClient', () => ({
  __esModule: true,
  default: {
    accessToken: null,
    refreshToken: null,
    user: null,
    login: jest.fn(),
    logout: jest.fn(),
    clearAuth: jest.fn(),
    getCurrentUser: jest.fn(),
    refreshAccessToken: jest.fn(),
    getMyKnowledgeBases: jest.fn().mockResolvedValue({ kb_ids: [] }),
  },
}));

jest.mock('../shared/auth/tokenStore', () => ({
  __esModule: true,
  default: {
    clearAuth: jest.fn(),
  },
}));

describe('useAuth login error mapping', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('shows a clear invalid-credentials message', async () => {
    authClient.login.mockRejectedValue(new Error('invalid_username_or_password'));

    const { result } = renderHook(() => useAuth(), {
      wrapper: ({ children }) => <AuthProvider>{children}</AuthProvider>,
    });

    await waitFor(() => expect(result.current.loading).toBe(false));

    let loginResult;
    await act(async () => {
      loginResult = await result.current.login('wangxin', 'wrong-password');
    });

    expect(loginResult).toEqual({ success: false, error: '用户名或密码错误' });
  });
});
