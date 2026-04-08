import React from 'react';
import { act, renderHook, waitFor } from '@testing-library/react';
import { AuthProvider, useAuth } from './useAuth';
import authApi from '../features/auth/api';
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

    expect(loginResult).toEqual(expect.objectContaining({ success: false }));
    expect(loginResult.error).toBeTruthy();
    expect(loginResult.error).not.toBe('invalid_username_or_password');
  });

  it('hydrates the current user from the stored session', async () => {
    tokenStore.getAccessToken.mockReturnValue('access-1');
    tokenStore.getRefreshToken.mockReturnValue('refresh-1');
    authApi.getCurrentUser.mockResolvedValue({
      user_id: 'u-1',
      username: 'alice',
      role: 'admin',
      accessible_kb_ids: ['kb-1', 'kb-2'],
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
      capabilities: {
        users: {
          manage: { scope: 'all', targets: [] },
        },
        kb_documents: {
          view: { scope: 'all', targets: [] },
          upload: { scope: 'all', targets: [] },
          review: { scope: 'all', targets: [] },
          approve: { scope: 'all', targets: [] },
          reject: { scope: 'all', targets: [] },
          delete: { scope: 'all', targets: [] },
          download: { scope: 'all', targets: [] },
          copy: { scope: 'all', targets: [] },
        },
        ragflow_documents: {
          view: { scope: 'all', targets: [] },
          preview: { scope: 'all', targets: [] },
          delete: { scope: 'all', targets: [] },
          download: { scope: 'all', targets: [] },
          copy: { scope: 'all', targets: [] },
        },
        kb_directory: {
          manage: { scope: 'all', targets: [] },
        },
        kbs_config: {
          view: { scope: 'all', targets: [] },
        },
        tools: {
          view: { scope: 'all', targets: [] },
        },
        chats: {
          view: { scope: 'all', targets: [] },
        },
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
    expect(result.current.accessibleKbs).toEqual(['kb-1', 'kb-2']);
    expect(result.current.can('tools', 'view', 'paper_download')).toBe(true);
    expect(result.current.can('users', 'manage')).toBe(true);
  });

  it('evaluates scoped capability targets from the auth payload', async () => {
    tokenStore.getAccessToken.mockReturnValue('access-1');
    tokenStore.getRefreshToken.mockReturnValue(null);
    authApi.getCurrentUser.mockResolvedValue({
      user_id: 'u-1',
      username: 'viewer',
      role: 'viewer',
      accessible_kb_ids: ['kb-1', 'kb-2'],
      permissions: {
        can_upload: false,
        can_review: false,
        can_download: false,
        can_copy: false,
        can_delete: false,
        can_manage_kb_directory: false,
        can_view_kb_config: false,
        can_view_tools: true,
        accessible_tools: ['nmpa'],
      },
      capabilities: {
        users: {
          manage: { scope: 'none', targets: [] },
        },
        kb_documents: {
          view: { scope: 'set', targets: ['kb-1', 'kb-2'] },
          upload: { scope: 'none', targets: [] },
          review: { scope: 'none', targets: [] },
          approve: { scope: 'none', targets: [] },
          reject: { scope: 'none', targets: [] },
          delete: { scope: 'none', targets: [] },
          download: { scope: 'none', targets: [] },
          copy: { scope: 'none', targets: [] },
        },
        ragflow_documents: {
          view: { scope: 'set', targets: ['kb-1', 'kb-2'] },
          preview: { scope: 'set', targets: ['kb-1', 'kb-2'] },
          delete: { scope: 'none', targets: [] },
          download: { scope: 'none', targets: [] },
          copy: { scope: 'none', targets: [] },
        },
        kb_directory: {
          manage: { scope: 'none', targets: [] },
        },
        kbs_config: {
          view: { scope: 'none', targets: [] },
        },
        tools: {
          view: { scope: 'set', targets: ['nmpa'] },
        },
        chats: {
          view: { scope: 'none', targets: [] },
        },
      },
    });

    const { result } = renderHook(() => useAuth(), {
      wrapper: ({ children }) => <AuthProvider>{children}</AuthProvider>,
    });

    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(result.current.accessibleKbs).toEqual(['kb-1', 'kb-2']);
    expect(result.current.canAccessKb('kb-1')).toBe(true);
    expect(result.current.canAccessKb('kb-9')).toBe(false);
    expect(result.current.can('tools', 'view')).toBe(true);
    expect(result.current.can('tools', 'view', 'nmpa')).toBe(true);
    expect(result.current.can('tools', 'view', 'paper_download')).toBe(false);
    expect(result.current.can('kb_documents', 'upload')).toBe(false);
    expect(result.current.isAuthorized({
      anyPermissions: [
        { resource: 'kb_documents', action: 'review' },
        { resource: 'kb_documents', action: 'view', target: 'kb-1' },
      ],
    })).toBe(true);
    expect(result.current.isAuthorized({
      anyPermissions: [
        { resource: 'kb_documents', action: 'review' },
        { resource: 'tools', action: 'view', target: 'paper_download' },
      ],
    })).toBe(false);
  });

  it('fails fast when the auth payload does not include capabilities', async () => {
    tokenStore.getAccessToken.mockReturnValue('access-1');
    tokenStore.getRefreshToken.mockReturnValue(null);
    authApi.getCurrentUser.mockResolvedValue({
      user_id: 'u-1',
      username: 'alice',
      role: 'admin',
      accessible_kb_ids: [],
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

    const { result } = renderHook(() => useAuth(), {
      wrapper: ({ children }) => <AuthProvider>{children}</AuthProvider>,
    });

    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(tokenStore.clearAuth).toHaveBeenCalledTimes(1);
    expect(result.current.user).toBeNull();
    expect(result.current.isAuthenticated).toBe(false);
  });
});
