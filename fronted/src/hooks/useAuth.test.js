import React from 'react';
import { act, renderHook, waitFor } from '@testing-library/react';
import { AuthProvider, useAuth } from './useAuth';
import authApi from '../features/auth/api';
import { meApi } from '../features/me/api';
import tokenStore from '../shared/auth/tokenStore';

jest.mock('../features/auth/api', () => ({
  __esModule: true,
  default: {
    login: jest.fn(),
    logout: jest.fn(),
    getCurrentUser: jest.fn(),
    refreshAccessToken: jest.fn(),
  },
}));

jest.mock('../features/me/api', () => ({
  __esModule: true,
  meApi: {
    listMyKnowledgeBases: jest.fn().mockResolvedValue({ kbIds: [], kbNames: [] }),
  },
}));

jest.mock('../shared/auth/tokenStore', () => ({
  __esModule: true,
  default: {
    getAccessToken: jest.fn(),
    getRefreshToken: jest.fn(),
    getUser: jest.fn(),
    setAuth: jest.fn(),
    setUser: jest.fn(),
    clearAuth: jest.fn(),
  },
}));

describe('useAuth', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    tokenStore.getAccessToken.mockReturnValue(null);
    tokenStore.getRefreshToken.mockReturnValue(null);
    tokenStore.getUser.mockReturnValue(null);
    meApi.listMyKnowledgeBases.mockResolvedValue({ kbIds: [], kbNames: [] });
  });

  it('shows a clear invalid-credentials message', async () => {
    authApi.login.mockRejectedValue(new Error('invalid_username_or_password'));

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

  it('hydrates the current user from the stored session', async () => {
    tokenStore.getAccessToken.mockReturnValue('access-1');
    tokenStore.getRefreshToken.mockReturnValue('refresh-1');
    authApi.getCurrentUser.mockResolvedValue({
      user_id: 'u-1',
      username: 'alice',
      role: 'admin',
      permissions: {
        can_upload: true,
        can_review: true,
        can_download: true,
        can_copy: true,
        can_delete: true,
        can_manage_kb_directory: true,
        can_view_kb_config: true,
        can_view_tools: true,
        accessible_tools: ['nas-browser'],
      },
    });

    const { result } = renderHook(() => useAuth(), {
      wrapper: ({ children }) => <AuthProvider>{children}</AuthProvider>,
    });

    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(authApi.getCurrentUser).toHaveBeenCalledTimes(1);
    expect(tokenStore.setUser).toHaveBeenCalledWith(expect.objectContaining({ user_id: 'u-1' }));
    expect(result.current.user).toEqual(expect.objectContaining({ user_id: 'u-1', username: 'alice' }));
    expect(result.current.isAuthenticated).toBe(true);
  });

  it('hydrates accessible KB ids through the me feature api contract', async () => {
    tokenStore.getAccessToken.mockReturnValue('access-1');
    tokenStore.getRefreshToken.mockReturnValue('refresh-1');
    authApi.getCurrentUser.mockResolvedValue({
      user_id: 'u-1',
      username: 'alice',
      role: 'admin',
      permissions: {
        can_upload: true,
        can_review: true,
        can_download: true,
        can_copy: true,
        can_delete: true,
        can_manage_kb_directory: true,
        can_view_kb_config: true,
        can_view_tools: true,
        accessible_tools: [],
      },
    });
    meApi.listMyKnowledgeBases.mockResolvedValue({ kbIds: ['kb-1', 'kb-2'], kbNames: ['KB 1', 'KB 2'] });

    const { result } = renderHook(() => useAuth(), {
      wrapper: ({ children }) => <AuthProvider>{children}</AuthProvider>,
    });

    await waitFor(() => expect(result.current.loading).toBe(false));
    await waitFor(() => expect(meApi.listMyKnowledgeBases).toHaveBeenCalledTimes(1));

    expect(result.current.accessibleKbs).toEqual(['kb-1', 'kb-2']);
  });
});
