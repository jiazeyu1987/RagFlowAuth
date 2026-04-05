import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import ChangePassword from './ChangePassword';
import meApi from '../features/me/api';
import { useAuth } from '../hooks/useAuth';

jest.mock('../features/me/api', () => ({
  __esModule: true,
  default: {
    changePassword: jest.fn(),
  },
}));

jest.mock('../hooks/useAuth', () => ({
  useAuth: jest.fn(),
}));

describe('ChangePassword', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    useAuth.mockReturnValue({
      user: {
        username: 'alice',
        full_name: 'Alice',
      },
    });
    meApi.changePassword.mockResolvedValue({ ok: true });
  });

  it('submits password changes through the me feature API', async () => {
    const user = userEvent.setup();

    render(<ChangePassword />);

    await user.type(screen.getByTestId('change-password-old'), 'OldPass123');
    await user.type(screen.getByTestId('change-password-new'), 'NewPass123');
    await user.type(screen.getByTestId('change-password-confirm'), 'NewPass123');
    await user.click(screen.getByTestId('change-password-submit'));

    await waitFor(() => {
      expect(meApi.changePassword).toHaveBeenCalledWith('OldPass123', 'NewPass123');
    });
    expect(screen.getByTestId('change-password-success')).toBeInTheDocument();
  });
});
