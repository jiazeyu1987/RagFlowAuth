import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import LoginPage from './LoginPage';
import { useAuth } from '../hooks/useAuth';

const mockNavigate = jest.fn();

jest.mock('react-router-dom', () => {
  const actual = jest.requireActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

jest.mock('../hooks/useAuth', () => ({
  useAuth: jest.fn(),
}));

describe('LoginPage', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockNavigate.mockReset();
  });

  it('submits the login form and navigates to chat on success', async () => {
    const user = userEvent.setup();
    const loginMock = jest.fn().mockResolvedValue({ success: true });

    useAuth.mockReturnValue({
      login: loginMock,
    });

    render(<LoginPage />);

    await user.type(screen.getByTestId('login-username'), 'alice');
    await user.type(screen.getByTestId('login-password'), 'Secret123');
    await user.click(screen.getByTestId('login-submit'));

    await waitFor(() => {
      expect(loginMock).toHaveBeenCalledWith('alice', 'Secret123');
    });
    expect(mockNavigate).toHaveBeenCalledWith('/chat');
  });

  it('shows the login error when credentials are invalid', async () => {
    const user = userEvent.setup();
    const loginMock = jest.fn().mockResolvedValue({
      success: false,
      error: '用户名或密码错误',
    });

    useAuth.mockReturnValue({
      login: loginMock,
    });

    render(<LoginPage />);

    await user.type(screen.getByTestId('login-username'), 'alice');
    await user.type(screen.getByTestId('login-password'), 'Wrong123');
    await user.click(screen.getByTestId('login-submit'));

    expect(await screen.findByTestId('login-error')).toHaveTextContent('用户名或密码错误');
    expect(mockNavigate).not.toHaveBeenCalled();
  });
});
