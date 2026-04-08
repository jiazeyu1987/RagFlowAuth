import React from 'react';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import PermissionGuard from './PermissionGuard';
import { useAuth } from '../hooks/useAuth';

jest.mock('../hooks/useAuth', () => ({
  useAuth: jest.fn(),
}));

const renderGuard = (guardProps = {}) => render(
  <MemoryRouter initialEntries={['/protected']}>
    <Routes>
      <Route path="/login" element={<div>login page</div>} />
      <Route path="/unauthorized" element={<div>unauthorized page</div>} />
      <Route
        path="/protected"
        element={(
          <PermissionGuard {...guardProps}>
            <div>protected content</div>
          </PermissionGuard>
        )}
      />
    </Routes>
  </MemoryRouter>
);

describe('PermissionGuard', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('shows a loading state while auth is loading', () => {
    useAuth.mockReturnValue({
      loading: true,
      user: null,
      isAuthorized: jest.fn(),
    });

    renderGuard();

    expect(screen.getByText('加载中...')).toBeInTheDocument();
  });

  it('redirects unauthenticated users to login', () => {
    useAuth.mockReturnValue({
      loading: false,
      user: null,
      isAuthorized: jest.fn(),
    });

    renderGuard();

    expect(screen.getByText('login page')).toBeInTheDocument();
  });

  it('delegates authorization to useAuth.isAuthorized', () => {
    const isAuthorized = jest.fn().mockReturnValue(true);

    useAuth.mockReturnValue({
      loading: false,
      user: { user_id: 'u-1', role: 'admin' },
      isAuthorized,
    });

    renderGuard({
      allowedRoles: ['admin'],
      permission: { resource: 'tools', action: 'view', target: 'nmpa' },
      anyPermissions: [{ resource: 'kb_documents', action: 'view', target: 'kb-1' }],
    });

    expect(screen.getByText('protected content')).toBeInTheDocument();
    expect(isAuthorized).toHaveBeenCalledWith({
      allowedRoles: ['admin'],
      permission: { resource: 'tools', action: 'view', target: 'nmpa' },
      permissions: undefined,
      anyPermissions: [{ resource: 'kb_documents', action: 'view', target: 'kb-1' }],
    });
  });

  it('renders the custom fallback when authorization is denied', () => {
    useAuth.mockReturnValue({
      loading: false,
      user: { user_id: 'u-2', role: 'viewer' },
      isAuthorized: jest.fn().mockReturnValue(false),
    });

    renderGuard({
      permission: { resource: 'tools', action: 'view', target: 'nmpa' },
      fallback: <div>denied content</div>,
    });

    expect(screen.getByText('denied content')).toBeInTheDocument();
  });

  it('redirects to unauthorized when no fallback is provided', () => {
    useAuth.mockReturnValue({
      loading: false,
      user: { user_id: 'u-2', role: 'viewer' },
      isAuthorized: jest.fn().mockReturnValue(false),
    });

    renderGuard({
      permission: { resource: 'tools', action: 'view', target: 'nmpa' },
    });

    expect(screen.getByText('unauthorized page')).toBeInTheDocument();
  });
});
