import React from 'react';
import { act, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import Layout from './Layout';
import { useAuth } from '../hooks/useAuth';
import operationApprovalApi from '../features/operationApproval/api';

jest.mock('../hooks/useAuth', () => ({
  useAuth: jest.fn(),
}));

jest.mock('../features/operationApproval/api', () => ({
  __esModule: true,
  default: {
    listInbox: jest.fn().mockResolvedValue({ items: [], count: 0, unreadCount: 0 }),
  },
}));

describe('Layout permission group navigation visibility', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('hides permission group navigation for admin', () => {
    useAuth.mockReturnValue({
      user: { user_id: 'admin-1', username: 'admin', role: 'admin', permission_groups: [] },
      logout: jest.fn(),
      canUpload: () => true,
      canReview: () => true,
      canViewKbConfig: () => true,
      canViewTools: () => true,
      hasRole: (roles) => roles.includes('admin'),
      isAuthorized: ({ allowedRoles }) => !allowedRoles || allowedRoles.includes('admin'),
    });

    render(
      <MemoryRouter initialEntries={['/users']}>
        <Layout>
          <div>content</div>
        </Layout>
      </MemoryRouter>
    );

    expect(screen.queryByTestId('nav-permission-groups')).not.toBeInTheDocument();
    expect(screen.queryByTestId('nav-kbs')).not.toBeInTheDocument();
    expect(screen.getByTestId('nav-document-history')).toBeInTheDocument();
    expect(screen.getByTestId('nav-training-compliance')).toBeInTheDocument();
    expect(screen.queryByTestId('nav-documents')).not.toBeInTheDocument();
  });

  it('shows permission group navigation for sub admin', () => {
    useAuth.mockReturnValue({
      user: { user_id: 'sub-1', username: 'sub', role: 'sub_admin', permission_groups: [] },
      logout: jest.fn(),
      canUpload: () => true,
      canReview: () => true,
      canViewKbConfig: () => true,
      canViewTools: () => true,
      hasRole: (roles) => roles.includes('sub_admin'),
      isAuthorized: ({ allowedRoles }) => !allowedRoles || allowedRoles.includes('sub_admin'),
    });

    render(
      <MemoryRouter initialEntries={['/users']}>
        <Layout>
          <div>content</div>
        </Layout>
      </MemoryRouter>
    );

    expect(screen.getByTestId('nav-permission-groups')).toBeInTheDocument();
    expect(screen.getByTestId('nav-kbs')).toBeInTheDocument();
    expect(screen.queryByTestId('nav-training-compliance')).not.toBeInTheDocument();
  });

  it('shows full name and localized role label in the sidebar profile area', () => {
    useAuth.mockReturnValue({
      user: {
        user_id: 'sub-1',
        username: 'wangxin',
        full_name: 'Wang Xin',
        role: 'sub_admin',
        permission_groups: [{ group_name: 'test-group' }],
      },
      logout: jest.fn(),
      canUpload: () => true,
      canReview: () => true,
      canViewKbConfig: () => true,
      canViewTools: () => true,
      hasRole: (roles) => roles.includes('sub_admin'),
      isAuthorized: ({ allowedRoles }) => !allowedRoles || allowedRoles.includes('sub_admin'),
    });

    render(
      <MemoryRouter initialEntries={['/users']}>
        <Layout>
          <div>content</div>
        </Layout>
      </MemoryRouter>
    );

    expect(screen.getByTestId('layout-sidebar-title')).toHaveTextContent('\u77e5\u8bc6\u5e93\u7cfb\u7edf');
    expect(screen.getByTestId('layout-sidebar-subtitle')).toHaveTextContent('sub-1');
    expect(screen.getByTestId('layout-user-name')).toHaveTextContent('Wang Xin');
    expect(screen.getByTestId('layout-user-role')).toHaveTextContent('\u5b50\u7ba1\u7406\u5458');
    expect(screen.getByTestId('layout-user-role')).not.toHaveTextContent('sub_admin');
    expect(screen.getByTestId('layout-user-role')).not.toHaveTextContent('test-group');
  });

  it('hides knowledge bases navigation for normal viewer', () => {
    useAuth.mockReturnValue({
      user: { user_id: 'viewer-1', username: 'viewer', role: 'viewer', permission_groups: [] },
      logout: jest.fn(),
      canUpload: () => true,
      canReview: () => true,
      canViewKbConfig: () => true,
      canViewTools: () => true,
      hasRole: () => false,
      isAuthorized: ({ allowedRoles }) => !allowedRoles,
    });

    render(
      <MemoryRouter initialEntries={['/browser']}>
        <Layout>
          <div>content</div>
        </Layout>
      </MemoryRouter>
    );

    expect(screen.queryByTestId('nav-kbs')).not.toBeInTheDocument();
  });

  it('hides document history navigation when shared auth evaluation denies both view and review access', () => {
    useAuth.mockReturnValue({
      user: { user_id: 'viewer-2', username: 'viewer', role: 'viewer', permission_groups: [] },
      logout: jest.fn(),
      hasRole: () => false,
      isAuthorized: ({ allowedRoles, anyPermissions }) => {
        if (allowedRoles) return false;
        if (anyPermissions) return false;
        return true;
      },
    });

    render(
      <MemoryRouter initialEntries={['/browser']}>
        <Layout>
          <div>content</div>
        </Layout>
      </MemoryRouter>
    );

    expect(screen.queryByTestId('nav-document-history')).not.toBeInTheDocument();
  });

  it('hides notification settings and electronic signatures for sub admin', () => {
    useAuth.mockReturnValue({
      user: { user_id: 'sub-1', username: 'sub', role: 'sub_admin', permission_groups: [] },
      logout: jest.fn(),
      canUpload: () => true,
      canReview: () => true,
      canViewKbConfig: () => true,
      canViewTools: () => true,
      hasRole: (roles) => roles.includes('sub_admin'),
      isAuthorized: ({ allowedRoles }) => !allowedRoles || allowedRoles.includes('sub_admin'),
    });

    render(
      <MemoryRouter initialEntries={['/users']}>
        <Layout>
          <div>content</div>
        </Layout>
      </MemoryRouter>
    );

    expect(screen.queryByTestId('nav-notification-settings')).not.toBeInTheDocument();
    expect(screen.queryByTestId('nav-electronic-signatures')).not.toBeInTheDocument();
  });

  it('updates inbox unread badge immediately when unread count event is published', async () => {
    operationApprovalApi.listInbox.mockResolvedValue({ items: [], count: 0, unreadCount: 0 });
    useAuth.mockReturnValue({
      user: { user_id: 'viewer-1', username: 'viewer', role: 'viewer', permission_groups: [] },
      logout: jest.fn(),
      canUpload: () => true,
      canReview: () => true,
      canViewKbConfig: () => false,
      canViewTools: () => true,
      hasRole: () => false,
      isAuthorized: ({ allowedRoles }) => !allowedRoles,
    });

    render(
      <MemoryRouter initialEntries={['/inbox']}>
        <Layout>
          <div>content</div>
        </Layout>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(operationApprovalApi.listInbox).toHaveBeenCalled();
    });

    act(() => {
      window.dispatchEvent(new CustomEvent('notification:inbox-unread-count', {
        detail: { unreadCount: 3 },
      }));
    });

    expect(screen.getByTestId('layout-inbox-unread')).toHaveTextContent('3');
  });
});
