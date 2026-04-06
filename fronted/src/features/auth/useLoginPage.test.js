import { act, renderHook } from '@testing-library/react';

import { useAuth } from '../../hooks/useAuth';
import useLoginPage from './useLoginPage';

const mockNavigate = jest.fn();

jest.mock('react-router-dom', () => {
  const actual = jest.requireActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

jest.mock('../../hooks/useAuth', () => ({
  useAuth: jest.fn(),
}));

describe('useLoginPage', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockNavigate.mockReset();
  });

  it('logs in successfully and navigates to chat', async () => {
    const loginMock = jest.fn().mockResolvedValue({ success: true });
    useAuth.mockReturnValue({
      login: loginMock,
    });

    const { result } = renderHook(() => useLoginPage());

    act(() => {
      result.current.setUsername('alice');
      result.current.setPassword('Secret123');
    });

    await act(async () => {
      await result.current.handleSubmit({ preventDefault() {} });
    });

    expect(loginMock).toHaveBeenCalledWith('alice', 'Secret123');
    expect(mockNavigate).toHaveBeenCalledWith('/chat');
    expect(result.current.error).toBe('');
  });

  it('keeps the user on the page and surfaces the login error when login fails', async () => {
    const loginMock = jest.fn().mockResolvedValue({
      success: false,
      error: '用户名或密码错误',
    });
    useAuth.mockReturnValue({
      login: loginMock,
    });

    const { result } = renderHook(() => useLoginPage());

    act(() => {
      result.current.setUsername('alice');
      result.current.setPassword('Wrong123');
    });

    await act(async () => {
      await result.current.handleSubmit({ preventDefault() {} });
    });

    expect(loginMock).toHaveBeenCalledWith('alice', 'Wrong123');
    expect(mockNavigate).not.toHaveBeenCalled();
    expect(result.current.error).toBe('用户名或密码错误');
  });
});
