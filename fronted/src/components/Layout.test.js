import React from 'react';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import Layout from './Layout';
import { useAuth } from '../hooks/useAuth';

jest.mock('../hooks/useAuth', () => ({
  useAuth: jest.fn(),
}));

jest.mock('../features/operationApproval/api', () => ({
  __esModule: true,
  default: {
    listInbox: jest.fn().mockResolvedValue({ unread_count: 0 }),
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

  it('hides notification settings and electronic signatures for sub admin', () => {
    useAuth.mockReturnValue({
      user: { user_id: 'sub-1', username: 'sub', role: 'sub_admin', permission_groups: [] },
      logout: jest.fn(),
      canUpload: () => true,
      canReview: () => true,
      canViewKbConfig: () => true,
      canViewTools: () => true,
      hasRole: (roles) => roles.includes('sub_admin'),
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
});
